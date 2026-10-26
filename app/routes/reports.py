import io
from datetime import datetime, date, timedelta
from decimal import Decimal
from flask import Blueprint, render_template, request, Response
from flask_login import login_required
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from app.extensions import db
from app.models.appointment import Appointment, AppointmentStatus
from app.models.billing import Invoice, Payment, InvoiceStatus
from app.services.billing_service import BillingService
from app.security import staff_required

bp = Blueprint('reports', __name__)

@bp.route('/')
@staff_required
def index():
    # Parse date range, defaulting to current month or past 7 days
    today = datetime.now().date()
    start_str = request.args.get('start_date', '').strip()
    end_str = request.args.get('end_date', '').strip()

    try:
        start_date = datetime.strptime(start_str, '%Y-%m-%d').date() if start_str else today - timedelta(days=7)
    except ValueError:
        start_date = today - timedelta(days=7)

    try:
        end_date = datetime.strptime(end_str, '%Y-%m-%d').date() if end_str else today
    except ValueError:
        end_date = today

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    # Appointment Stats
    appointments = Appointment.query.filter(
        Appointment.scheduled_time >= start_dt,
        Appointment.scheduled_time <= end_dt
    ).all()

    total_appointments = len(appointments)
    completed_appointments = sum(1 for a in appointments if a.status == AppointmentStatus.COMPLETED)
    cancelled_appointments = sum(1 for a in appointments if a.status == AppointmentStatus.CANCELLED)

    # Billing Stats
    summary = BillingService.get_financial_summary(start_date, end_date)

    return render_template(
        'reports/index.html',
        start_date=start_date,
        end_date=end_date,
        total_appointments=total_appointments,
        completed_appointments=completed_appointments,
        cancelled_appointments=cancelled_appointments,
        summary=summary
    )

@bp.route('/pdf')
@staff_required
def export_pdf():
    today = datetime.now().date()
    start_str = request.args.get('start_date', '').strip()
    end_str = request.args.get('end_date', '').strip()

    try:
        start_date = datetime.strptime(start_str, '%Y-%m-%d').date() if start_str else today - timedelta(days=7)
        end_date = datetime.strptime(end_str, '%Y-%m-%d').date() if end_str else today
    except ValueError:
        start_date = today - timedelta(days=7)
        end_date = today

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    appointments = Appointment.query.filter(
        Appointment.scheduled_time >= start_dt,
        Appointment.scheduled_time <= end_dt
    ).all()
    summary = BillingService.get_financial_summary(start_date, end_date)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('ReportTitle', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor('#0d6efd'), spaceAfter=4)
    sub_style = ParagraphStyle('ReportSub', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#6c757d'), spaceAfter=15)
    bold_style = ParagraphStyle('BText', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10)
    body_style = ParagraphStyle('NText', parent=styles['Normal'], fontSize=10)

    elements = []
    elements.append(Paragraph("<b>CLINICFLOW MANAGEMENT REPORT</b>", title_style))
    elements.append(Paragraph(f"Financial Collections & Clinical Activity Summary ({start_date} to {end_date})", sub_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0d6efd'), spaceAfter=15))

    # Activity table
    act_data = [
        [Paragraph("<b>Metric</b>", bold_style), Paragraph("<b>Count / Value</b>", bold_style)],
        [Paragraph("Total Scheduled Appointments", body_style), Paragraph(str(len(appointments)), body_style)],
        [Paragraph("Completed Consultations", body_style), Paragraph(str(sum(1 for a in appointments if a.status == AppointmentStatus.COMPLETED)), body_style)],
        [Paragraph("Cancelled Appointments", body_style), Paragraph(str(sum(1 for a in appointments if a.status == AppointmentStatus.CANCELLED)), body_style)],
        [Paragraph("Invoices Generated", body_style), Paragraph(str(summary['invoice_count']), body_style)],
        [Paragraph("Total Gross Invoiced", body_style), Paragraph(f"${summary['total_invoiced']:.2f}", body_style)],
        [Paragraph("Total Discounts Given", body_style), Paragraph(f"-${summary['total_discount']:.2f}", body_style)],
        [Paragraph("Total Revenue Collected", bold_style), Paragraph(f"<b>${summary['total_collected']:.2f}</b>", bold_style)],
        [Paragraph("Total Outstanding Receivables", bold_style), Paragraph(f"<b>${summary['total_outstanding']:.2f}</b>", bold_style)]
    ]
    t = Table(act_data, colWidths=[320, 210])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e9ecef')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(t)

    doc.build(elements)
    buffer.seek(0)
    return Response(
        buffer.getvalue(),
        mimetype="application/pdf",
        headers={"Content-Disposition": f"inline; filename=ClinicFlow_Report_{start_date}_{end_date}.pdf"}
    )
