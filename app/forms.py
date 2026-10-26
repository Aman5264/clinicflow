import re
from datetime import date
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, DateField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Optional
from app.models.user import Role

def sanitize_phone(phone_str):
    """Keep only digits and optional leading plus sign."""
    if not phone_str:
        return ''
    cleaned = re.sub(r'[^\d+]', '', phone_str.strip())
    return cleaned

EMAIL_REGEX = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

def validate_email_format(form, field):
    if not field.data or not EMAIL_REGEX.match(field.data.strip()):
        raise ValidationError('Please provide a valid email address.')

class LoginForm(FlaskForm):
    email = StringField('Email Address', validators=[
        DataRequired(message='Email is required.'),
        validate_email_format
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required.')
    ])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[
        DataRequired(message='Current password is required.')
    ])
    new_password = PasswordField('New Password', validators=[
        DataRequired(message='New password is required.'),
        Length(min=8, message='Password must be at least 8 characters long.')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(message='Please confirm your new password.'),
        EqualTo('new_password', message='Passwords must match.')
    ])
    submit = SubmitField('Update Password')

class UserCreateForm(FlaskForm):
    name = StringField('Full Name', validators=[
        DataRequired(message='Name is required.'),
        Length(min=2, max=100, message='Name must be between 2 and 100 characters.')
    ])
    email = StringField('Email Address', validators=[
        DataRequired(message='Email is required.'),
        validate_email_format
    ])
    role = SelectField('Role', choices=[
        (Role.RECEPTIONIST, 'Receptionist'),
        (Role.DOCTOR, 'Doctor'),
        (Role.ADMIN, 'Administrator')
    ], validators=[DataRequired()])
    password = PasswordField('Temporary Password', validators=[
        DataRequired(message='Temporary password is required.'),
        Length(min=8, message='Password must be at least 8 characters long.')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message='Please confirm password.'),
        EqualTo('password', message='Passwords must match.')
    ])
    submit = SubmitField('Create User')

class UserEditForm(FlaskForm):
    name = StringField('Full Name', validators=[
        DataRequired(message='Name is required.'),
        Length(min=2, max=100)
    ])
    email = StringField('Email Address', validators=[
        DataRequired(message='Email is required.'),
        validate_email_format
    ])
    role = SelectField('Role', choices=[
        (Role.RECEPTIONIST, 'Receptionist'),
        (Role.DOCTOR, 'Doctor'),
        (Role.ADMIN, 'Administrator')
    ], validators=[DataRequired()])
    is_active = BooleanField('Active Account')
    submit = SubmitField('Update User')

class PatientForm(FlaskForm):
    full_name = StringField('Full Name', validators=[
        DataRequired(message='Patient full name is required.'),
        Length(min=2, max=120, message='Name must be between 2 and 120 characters.')
    ])
    date_of_birth = DateField('Date of Birth', format='%Y-%m-%d', validators=[
        DataRequired(message='Valid date of birth is required (YYYY-MM-DD).')
    ])
    phone = StringField('Phone Number', validators=[
        DataRequired(message='Contact phone number is required.'),
        Length(min=7, max=25, message='Phone number must be between 7 and 25 characters.')
    ])
    address = TextAreaField('Address', validators=[
        DataRequired(message='Residential address is required.'),
        Length(min=5, max=500, message='Address must be between 5 and 500 characters.')
    ])
    emergency_contact = StringField('Emergency Contact (Name & Phone)', validators=[
        DataRequired(message='Emergency contact details are required.'),
        Length(min=3, max=120, message='Emergency contact must be between 3 and 120 characters.')
    ])
    submit = SubmitField('Save Patient')

    def validate_date_of_birth(self, field):
        if field.data and field.data > date.today():
            raise ValidationError('Date of birth cannot be in the future.')

    def validate_phone(self, field):
        cleaned = sanitize_phone(field.data)
        if not re.match(r'^\+?[0-9]{7,15}$', cleaned):
            raise ValidationError('Enter a valid phone number with 7 to 15 digits (optional leading +).')

class PatientArchiveForm(FlaskForm):
    archive_reason = StringField('Reason for Archiving', validators=[
        DataRequired(message='Please provide a reason for archiving this patient record.'),
        Length(min=3, max=250, message='Reason must be between 3 and 250 characters.')
    ])
    submit = SubmitField('Archive Patient')

class AppointmentForm(FlaskForm):
    patient_id = SelectField('Patient', coerce=int, validators=[DataRequired(message='Select a patient.')])
    doctor_id = SelectField('Doctor', coerce=int, validators=[DataRequired(message='Select an attending doctor.')])
    appointment_date = DateField('Date', format='%Y-%m-%d', validators=[DataRequired(message='Date is required.')])
    appointment_time = StringField('Time (HH:MM 24-hour)', validators=[
        DataRequired(message='Time is required (e.g. 09:30 or 14:00).')
    ])
    duration_minutes = SelectField('Duration', coerce=int, choices=[
        (15, '15 Minutes'),
        (30, '30 Minutes (Standard)'),
        (45, '45 Minutes'),
        (60, '60 Minutes (Comprehensive)')
    ], default=30)
    reason = StringField('Reason for Visit', validators=[
        DataRequired(message='Reason for visit is required.'),
        Length(min=3, max=255, message='Reason must be between 3 and 255 characters.')
    ])
    notes = TextAreaField('Scheduling Notes', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Book Appointment')

    def validate_appointment_time(self, field):
        pattern = r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$'
        if not re.match(pattern, field.data.strip()):
            raise ValidationError('Enter a valid 24-hour time in format HH:MM (e.g. 09:30, 14:15).')

class AppointmentRescheduleForm(FlaskForm):
    appointment_date = DateField('New Date', format='%Y-%m-%d', validators=[DataRequired(message='Date is required.')])
    appointment_time = StringField('New Time (HH:MM 24-hour)', validators=[
        DataRequired(message='Time is required (e.g. 09:30 or 14:00).')
    ])
    duration_minutes = SelectField('Duration', coerce=int, choices=[
        (15, '15 Minutes'),
        (30, '30 Minutes'),
        (45, '45 Minutes'),
        (60, '60 Minutes')
    ], default=30)
    notes = TextAreaField('Reason for Rescheduling / Notes', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Reschedule Appointment')

    def validate_appointment_time(self, field):
        pattern = r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$'
        if not re.match(pattern, field.data.strip()):
            raise ValidationError('Enter a valid 24-hour time in format HH:MM.')

class AppointmentStatusUpdateForm(FlaskForm):
    target_status = SelectField('Status', choices=[], validators=[DataRequired()])
    notes = TextAreaField('Transition Notes', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Update Status')

class VisitForm(FlaskForm):
    symptoms = TextAreaField('Symptoms & Chief Complaint', validators=[
        DataRequired(message='Please record the patient symptoms and complaint.'),
        Length(min=5, message='Must provide at least 5 characters.')
    ])
    diagnosis = TextAreaField('Assessment & Diagnosis', validators=[
        DataRequired(message='Clinical diagnosis or assessment is required.'),
        Length(min=5, message='Must provide at least 5 characters.')
    ])
    clinical_notes = TextAreaField('Physician Notes & Prescription / Plan', validators=[
        Optional(),
        Length(max=2000)
    ])
    submit = SubmitField('Save Clinical Consultation')

class PrescriptionItemForm(FlaskForm):
    medicine_name = StringField('Medication Name', validators=[DataRequired(message='Medicine name is required.')])
    strength = StringField('Strength', validators=[DataRequired(message='e.g. 500mg, 10mg/ml')])
    dosage = StringField('Dosage', validators=[DataRequired(message='e.g. 1 tablet, 2 capsules')])
    route = SelectField('Route', choices=[
        ('Oral', 'Oral'),
        ('Inhalation', 'Inhalation'),
        ('Topical', 'Topical'),
        ('Sublingual', 'Sublingual'),
        ('Intramuscular', 'Intramuscular'),
        ('Intravenous', 'Intravenous'),
        ('Ophthalmic', 'Ophthalmic (Eye)'),
        ('Otic', 'Otic (Ear)')
    ], default='Oral')
    frequency = StringField('Frequency', validators=[DataRequired(message='e.g. Twice daily (BID)')])
    duration = StringField('Duration', validators=[DataRequired(message='e.g. 7 days, 1 month')])
    instructions = TextAreaField('Patient Instructions', validators=[Optional(), Length(max=300)])

class PrescriptionCreateForm(FlaskForm):
    notes = TextAreaField('Special Instructions / Physician Notes', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Issue Prescription')

class InvoiceCreateForm(FlaskForm):
    patient_id = SelectField('Patient', coerce=int, validators=[DataRequired(message='Select a patient.')])
    visit_id = SelectField('Linked Consultation Visit', coerce=int, validators=[Optional()])
    discount = StringField('Discount Amount (₹ / INR)', default='0.00', validators=[DataRequired()])
    notes = TextAreaField('Billing Notes', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Generate Invoice')

class PaymentForm(FlaskForm):
    amount = StringField('Payment Amount (₹ / INR)', validators=[DataRequired(message='Amount is required.')])
    payment_method = SelectField('Payment Method', choices=[
        ('upi', 'UPI (Google Pay, PhonePe, Paytm, BHIM)'),
        ('cash', 'Cash (INR)'),
        ('card', 'Debit / Credit Card (RuPay, Visa, Mastercard)'),
        ('bank_transfer', 'Net Banking / NEFT / IMPS'),
        ('insurance', 'Mediclaim / TPA Insurance Claim')
    ], default='upi')
    reference = StringField('Transaction Ref / UPI UTR / Receipt No.', validators=[Optional(), Length(max=100)])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=300)])
    submit = SubmitField('Record Payment')

class InvoiceCancelForm(FlaskForm):
    cancellation_reason = StringField('Cancellation Reason', validators=[
        DataRequired(message='Reason for cancelling invoice is required.'),
        Length(min=3, max=250)
    ])
    submit = SubmitField('Cancel Invoice')

class DateRangeReportForm(FlaskForm):
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[DataRequired()])
    end_date = DateField('End Date', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Generate Report')


