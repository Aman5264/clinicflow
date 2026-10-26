from decimal import Decimal, InvalidOperation
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response
from flask_login import current_user
from app.extensions import db
from app.models.billing import Invoice, InvoiceItem, Payment, InvoiceStatus, PaymentMethod
from app.models.patient import Patient
from app.models.visit import Visit
from app.forms import InvoiceCreateForm, PaymentForm, InvoiceCancelForm
from app.services.billing_service import BillingService, BillingError, OverpaymentError
from app.services.pdf_service import PDFService
from app.security import staff_required

bp = Blueprint('billing', __name__)

@bp.route('/')
@staff_required
def index():
    status = request.args.get('status', '').strip() or None
    query = Invoice.query

    if status:
        query = query.filter_by(status=status)

    invoices = query.order_by(Invoice.created_at.desc()).all()
    return render_template('billing/index.html', invoices=invoices, selected_status=status, InvoiceStatus=InvoiceStatus)

@bp.route('/new', methods=['GET', 'POST'])
@staff_required
def create():
    form = InvoiceCreateForm()
    patients = Patient.query.filter_by(is_archived=False).order_by(Patient.full_name).all()
    form.patient_id.choices = [(p.id, f"{p.full_name} ({p.patient_code})") for p in patients]

    # Pre-select patient / visit if passed in GET
    patient_arg = request.args.get('patient_id', type=int)
    visit_arg = request.args.get('visit_id', type=int)

    if request.method == 'GET':
        if patient_arg and any(p.id == patient_arg for p in patients):
            form.patient_id.data = patient_arg

    # Populate visits choices for the selected patient
    visits = []
    if form.patient_id.data or patient_arg:
        pid = form.patient_id.data or patient_arg
        visits = Visit.query.filter_by(patient_id=pid).order_by(Visit.start_time.desc()).all()

    form.visit_id.choices = [(0, '-- None (Direct Billing) --')] + [
        (v.id, f"Visit #{v.id} ({v.start_time.strftime('%Y-%m-%d')} - {v.diagnosis[:30]})") for v in visits
    ]

    if form.validate_on_submit():
        descriptions = request.form.getlist('item_desc[]')
        quantities = request.form.getlist('item_qty[]')
        prices = request.form.getlist('item_price[]')

        items_data = []
        for i in range(len(descriptions)):
            desc = descriptions[i].strip() if i < len(descriptions) else ''
            if desc:
                try:
                    qty = int(quantities[i]) if i < len(quantities) else 1
                    price = Decimal(prices[i]) if i < len(prices) else Decimal('0.00')
                    items_data.append({
                        'description': desc,
                        'quantity': qty,
                        'unit_price': price
                    })
                except (ValueError, InvalidOperation):
                    flash(f"Invalid quantity or price for '{desc}'.", "danger")
                    return render_template('billing/form.html', form=form, title="Create New Invoice")

        if not items_data:
            flash("Please add at least one line item.", "danger")
            return render_template('billing/form.html', form=form, title="Create New Invoice")

        try:
            discount = Decimal(str(form.discount.data or '0.00'))
        except InvalidOperation:
            discount = Decimal('0.00')

        try:
            v_id = form.visit_id.data if form.visit_id.data != 0 else None
            invoice = BillingService.create_invoice(
                patient_id=form.patient_id.data,
                items_data=items_data,
                visit_id=v_id,
                discount=discount,
                notes=form.notes.data,
                created_by_id=current_user.id
            )
            flash(f"Invoice {invoice.invoice_number} created successfully.", "success")
            return redirect(url_for('billing.detail', invoice_id=invoice.id))
        except BillingError as be:
            flash(str(be), "danger")

    return render_template('billing/form.html', form=form, title="Create New Invoice")

@bp.route('/<int:invoice_id>')
@staff_required
def detail(invoice_id):
    invoice = db.get_or_404(Invoice, invoice_id)
    payment_form = PaymentForm()
    cancel_form = InvoiceCancelForm()
    return render_template(
        'billing/detail.html',
        invoice=invoice,
        payment_form=payment_form,
        cancel_form=cancel_form,
        PaymentMethod=PaymentMethod
    )

@bp.route('/<int:invoice_id>/pay', methods=['POST'])
@staff_required
def pay(invoice_id):
    invoice = db.get_or_404(Invoice, invoice_id)
    payment_form = PaymentForm()

    if payment_form.validate_on_submit():
        try:
            amt = Decimal(str(payment_form.amount.data.strip()))
            payment = BillingService.record_payment(
                invoice_id=invoice.id,
                amount=amt,
                payment_method=payment_form.payment_method.data,
                received_by_id=current_user.id,
                reference=payment_form.reference.data,
                notes=payment_form.notes.data
            )
            flash(f"Payment of ${amt:.2f} recorded successfully (Receipt #{payment.receipt_number}).", "success")
            return redirect(url_for('billing.detail', invoice_id=invoice.id))
        except OverpaymentError as oe:
            flash(str(oe), "danger")
        except (BillingError, InvalidOperation) as e:
            flash(str(e), "danger")
    else:
        for err in payment_form.amount.errors:
            flash(f"Payment error: {err}", "danger")

    return redirect(url_for('billing.detail', invoice_id=invoice.id))

@bp.route('/<int:invoice_id>/cancel', methods=['POST'])
@staff_required
def cancel(invoice_id):
    cancel_form = InvoiceCancelForm()
    if cancel_form.validate_on_submit():
        try:
            BillingService.cancel_invoice(
                invoice_id=invoice_id,
                reason=cancel_form.cancellation_reason.data,
                user_id=current_user.id
            )
            flash("Invoice has been successfully cancelled.", "info")
        except BillingError as be:
            flash(str(be), "danger")
    else:
        for err in cancel_form.cancellation_reason.errors:
            flash(f"Cancellation error: {err}", "danger")

    return redirect(url_for('billing.detail', invoice_id=invoice_id))

@bp.route('/<int:invoice_id>/pdf')
@staff_required
def invoice_pdf(invoice_id):
    invoice = db.get_or_404(Invoice, invoice_id)
    pdf_bytes = PDFService.generate_invoice_pdf(invoice)
    filename = f"Invoice_{invoice.invoice_number}.pdf"
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )

@bp.route('/payment/<int:payment_id>/pdf')
@staff_required
def receipt_pdf(payment_id):
    payment = db.get_or_404(Payment, payment_id)
    pdf_bytes = PDFService.generate_receipt_pdf(payment)
    filename = f"Receipt_{payment.receipt_number}.pdf"
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )
