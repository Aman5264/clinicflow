from datetime import datetime, timezone
from app.extensions import db

class Visit(db.Model):
    __tablename__ = 'visits'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id', ondelete='SET NULL'), nullable=True, unique=True, index=True)
    symptoms = db.Column(db.Text, nullable=False)
    diagnosis = db.Column(db.Text, nullable=False)
    clinical_notes = db.Column(db.Text, nullable=True)
    start_time = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    patient = db.relationship('Patient', backref=db.backref('visits', lazy='dynamic', cascade='all, delete-orphan'))
    doctor = db.relationship('User', backref=db.backref('doctor_visits', lazy='dynamic'))
    appointment = db.relationship('Appointment', backref=db.backref('visit', uselist=False))

    def __repr__(self):
        return f'<Visit {self.id}: Patient {self.patient_id} by Doctor {self.doctor_id} @ {self.start_time}>'

class ClinicalAuditLog(db.Model):
    __tablename__ = 'clinical_audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action = db.Column(db.String(50), nullable=False)  # 'created', 'updated'
    changes_json = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    visit = db.relationship('Visit', backref=db.backref('audit_logs', lazy='dynamic', cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('audit_actions', lazy='dynamic'))

    def __repr__(self):
        return f'<ClinicalAuditLog {self.id}: Visit {self.visit_id} {self.action} by User {self.user_id}>'
