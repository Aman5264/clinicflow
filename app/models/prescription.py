import random
import string
from datetime import datetime, timezone
from app.extensions import db

def generate_rx_number():
    timestamp = datetime.now().strftime('%y%m%d')
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f'RX-{timestamp}-{suffix}'

class Prescription(db.Model):
    __tablename__ = 'prescriptions'

    id = db.Column(db.Integer, primary_key=True)
    prescription_number = db.Column(db.String(32), unique=True, nullable=False, index=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id', ondelete='CASCADE'), nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False, index=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def __init__(self, **kwargs):
        if 'prescription_number' not in kwargs or not kwargs['prescription_number']:
            kwargs['prescription_number'] = generate_rx_number()
        super().__init__(**kwargs)

    # Relationships
    visit = db.relationship('Visit', backref=db.backref('prescriptions', lazy='dynamic', cascade='all, delete-orphan'))
    doctor = db.relationship('User', backref=db.backref('authored_prescriptions', lazy='dynamic'))
    patient = db.relationship('Patient', backref=db.backref('prescriptions', lazy='dynamic', cascade='all, delete-orphan'))
    items = db.relationship('PrescriptionItem', backref='prescription', cascade='all, delete-orphan', lazy='joined')

    def __repr__(self):
        return f'<Prescription {self.prescription_number} (Visit #{self.visit_id})>'

class PrescriptionItem(db.Model):
    __tablename__ = 'prescription_items'

    id = db.Column(db.Integer, primary_key=True)
    prescription_id = db.Column(db.Integer, db.ForeignKey('prescriptions.id', ondelete='CASCADE'), nullable=False, index=True)
    medicine_name = db.Column(db.String(120), nullable=False)
    strength = db.Column(db.String(50), nullable=False)    # e.g., '500 mg', '10 mg/5ml'
    dosage = db.Column(db.String(50), nullable=False)      # e.g., '1 tablet', '2 puffs'
    route = db.Column(db.String(50), nullable=False)       # e.g., 'Oral', 'Inhalation', 'Topical', 'Intravenous'
    frequency = db.Column(db.String(80), nullable=False)   # e.g., 'Twice daily after meals (BID)', 'Every 8 hours'
    duration = db.Column(db.String(50), nullable=False)    # e.g., '7 days', '30 days'
    instructions = db.Column(db.Text, nullable=True)       # e.g., 'Take with plenty of water. Finish entire course.'

    def __repr__(self):
        return f'<PrescriptionItem {self.medicine_name} {self.strength}>'
