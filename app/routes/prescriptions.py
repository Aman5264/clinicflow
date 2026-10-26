from flask import Blueprint, render_template, redirect, url_for, flash, request, Response
from flask_login import current_user
from app.extensions import db
from app.models.prescription import Prescription, PrescriptionItem
from app.models.visit import Visit
from app.forms import PrescriptionCreateForm
from app.services.prescription_service import PrescriptionService
from app.services.pdf_service import PDFService
from app.security import clinical_required, staff_required

bp = Blueprint('prescriptions', __name__)

@bp.route('/visit/<int:visit_id>/new', methods=['GET', 'POST'])
@clinical_required
def create(visit_id):
    visit = db.get_or_404(Visit, visit_id)
    form = PrescriptionCreateForm()

    if form.validate_on_submit():
        med_names = request.form.getlist('med_name[]')
        strengths = request.form.getlist('strength[]')
        dosages = request.form.getlist('dosage[]')
        routes = request.form.getlist('route[]')
        frequencies = request.form.getlist('frequency[]')
        durations = request.form.getlist('duration[]')
        instructions = request.form.getlist('instructions[]')

        items_data = []
        for i in range(len(med_names)):
            name = med_names[i].strip() if i < len(med_names) else ''
            if name:
                items_data.append({
                    'medicine_name': name,
                    'strength': strengths[i].strip() if i < len(strengths) else 'Standard',
                    'dosage': dosages[i].strip() if i < len(dosages) else '1 unit',
                    'route': routes[i].strip() if i < len(routes) else 'Oral',
                    'frequency': frequencies[i].strip() if i < len(frequencies) else 'Once daily',
                    'duration': durations[i].strip() if i < len(durations) else '7 days',
                    'instructions': instructions[i].strip() if i < len(instructions) else None
                })

        if not items_data:
            flash("Please add at least one medication item to the prescription.", "danger")
            return render_template('prescriptions/form.html', form=form, visit=visit, title="Issue Prescription")

        try:
            rx = PrescriptionService.create_prescription(
                visit_id=visit.id,
                doctor_id=current_user.id,
                items_data=items_data,
                notes=form.notes.data
            )
            flash(f"Prescription {rx.prescription_number} issued successfully.", "success")
            return redirect(url_for('prescriptions.detail', prescription_id=rx.id))
        except ValueError as ve:
            flash(str(ve), "danger")

    return render_template('prescriptions/form.html', form=form, visit=visit, title="Issue Prescription")

@bp.route('/<int:prescription_id>')
@staff_required
def detail(prescription_id):
    rx = db.get_or_404(Prescription, prescription_id)
    return render_template('prescriptions/detail.html', prescription=rx)

@bp.route('/<int:prescription_id>/pdf')
@staff_required
def download_pdf(prescription_id):
    rx = db.get_or_404(Prescription, prescription_id)
    pdf_bytes = PDFService.generate_prescription_pdf(rx)
    filename = f"Prescription_{rx.prescription_number}.pdf"
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )

@bp.route('/<int:prescription_id>/edit', methods=['GET', 'POST'])
@clinical_required
def edit(prescription_id):
    rx = db.get_or_404(Prescription, prescription_id)
    form = PrescriptionCreateForm()

    if request.method == 'GET':
        form.notes.data = rx.notes

    if form.validate_on_submit():
        med_names = request.form.getlist('med_name[]')
        strengths = request.form.getlist('strength[]')
        dosages = request.form.getlist('dosage[]')
        routes = request.form.getlist('route[]')
        frequencies = request.form.getlist('frequency[]')
        durations = request.form.getlist('duration[]')
        instructions = request.form.getlist('instructions[]')

        items_data = []
        for i in range(len(med_names)):
            name = med_names[i].strip() if i < len(med_names) else ''
            if name:
                items_data.append({
                    'medicine_name': name,
                    'strength': strengths[i].strip() if i < len(strengths) else 'Standard',
                    'dosage': dosages[i].strip() if i < len(dosages) else '1 unit',
                    'route': routes[i].strip() if i < len(routes) else 'Oral',
                    'frequency': frequencies[i].strip() if i < len(frequencies) else 'Once daily',
                    'duration': durations[i].strip() if i < len(durations) else '7 days',
                    'instructions': instructions[i].strip() if i < len(instructions) else None
                })

        if not items_data:
            flash("Please keep at least one medication item.", "danger")
            return render_template('prescriptions/form.html', form=form, visit=rx.visit, prescription=rx, title=f"Amend Prescription {rx.prescription_number}")

        try:
            PrescriptionService.update_prescription(
                prescription_id=rx.id,
                items_data=items_data,
                notes=form.notes.data
            )
            flash(f"Prescription {rx.prescription_number} updated successfully.", "success")
            return redirect(url_for('prescriptions.detail', prescription_id=rx.id))
        except ValueError as ve:
            flash(str(ve), "danger")

    return render_template('prescriptions/form.html', form=form, visit=rx.visit, prescription=rx, title=f"Amend Prescription {rx.prescription_number}")
