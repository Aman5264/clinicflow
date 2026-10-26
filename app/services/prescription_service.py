from typing import List, Dict, Optional, Any
from app.extensions import db
from app.models.prescription import Prescription, PrescriptionItem
from app.models.visit import Visit
from app.models.user import User, Role

class PrescriptionService:
    @staticmethod
    def create_prescription(
        visit_id: int,
        doctor_id: int,
        items_data: List[Dict[str, Any]],
        notes: Optional[str] = None
    ) -> Prescription:
        if not items_data:
            raise ValueError("Prescription must contain at least one medication item.")

        visit = db.session.get(Visit, visit_id)
        if not visit:
            raise ValueError("Clinical consultation visit not found.")

        doctor = db.session.get(User, doctor_id)
        if not doctor or doctor.role not in [Role.DOCTOR, Role.ADMIN]:
            raise ValueError("Prescriptions may only be authored by authorized doctors or medical administrators.")

        prescription = Prescription(
            visit_id=visit.id,
            patient_id=visit.patient_id,
            doctor_id=doctor_id,
            notes=notes.strip() if notes else None
        )
        db.session.add(prescription)

        for item in items_data:
            med_name = item.get('medicine_name', '').strip()
            if not med_name:
                raise ValueError("Medicine name cannot be blank.")

            p_item = PrescriptionItem(
                prescription=prescription,
                medicine_name=med_name,
                strength=item.get('strength', 'Standard').strip(),
                dosage=item.get('dosage', '1 unit').strip(),
                route=item.get('route', 'Oral').strip(),
                frequency=item.get('frequency', 'Once daily').strip(),
                duration=item.get('duration', '7 days').strip(),
                instructions=item.get('instructions', '').strip() if item.get('instructions') else None
            )
            db.session.add(p_item)

        db.session.commit()
        return prescription

    @staticmethod
    def update_prescription(
        prescription_id: int,
        items_data: List[Dict[str, Any]],
        notes: Optional[str] = None
    ) -> Prescription:
        if not items_data:
            raise ValueError("Prescription must contain at least one medication item.")

        prescription = db.session.get(Prescription, prescription_id)
        if not prescription:
            raise ValueError("Prescription not found.")

        # Clear existing items and repopulate
        for item in list(prescription.items):
            db.session.delete(item)

        for item in items_data:
            med_name = item.get('medicine_name', '').strip()
            if not med_name:
                raise ValueError("Medicine name cannot be blank.")

            p_item = PrescriptionItem(
                prescription=prescription,
                medicine_name=med_name,
                strength=item.get('strength', 'Standard').strip(),
                dosage=item.get('dosage', '1 unit').strip(),
                route=item.get('route', 'Oral').strip(),
                frequency=item.get('frequency', 'Once daily').strip(),
                duration=item.get('duration', '7 days').strip(),
                instructions=item.get('instructions', '').strip() if item.get('instructions') else None
            )
            db.session.add(p_item)

        if notes is not None:
            prescription.notes = notes.strip() if notes else None

        db.session.commit()
        return prescription
