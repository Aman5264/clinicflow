from datetime import datetime, date, time
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.appointment import Appointment, AppointmentStatus
from app.models.user import User, Role
from app.models.patient import Patient
from app.forms import AppointmentForm, AppointmentRescheduleForm, AppointmentStatusUpdateForm
from app.services.appointment_service import (
    AppointmentService,
    AppointmentConflictError,
    AppointmentStateError
)
from app.security import staff_required

bp = Blueprint('appointments', __name__)

@bp.route('/')
@staff_required
def index():
    # Filter by date (default to today)
    date_str = request.args.get('date', '').strip()
    if date_str:
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            target_date = datetime.now().date()
    else:
        target_date = datetime.now().date()

    doctor_id = request.args.get('doctor_id', type=int)
    status = request.args.get('status', '').strip() or None

    appointments = AppointmentService.get_daily_schedule(
        target_date=target_date,
        doctor_id=doctor_id if doctor_id else None,
        status=status
    )

    doctors = User.query.filter(User.role.in_([Role.DOCTOR, Role.ADMIN]), User.is_active == True).order_by(User.name).all()

    return render_template(
        'appointments/index.html',
        appointments=appointments,
        target_date=target_date,
        selected_doctor_id=doctor_id,
        selected_status=status,
        doctors=doctors,
        AppointmentStatus=AppointmentStatus
    )

@bp.route('/queue')
@staff_required
def queue():
    doctor_id = request.args.get('doctor_id', type=int)
    waiting_queue = AppointmentService.get_waiting_queue(
        target_date=datetime.now().date(),
        doctor_id=doctor_id if doctor_id else None
    )
    doctors = User.query.filter(User.role.in_([Role.DOCTOR, Role.ADMIN]), User.is_active == True).order_by(User.name).all()

    return render_template(
        'appointments/queue.html',
        queue=waiting_queue,
        selected_doctor_id=doctor_id,
        doctors=doctors,
        AppointmentStatus=AppointmentStatus
    )

@bp.route('/book', methods=['GET', 'POST'])
@staff_required
def book():
    form = AppointmentForm()
    # Populate dropdown choices dynamically
    patients = Patient.query.filter_by(is_archived=False).order_by(Patient.full_name).all()
    form.patient_id.choices = [(p.id, f"{p.full_name} ({p.patient_code})") for p in patients]

    doctors = User.query.filter(User.role.in_([Role.DOCTOR, Role.ADMIN]), User.is_active == True).order_by(User.name).all()
    form.doctor_id.choices = [(d.id, f"Dr. {d.name} ({d.role.capitalize()})") for d in doctors]

    # Pre-select patient if passed in query
    patient_arg = request.args.get('patient_id', type=int)
    if request.method == 'GET':
        if patient_arg and any(p.id == patient_arg for p in patients):
            form.patient_id.data = patient_arg
        form.appointment_date.data = datetime.now().date()
        form.appointment_time.data = "09:00"

    if form.validate_on_submit():
        time_parts = [int(p) for p in form.appointment_time.data.split(':')]
        scheduled_dt = datetime.combine(
            form.appointment_date.data,
            time(hour=time_parts[0], minute=time_parts[1])
        )

        try:
            appointment = AppointmentService.book_appointment(
                patient_id=form.patient_id.data,
                doctor_id=form.doctor_id.data,
                scheduled_time=scheduled_dt,
                duration_minutes=form.duration_minutes.data,
                reason=form.reason.data,
                notes=form.notes.data
            )
            flash(
                f"Appointment booked successfully for {appointment.patient.full_name} on {scheduled_dt.strftime('%d %b %Y at %H:%M')}.",
                'success'
            )
            return redirect(url_for('appointments.index', date=form.appointment_date.data.strftime('%Y-%m-%d')))
        except AppointmentConflictError as ace:
            flash(str(ace), 'warning')
        except ValueError as ve:
            flash(str(ve), 'danger')

    return render_template('appointments/book.html', form=form, title="Book New Appointment")

@bp.route('/<int:appointment_id>/reschedule', methods=['GET', 'POST'])
@staff_required
def reschedule(appointment_id):
    appointment = db.get_or_404(Appointment, appointment_id)
    form = AppointmentRescheduleForm()

    if request.method == 'GET':
        form.appointment_date.data = appointment.scheduled_time.date()
        form.appointment_time.data = appointment.scheduled_time.strftime('%H:%M')
        form.duration_minutes.data = appointment.duration_minutes
        form.notes.data = appointment.notes

    if form.validate_on_submit():
        time_parts = [int(p) for p in form.appointment_time.data.split(':')]
        new_dt = datetime.combine(
            form.appointment_date.data,
            time(hour=time_parts[0], minute=time_parts[1])
        )

        try:
            AppointmentService.reschedule_appointment(
                appointment_id=appointment.id,
                new_scheduled_time=new_dt,
                new_duration_minutes=form.duration_minutes.data,
                notes=form.notes.data
            )
            flash(f"Appointment rescheduled to {new_dt.strftime('%d %b %Y at %H:%M')}.", 'success')
            return redirect(url_for('appointments.index', date=new_dt.strftime('%Y-%m-%d')))
        except AppointmentConflictError as ace:
            flash(str(ace), 'warning')
        except AppointmentStateError as ase:
            flash(str(ase), 'danger')

    return render_template('appointments/reschedule.html', form=form, appointment=appointment)

@bp.route('/<int:appointment_id>/transition/<target_status>', methods=['POST'])
@staff_required
def transition(appointment_id, target_status):
    try:
        appointment = AppointmentService.transition_status(appointment_id, target_status)
        flash(f"Appointment status updated to '{target_status.replace('_', ' ').capitalize()}'.", 'success')
    except (AppointmentStateError, ValueError) as e:
        flash(str(e), 'danger')

    # Return to previous page or queue
    ref = request.referrer
    if ref and ('queue' in ref or 'appointments' in ref or 'patients' in ref):
        return redirect(ref)
    return redirect(url_for('appointments.queue'))
