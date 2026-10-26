from datetime import datetime, timezone
from app.extensions import db

class AppointmentStatus:
    SCHEDULED = 'scheduled'
    CHECKED_IN = 'checked_in'
    IN_CONSULTATION = 'in_consultation'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    NO_SHOW = 'no_show'

    ALL_STATUSES = [SCHEDULED, CHECKED_IN, IN_CONSULTATION, COMPLETED, CANCELLED, NO_SHOW]
    ACTIVE_STATUSES = [SCHEDULED, CHECKED_IN, IN_CONSULTATION]

    # Valid state transitions
    VALID_TRANSITIONS = {
        SCHEDULED: [CHECKED_IN, CANCELLED, NO_SHOW],
        CHECKED_IN: [IN_CONSULTATION, CANCELLED],
        IN_CONSULTATION: [COMPLETED, CANCELLED],
        COMPLETED: [],
        CANCELLED: [],
        NO_SHOW: []
    }

class Appointment(db.Model):
    __tablename__ = 'appointments'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    scheduled_time = db.Column(db.DateTime, nullable=False, index=True)
    duration_minutes = db.Column(db.Integer, default=30, nullable=False)
    status = db.Column(db.String(30), default=AppointmentStatus.SCHEDULED, nullable=False, index=True)
    reason = db.Column(db.String(255), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    check_in_time = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    patient = db.relationship('Patient', backref=db.backref('appointments', lazy='dynamic', cascade='all, delete-orphan'))
    doctor = db.relationship('User', backref=db.backref('doctor_appointments', lazy='dynamic'))

    def can_transition_to(self, target_status: str) -> bool:
        allowed = AppointmentStatus.VALID_TRANSITIONS.get(self.status, [])
        return target_status in allowed

    def __repr__(self):
        return f'<Appointment {self.id}: Patient {self.patient_id} with Doctor {self.doctor_id} @ {self.scheduled_time} ({self.status})>'
