from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.visit import Visit, ClinicalAuditLog
from app.models.patient import Patient
from app.models.appointment import Appointment, AppointmentStatus
from app.forms import VisitForm
from app.services.consultation_service import ConsultationService, ConsultationError
from app.security import clinical_required

bp = Blueprint('consultations', __name__)

@bp.route('/new', methods=['GET', 'POST'])
@clinical_required
def new_visit():
    patient_id = request.args.get('patient_id', type=int)
    appointment_id = request.args.get('appointment_id', type=int)

    if not patient_id and appointment_id:
        apt = db.get_or_404(Appointment, appointment_id)
        patient_id = apt.patient_id

    patient = db.get_or_404(Patient, patient_id)
    appointment = db.session.get(Appointment, appointment_id) if appointment_id else None

    # Check if a visit already exists for this appointment
    if appointment and appointment.visit:
        flash("A consultation record already exists for this appointment. Redirecting to existing record.", "info")
        return redirect(url_for('consultations.detail', visit_id=appointment.visit.id))

    form = VisitForm()
    if request.method == 'GET' and appointment:
        # Pre-fill chief complaint with appointment reason
        form.symptoms.data = appointment.reason

    if form.validate_on_submit():
        try:
            visit = ConsultationService.create_visit(
                patient_id=patient.id,
                doctor_id=current_user.id,
                symptoms=form.symptoms.data,
                diagnosis=form.diagnosis.data,
                clinical_notes=form.clinical_notes.data,
                appointment_id=appointment.id if appointment else None,
                author_user_id=current_user.id
            )
            flash(f"Clinical encounter recorded successfully for {patient.full_name}.", "success")
            return redirect(url_for('consultations.detail', visit_id=visit.id))
        except (ConsultationError, ValueError) as e:
            flash(str(e), "danger")

    return render_template(
        'consultations/form.html',
        form=form,
        patient=patient,
        appointment=appointment,
        title="New Clinical Consultation"
    )

@bp.route('/<int:visit_id>')
@clinical_required
def detail(visit_id):
    visit = db.get_or_404(Visit, visit_id)
    audit_logs = visit.audit_logs.order_by(ClinicalAuditLog.timestamp.desc()).all()
    return render_template('consultations/detail.html', visit=visit, audit_logs=audit_logs)

@bp.route('/<int:visit_id>/edit', methods=['GET', 'POST'])
@clinical_required
def edit(visit_id):
    visit = db.get_or_404(Visit, visit_id)
    form = VisitForm(obj=visit)

    if form.validate_on_submit():
        try:
            ConsultationService.update_visit(
                visit_id=visit.id,
                symptoms=form.symptoms.data,
                diagnosis=form.diagnosis.data,
                clinical_notes=form.clinical_notes.data,
                author_user_id=current_user.id
            )
            flash("Clinical record updated and audit log saved.", "success")
            return redirect(url_for('consultations.detail', visit_id=visit.id))
        except (ConsultationError, ValueError) as e:
            flash(str(e), "danger")

    return render_template(
        'consultations/form.html',
        form=form,
        patient=visit.patient,
        appointment=visit.appointment,
        visit=visit,
        title=f"Edit Clinical Consultation - Visit #{visit.id}"
    )
