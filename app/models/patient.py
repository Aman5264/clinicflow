import random
import string
from datetime import datetime, timezone
from app.extensions import db

def generate_patient_code():
    timestamp = datetime.now().strftime('%y%m%d')
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f'PAT-{timestamp}-{suffix}'

class Patient(db.Model):
    __tablename__ = 'patients'

    id = db.Column(db.Integer, primary_key=True)
    patient_code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(120), nullable=False, index=True)
    date_of_birth = db.Column(db.Date, nullable=False)
    phone = db.Column(db.String(25), nullable=False, index=True)
    address = db.Column(db.Text, nullable=False)
    emergency_contact = db.Column(db.String(120), nullable=False)
    is_archived = db.Column(db.Boolean, default=False, nullable=False, index=True)
    archive_reason = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def __init__(self, **kwargs):
        if 'patient_code' not in kwargs or not kwargs['patient_code']:
            kwargs['patient_code'] = generate_patient_code()
        super().__init__(**kwargs)

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        today = datetime.now().date()
        born = self.date_of_birth
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    def __repr__(self):
        return f'<Patient {self.patient_code} - {self.full_name}>'
