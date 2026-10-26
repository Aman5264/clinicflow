import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from app.extensions import db
from app.models.visit import Visit, ClinicalAuditLog
from app.models.appointment import Appointment, AppointmentStatus
from app.models.patient import Patient
from app.models.user import User, Role

class ConsultationError(Exception):
    pass

class ConsultationService:
    @staticmethod
    def create_visit(
        patient_id: int,
        doctor_id: int,
        symptoms: str,
        diagnosis: str,
        clinical_notes: Optional[str] = None,
        appointment_id: Optional[int] = None,
        author_user_id: Optional[int] = None
    ) -> Visit:
        patient = db.session.get(Patient, patient_id)
        if not patient or patient.is_archived:
            raise ValueError("Patient not found or is archived.")

        doctor = db.session.get(User, doctor_id)
        if not doctor or doctor.role not in [Role.DOCTOR, Role.ADMIN]:
            raise ValueError("Assigned practitioner must be a doctor or clinical administrator.")

        appointment = None
        if appointment_id:
            appointment = db.session.get(Appointment, appointment_id)
            if not appointment:
                raise ValueError("Referenced appointment does not exist.")

            # Duplicate visit check: avoid creating multiple visits for the same appointment
            existing_visit = Visit.query.filter_by(appointment_id=appointment_id).first()
            if existing_visit:
                raise ConsultationError(
                    f"A clinical consultation record (Visit #{existing_visit.id}) has already been completed for this appointment."
                )

        now = datetime.now(timezone.utc)
        visit = Visit(
            patient_id=patient_id,
            doctor_id=doctor_id,
            appointment_id=appointment_id,
            symptoms=symptoms.strip(),
            diagnosis=diagnosis.strip(),
            clinical_notes=clinical_notes.strip() if clinical_notes else None,
            start_time=now,
            end_time=now
        )
        db.session.add(visit)

        # Transition appointment to COMPLETED if linked
        if appointment:
            appointment.status = AppointmentStatus.COMPLETED

        # Create audit entry
        audit = ClinicalAuditLog(
            visit=visit,
            user_id=author_user_id or doctor_id,
            action='created',
            changes_json=json.dumps({
                'symptoms': visit.symptoms,
                'diagnosis': visit.diagnosis,
                'appointment_id': appointment_id
            })
        )
        db.session.add(audit)

        db.session.commit()
        return visit

    @staticmethod
    def update_visit(
        visit_id: int,
        symptoms: str,
        diagnosis: str,
        clinical_notes: Optional[str] = None,
        author_user_id: Optional[int] = None
    ) -> Visit:
        visit = db.session.get(Visit, visit_id)
        if not visit:
            raise ValueError("Visit not found.")

        changes = {}
        if visit.symptoms != symptoms.strip():
            changes['symptoms'] = {'old': visit.symptoms, 'new': symptoms.strip()}
            visit.symptoms = symptoms.strip()

        if visit.diagnosis != diagnosis.strip():
            changes['diagnosis'] = {'old': visit.diagnosis, 'new': diagnosis.strip()}
            visit.diagnosis = diagnosis.strip()

        new_notes = clinical_notes.strip() if clinical_notes else None
        if visit.clinical_notes != new_notes:
            changes['clinical_notes'] = {'old': visit.clinical_notes, 'new': new_notes}
            visit.clinical_notes = new_notes

        if changes:
            audit = ClinicalAuditLog(
                visit=visit,
                user_id=author_user_id or visit.doctor_id,
                action='updated',
                changes_json=json.dumps(changes)
            )
            db.session.add(audit)

        db.session.commit()
        return visit
