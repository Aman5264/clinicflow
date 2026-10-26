import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from app.models.prescription import Prescription
from app.models.billing import Invoice, Payment

class PDFService:
    @staticmethod
    def generate_prescription_pdf(prescription: Prescription) -> bytes:
        """
        Generates a clean medical prescription document using ReportLab.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'ClinicTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#0d6efd'),
            alignment=0,
            spaceAfter=4
        )
        subtitle_style = ParagraphStyle(
            'ClinicSubtitle',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#6c757d'),
            spaceAfter=15
        )
        section_style = ParagraphStyle(
            'SectionHead',
            parent=styles['Heading3'],
            fontSize=11,
            textColor=colors.HexColor('#212529'),
            spaceBefore=10,
            spaceAfter=6
        )
        body_style = styles['Normal']
        body_style.fontSize = 9
        bold_style = ParagraphStyle('BoldText', parent=body_style, fontName='Helvetica-Bold')

        elements = []

        # 1. Header
        elements.append(Paragraph("<b>CLINICFLOW MEDICAL CENTER</b>", title_style))
        elements.append(Paragraph("Prescription & Clinical Therapy Directive &bull; Confidential Medical Record", subtitle_style))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0d6efd'), spaceAfter=15))

        # 2. Prescription Meta & Patient info table
        patient = prescription.patient
        doctor = prescription.doctor

        patient_info = [
            [
                Paragraph("<b>Patient Name:</b>", body_style),
                Paragraph(patient.full_name, bold_style),
                Paragraph("<b>Prescription #:</b>", body_style),
                Paragraph(f"<font color='#0d6efd'>{prescription.prescription_number}</font>", bold_style)
            ],
            [
                Paragraph("<b>Patient Code:</b>", body_style),
                Paragraph(patient.patient_code, body_style),
                Paragraph("<b>Date Prescribed:</b>", body_style),
                Paragraph(prescription.created_at.strftime('%B %d, %Y'), body_style)
            ],
            [
                Paragraph("<b>Age / DOB:</b>", body_style),
                Paragraph(f"{patient.age} yrs ({patient.date_of_birth.strftime('%Y-%m-%d')})", body_style),
                Paragraph("<b>Prescribing Doctor:</b>", body_style),
                Paragraph(f"Dr. {doctor.name}", bold_style)
            ]
        ]

        p_table = Table(patient_info, colWidths=[90, 170, 110, 160])
        p_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(p_table)
        elements.append(Spacer(1, 15))

        # 3. Rx Medication List
        elements.append(Paragraph("<b>Rx - Prescribed Medications</b>", section_style))

        med_headers = [
            Paragraph("<b>#</b>", bold_style),
            Paragraph("<b>Medication & Strength</b>", bold_style),
            Paragraph("<b>Dosage & Route</b>", bold_style),
            Paragraph("<b>Frequency & Duration</b>", bold_style),
            Paragraph("<b>Instructions</b>", bold_style),
        ]
        med_rows = [med_headers]

        for idx, item in enumerate(prescription.items, start=1):
            med_rows.append([
                Paragraph(str(idx), body_style),
                Paragraph(f"<b>{item.medicine_name}</b><br/><font color='#6c757d'>{item.strength}</font>", body_style),
                Paragraph(f"{item.dosage}<br/>{item.route}", body_style),
                Paragraph(f"{item.frequency}<br/>Duration: {item.duration}", body_style),
                Paragraph(item.instructions or "As directed", body_style)
            ])

        med_table = Table(med_rows, colWidths=[25, 145, 100, 130, 130])
        med_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e9ecef')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(med_table)
        elements.append(Spacer(1, 15))

        # 4. Clinical notes / instructions
        if prescription.notes:
            elements.append(Paragraph("<b>Special Precautions / Clinician Notes:</b>", section_style))
            elements.append(Paragraph(prescription.notes, body_style))
            elements.append(Spacer(1, 20))

        # 5. Sign-off block
        elements.append(Spacer(1, 30))
        sig_data = [
            ["", Paragraph("____________________________________", body_style)],
            ["", Paragraph(f"<b>Dr. {doctor.name}</b>", bold_style)],
            ["", Paragraph("Authorized Medical Practitioner", subtitle_style)]
        ]
        sig_table = Table(sig_data, colWidths=[320, 210])
        elements.append(sig_table)

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()

    @staticmethod
    def generate_invoice_pdf(invoice: Invoice) -> bytes:
        """
        Generates an itemized patient invoice PDF using ReportLab.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'InvoiceTitle',
            parent=styles['Heading1'],
            fontSize=22,
            textColor=colors.HexColor('#198754'),
            spaceAfter=4
        )
        subtitle_style = ParagraphStyle(
            'InvSub',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#6c757d'),
            spaceAfter=15
        )
        bold_style = ParagraphStyle('BText', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9)
        body_style = ParagraphStyle('NText', parent=styles['Normal'], fontSize=9)

        elements = []

        # 1. Header
        elements.append(Paragraph("<b>CLINICFLOW HEALTHCARE</b>", title_style))
        elements.append(Paragraph("Official Medical Bill & Invoice", subtitle_style))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#198754'), spaceAfter=15))

        # 2. Details
        patient = invoice.patient
        info_data = [
            [
                Paragraph("<b>Billed To:</b>", body_style),
                Paragraph(patient.full_name, bold_style),
                Paragraph("<b>Invoice #:</b>", body_style),
                Paragraph(f"<font color='#198754'>{invoice.invoice_number}</font>", bold_style)
            ],
            [
                Paragraph("<b>Patient Code:</b>", body_style),
                Paragraph(patient.patient_code, body_style),
                Paragraph("<b>Date:</b>", body_style),
                Paragraph(invoice.created_at.strftime('%B %d, %Y'), body_style)
            ],
            [
                Paragraph("<b>Phone / Contact:</b>", body_style),
                Paragraph(patient.phone, body_style),
                Paragraph("<b>Status:</b>", body_style),
                Paragraph(f"<b>{invoice.status.upper()}</b>", bold_style)
            ]
        ]
        info_table = Table(info_data, colWidths=[90, 170, 100, 170])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 15))

        # 3. Itemized Services Table
        item_rows = [
            [
                Paragraph("<b>#</b>", bold_style),
                Paragraph("<b>Service / Item Description</b>", bold_style),
                Paragraph("<b>Qty</b>", bold_style),
                Paragraph("<b>Unit Price</b>", bold_style),
                Paragraph("<b>Total</b>", bold_style)
            ]
        ]
        for idx, itm in enumerate(invoice.items, start=1):
            item_rows.append([
                Paragraph(str(idx), body_style),
                Paragraph(itm.description, body_style),
                Paragraph(str(itm.quantity), body_style),
                Paragraph(f"${itm.unit_price:.2f}", body_style),
                Paragraph(f"${itm.total_price:.2f}", bold_style)
            ])

        item_table = Table(item_rows, colWidths=[30, 260, 50, 90, 100])
        item_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e9ecef')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(item_table)
        elements.append(Spacer(1, 10))

        # 4. Totals Summary Table
        totals_data = [
            ["", "", Paragraph("<b>Subtotal:</b>", body_style), Paragraph(f"${invoice.subtotal:.2f}", body_style)],
            ["", "", Paragraph("<b>Discount:</b>", body_style), Paragraph(f"-${invoice.discount:.2f}", body_style)],
            ["", "", Paragraph("<b>Net Total:</b>", bold_style), Paragraph(f"<b>${invoice.total_amount:.2f}</b>", bold_style)],
            ["", "", Paragraph("<b>Amount Paid:</b>", body_style), Paragraph(f"${invoice.amount_paid:.2f}", body_style)],
            ["", "", Paragraph("<b>Balance Due:</b>", bold_style), Paragraph(f"<b>${invoice.balance_due:.2f}</b>", bold_style)]
        ]
        totals_table = Table(totals_data, colWidths=[150, 140, 110, 130])
        totals_table.setStyle(TableStyle([
            ('PADDING', (0, 0), (-1, -1), 4),
            ('LINEABOVE', (2, 2), (3, 2), 1, colors.black),
            ('LINEBELOW', (2, 4), (3, 4), 1.5, colors.black),
        ]))
        elements.append(totals_table)

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()

    @staticmethod
    def generate_receipt_pdf(payment: Payment) -> bytes:
        """
        Generates an official payment receipt PDF.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'ReceiptTitle',
            parent=styles['Heading1'],
            fontSize=22,
            textColor=colors.HexColor('#0d6efd'),
            spaceAfter=4
        )
        subtitle_style = ParagraphStyle(
            'RcpSub',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#6c757d'),
            spaceAfter=15
        )
        bold_style = ParagraphStyle('BText', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10)
        body_style = ParagraphStyle('NText', parent=styles['Normal'], fontSize=10)

        elements = []

        elements.append(Paragraph("<b>CLINICFLOW HEALTHCARE</b>", title_style))
        elements.append(Paragraph("Official Payment Acknowledgment & Receipt", subtitle_style))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0d6efd'), spaceAfter=20))

        invoice = payment.invoice
        patient = invoice.patient

        receipt_rows = [
            [Paragraph("<b>Receipt Number:</b>", body_style), Paragraph(f"<font color='#0d6efd'>{payment.receipt_number}</font>", bold_style)],
            [Paragraph("<b>Invoice Number:</b>", body_style), Paragraph(invoice.invoice_number, body_style)],
            [Paragraph("<b>Payment Date:</b>", body_style), Paragraph(payment.payment_date.strftime('%B %d, %Y %H:%M UTC'), body_style)],
            [Paragraph("<b>Patient Name:</b>", body_style), Paragraph(patient.full_name, bold_style)],
            [Paragraph("<b>Patient ID Code:</b>", body_style), Paragraph(patient.patient_code, body_style)],
            [Paragraph("<b>Payment Method:</b>", body_style), Paragraph(payment.payment_method.upper(), body_style)],
            [Paragraph("<b>Transaction / Ref:</b>", body_style), Paragraph(payment.reference or "N/A", body_style)],
            [Paragraph("<b>Amount Paid:</b>", bold_style), Paragraph(f"<font color='#198754' size='14'><b>${payment.amount:.2f}</b></font>", bold_style)],
            [Paragraph("<b>Remaining Balance on Invoice:</b>", body_style), Paragraph(f"${invoice.balance_due:.2f}", bold_style)]
        ]

        table = Table(receipt_rows, colWidths=[200, 310])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 30))

        elements.append(Paragraph("<i>Thank you for your payment. This receipt is an official clinical financial confirmation.</i>", subtitle_style))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
