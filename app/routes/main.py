from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user
from app.models.patient import Patient
from app.models.user import User
from app.models.appointment import Appointment, AppointmentStatus
from app.security import staff_required

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))

@bp.route('/dashboard')
@staff_required
def dashboard():
    today = datetime.now().date()
    start_dt = datetime.combine(today, datetime.min.time())
    end_dt = datetime.combine(today, datetime.max.time())

    total_active_patients = Patient.query.filter_by(is_archived=False).count()
    total_archived_patients = Patient.query.filter_by(is_archived=True).count()
    recent_patients = Patient.query.filter_by(is_archived=False).order_by(Patient.created_at.desc()).limit(5).all()

    today_appointments = Appointment.query.filter(
        Appointment.scheduled_time >= start_dt,
        Appointment.scheduled_time <= end_dt
    ).count()

    waiting_queue_count = Appointment.query.filter(
        Appointment.scheduled_time >= start_dt,
        Appointment.scheduled_time <= end_dt,
        Appointment.status.in_([AppointmentStatus.CHECKED_IN, AppointmentStatus.IN_CONSULTATION])
    ).count()

    user_count = User.query.filter_by(is_active=True).count() if current_user.is_admin() else None

    return render_template(
        'main/dashboard.html',
        total_active_patients=total_active_patients,
        total_archived_patients=total_archived_patients,
        recent_patients=recent_patients,
        today_appointments=today_appointments,
        waiting_queue_count=waiting_queue_count,
        user_count=user_count
    )
