from datetime import datetime, timedelta, timezone, date
from typing import Optional, List
from sqlalchemy import or_, and_
from app.extensions import db
from app.models.appointment import Appointment, AppointmentStatus
from app.models.user import User, Role
from app.models.patient import Patient

class AppointmentConflictError(Exception):
    pass

class AppointmentStateError(Exception):
    pass

class AppointmentService:
    @staticmethod
    def check_doctor_conflict(
        doctor_id: int,
        scheduled_time: datetime,
        duration_minutes: int = 30,
        exclude_appointment_id: Optional[int] = None
    ) -> bool:
        """
        Detects if another active appointment overlaps with [scheduled_time, scheduled_time + duration].
        Overlapping interval logic: startA < endB and endA > startB
        """
        new_start = scheduled_time
        new_end = scheduled_time + timedelta(minutes=duration_minutes)

        # Active statuses that count as occupying a doctor's schedule
        active_statuses = [
            AppointmentStatus.SCHEDULED,
            AppointmentStatus.CHECKED_IN,
            AppointmentStatus.IN_CONSULTATION
        ]

        query = Appointment.query.filter(
            Appointment.doctor_id == doctor_id,
            Appointment.status.in_(active_statuses)
        )

        if exclude_appointment_id:
            query = query.filter(Appointment.id != exclude_appointment_id)

        existing_appointments = query.all()
        for apt in existing_appointments:
            apt_start = apt.scheduled_time
            apt_end = apt.scheduled_time + timedelta(minutes=apt.duration_minutes)

            # Check overlap
            if new_start < apt_end and new_end > apt_start:
                return True

        return False

    @staticmethod
    def book_appointment(
        patient_id: int,
        doctor_id: int,
        scheduled_time: datetime,
        reason: str,
        duration_minutes: int = 30,
        notes: Optional[str] = None
    ) -> Appointment:
        patient = db.session.get(Patient, patient_id)
        if not patient or patient.is_archived:
            raise ValueError("Patient not found or is archived.")

        doctor = db.session.get(User, doctor_id)
        if not doctor or doctor.role not in [Role.DOCTOR, Role.ADMIN] or not doctor.is_active:
            raise ValueError("Invalid doctor specified.")

        if AppointmentService.check_doctor_conflict(doctor_id, scheduled_time, duration_minutes):
            doctor_name = doctor.name
            time_str = scheduled_time.strftime('%Y-%m-%d %H:%M')
            raise AppointmentConflictError(
                f"Doctor {doctor_name} already has an appointment overlapping with {time_str} ({duration_minutes} min)."
            )

        appointment = Appointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            scheduled_time=scheduled_time,
            duration_minutes=duration_minutes,
            status=AppointmentStatus.SCHEDULED,
            reason=reason.strip(),
            notes=notes.strip() if notes else None
        )
        db.session.add(appointment)
        db.session.commit()
        return appointment

    @staticmethod
    def reschedule_appointment(
        appointment_id: int,
        new_scheduled_time: datetime,
        new_duration_minutes: int = 30,
        notes: Optional[str] = None
    ) -> Appointment:
        appointment = db.session.get(Appointment, appointment_id)
        if not appointment:
            raise ValueError("Appointment not found.")

        if appointment.status in [AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED]:
            raise AppointmentStateError(f"Cannot reschedule an appointment that is already {appointment.status}.")

        if AppointmentService.check_doctor_conflict(
            appointment.doctor_id,
            new_scheduled_time,
            new_duration_minutes,
            exclude_appointment_id=appointment.id
        ):
            raise AppointmentConflictError(
                f"Doctor schedule conflict at {new_scheduled_time.strftime('%Y-%m-%d %H:%M')}."
            )

        appointment.scheduled_time = new_scheduled_time
        appointment.duration_minutes = new_duration_minutes
        if notes:
            appointment.notes = notes.strip()
        # If rescheduled after being checked in, optionally reset to scheduled
        if appointment.status == AppointmentStatus.CHECKED_IN:
            appointment.status = AppointmentStatus.SCHEDULED
            appointment.check_in_time = None

        db.session.commit()
        return appointment

    @staticmethod
    def transition_status(appointment_id: int, target_status: str, notes: Optional[str] = None) -> Appointment:
        appointment = db.session.get(Appointment, appointment_id)
        if not appointment:
            raise ValueError("Appointment not found.")

        if not appointment.can_transition_to(target_status):
            raise AppointmentStateError(
                f"Cannot change status from '{appointment.status}' to '{target_status}'. "
                f"Allowed transitions: {AppointmentStatus.VALID_TRANSITIONS.get(appointment.status, [])}"
            )

        appointment.status = target_status
        if target_status == AppointmentStatus.CHECKED_IN:
            appointment.check_in_time = datetime.now(timezone.utc)
        if notes:
            if appointment.notes:
                appointment.notes += f"\n[{target_status.upper()}]: {notes.strip()}"
            else:
                appointment.notes = f"[{target_status.upper()}]: {notes.strip()}"

        db.session.commit()
        return appointment

    @staticmethod
    def get_waiting_queue(target_date: Optional[date] = None, doctor_id: Optional[int] = None) -> List[Appointment]:
        """
        Returns patients waiting in clinic today (checked in or currently in consultation),
        sorted by check_in_time ascending.
        """
        if not target_date:
            target_date = datetime.now().date()

        start_dt = datetime.combine(target_date, datetime.min.time())
        end_dt = datetime.combine(target_date, datetime.max.time())

        query = Appointment.query.filter(
            Appointment.scheduled_time >= start_dt,
            Appointment.scheduled_time <= end_dt,
            Appointment.status.in_([AppointmentStatus.CHECKED_IN, AppointmentStatus.IN_CONSULTATION])
        )

        if doctor_id:
            query = query.filter(Appointment.doctor_id == doctor_id)

        # Ordering: in_consultation first, then checked_in by check_in_time
        # Use case expression or python sort
        appointments = query.all()
        # Sort in_consultation first, then earliest check-in time
        def queue_key(a: Appointment):
            is_in_consult = 0 if a.status == AppointmentStatus.IN_CONSULTATION else 1
            check_in = a.check_in_time or a.scheduled_time
            return (is_in_consult, check_in)

        return sorted(appointments, key=queue_key)

    @staticmethod
    def get_daily_schedule(
        target_date: date,
        doctor_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[Appointment]:
        start_dt = datetime.combine(target_date, datetime.min.time())
        end_dt = datetime.combine(target_date, datetime.max.time())

        query = Appointment.query.filter(
            Appointment.scheduled_time >= start_dt,
            Appointment.scheduled_time <= end_dt
        )

        if doctor_id:
            query = query.filter(Appointment.doctor_id == doctor_id)
        if status:
            query = query.filter(Appointment.status == status)

        return query.order_by(Appointment.scheduled_time.asc()).all()
