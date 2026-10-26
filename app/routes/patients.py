from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user
from sqlalchemy import or_
from app.extensions import db
from app.models.patient import Patient
from app.forms import PatientForm, PatientArchiveForm
from app.security import staff_required, admin_required, clinical_required

bp = Blueprint('patients', __name__)

@bp.route('/')
@staff_required
def index():
    search_query = request.args.get('q', '').strip()
    include_archived = request.args.get('archived', '0') == '1'
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('ITEMS_PER_PAGE', 10)

    query = Patient.query

    if not include_archived:
        query = query.filter_by(is_archived=False)

    if search_query:
        search_filter = or_(
            Patient.full_name.ilike(f'%{search_query}%'),
            Patient.patient_code.ilike(f'%{search_query}%'),
            Patient.phone.ilike(f'%{search_query}%')
        )
        query = query.filter(search_filter)

    pagination = query.order_by(Patient.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    patients = pagination.items

    return render_template(
        'patients/index.html',
        patients=patients,
        pagination=pagination,
        search_query=search_query,
        include_archived=include_archived
    )

@bp.route('/register', methods=['GET', 'POST'])
@staff_required
def register():
    form = PatientForm()
    if form.validate_on_submit():
        # Duplicate record check based on name, DOB, and phone
        existing_duplicate = Patient.query.filter(
            Patient.full_name.ilike(form.full_name.data.strip()),
            Patient.date_of_birth == form.date_of_birth.data,
            Patient.phone == form.phone.data.strip(),
            Patient.is_archived == False
        ).first()

        if existing_duplicate:
            flash(
                f'A patient with matching name, birth date, and phone number already exists '
                f'({existing_duplicate.patient_code}). Please review existing records before creating a duplicate.',
                'warning'
            )
            return render_template('patients/form.html', form=form, title='Register New Patient')

        patient = Patient(
            full_name=form.full_name.data.strip(),
            date_of_birth=form.date_of_birth.data,
            phone=form.phone.data.strip(),
            address=form.address.data.strip(),
            emergency_contact=form.emergency_contact.data.strip()
        )
        try:
            db.session.add(patient)
            db.session.commit()
            flash(f'Patient {patient.full_name} registered successfully with code {patient.patient_code}.', 'success')
            return redirect(url_for('patients.detail', patient_id=patient.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Database error during patient registration: {str(e)}', 'danger')

    return render_template('patients/form.html', form=form, title='Register New Patient')

@bp.route('/<int:patient_id>')
@staff_required
def detail(patient_id):
    patient = db.get_or_404(Patient, patient_id)
    archive_form = PatientArchiveForm()
    return render_template('patients/detail.html', patient=patient, archive_form=archive_form)

@bp.route('/<int:patient_id>/edit', methods=['GET', 'POST'])
@staff_required
def edit(patient_id):
    patient = db.get_or_404(Patient, patient_id)
    form = PatientForm(obj=patient)

    if form.validate_on_submit():
        # Duplicate check excluding current patient
        duplicate = Patient.query.filter(
            Patient.full_name.ilike(form.full_name.data.strip()),
            Patient.date_of_birth == form.date_of_birth.data,
            Patient.phone == form.phone.data.strip(),
            Patient.id != patient.id,
            Patient.is_archived == False
        ).first()

        if duplicate:
            flash(
                f'Another active patient with matching details exists ({duplicate.patient_code}).',
                'warning'
            )
            return render_template('patients/form.html', form=form, patient=patient, title=f'Edit Patient: {patient.patient_code}')

        patient.full_name = form.full_name.data.strip()
        patient.date_of_birth = form.date_of_birth.data
        patient.phone = form.phone.data.strip()
        patient.address = form.address.data.strip()
        patient.emergency_contact = form.emergency_contact.data.strip()

        try:
            db.session.commit()
            flash(f'Patient record for {patient.patient_code} updated successfully.', 'success')
            return redirect(url_for('patients.detail', patient_id=patient.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to update patient record: {str(e)}', 'danger')

    return render_template('patients/form.html', form=form, patient=patient, title=f'Edit Patient: {patient.patient_code}')

@bp.route('/<int:patient_id>/archive', methods=['POST'])
@staff_required
def archive(patient_id):
    patient = db.get_or_404(Patient, patient_id)
    form = PatientArchiveForm()

    if form.validate_on_submit():
        patient.is_archived = True
        patient.archive_reason = form.archive_reason.data.strip()
        try:
            db.session.commit()
            flash(f'Patient {patient.patient_code} has been archived.', 'info')
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to archive patient: {str(e)}', 'danger')
    else:
        for err in form.archive_reason.errors:
            flash(f'Archive error: {err}', 'danger')

    return redirect(url_for('patients.detail', patient_id=patient.id))

@bp.route('/<int:patient_id>/restore', methods=['POST'])
@staff_required
def restore(patient_id):
    patient = db.get_or_404(Patient, patient_id)
    patient.is_archived = False
    patient.archive_reason = None
    try:
        db.session.commit()
        flash(f'Patient {patient.patient_code} has been restored to active status.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to restore patient: {str(e)}', 'danger')

    return redirect(url_for('patients.detail', patient_id=patient.id))
