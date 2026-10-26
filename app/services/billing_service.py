from decimal import Decimal
from datetime import datetime, timezone, date
from typing import List, Dict, Optional, Any
from app.extensions import db
from app.models.billing import Invoice, InvoiceItem, Payment, InvoiceStatus, PaymentMethod
from app.models.patient import Patient
from app.models.visit import Visit
from app.models.user import User

class BillingError(Exception):
    pass

class OverpaymentError(BillingError):
    pass

class BillingService:
    @staticmethod
    def create_invoice(
        patient_id: int,
        items_data: List[Dict[str, Any]],
        visit_id: Optional[int] = None,
        discount: Decimal = Decimal('0.00'),
        notes: Optional[str] = None,
        created_by_id: Optional[int] = None
    ) -> Invoice:
        """
        Creates an invoice with multiple items using Decimal arithmetic in a database transaction.
        """
        if not items_data:
            raise BillingError("An invoice must contain at least one line item.")

        patient = db.session.get(Patient, patient_id)
        if not patient or patient.is_archived:
            raise BillingError("Invalid or archived patient.")

        if discount < Decimal('0.00'):
            raise BillingError("Discount cannot be negative.")

        try:
            invoice = Invoice(
                patient_id=patient_id,
                visit_id=visit_id,
                discount=discount,
                notes=notes.strip() if notes else None,
                created_by_id=created_by_id
            )
            db.session.add(invoice)

            subtotal = Decimal('0.00')
            for item in items_data:
                description = item.get('description', '').strip()
                if not description:
                    raise BillingError("Line item description cannot be empty.")

                qty = int(item.get('quantity', 1))
                if qty <= 0:
                    raise BillingError(f"Quantity for '{description}' must be greater than zero.")

                unit_price = Decimal(str(item.get('unit_price', '0.00')))
                if unit_price < Decimal('0.00'):
                    raise BillingError(f"Unit price for '{description}' cannot be negative.")

                item_total = Decimal(str(qty)) * unit_price
                invoice_item = InvoiceItem(
                    invoice=invoice,
                    description=description,
                    quantity=qty,
                    unit_price=unit_price,
                    total_price=item_total
                )
                db.session.add(invoice_item)
                subtotal += item_total

            invoice.subtotal = subtotal
            if discount > subtotal:
                invoice.discount = subtotal
            else:
                invoice.discount = discount

            invoice.total_amount = invoice.subtotal - invoice.discount
            invoice.amount_paid = Decimal('0.00')
            invoice.status = InvoiceStatus.UNPAID

            db.session.commit()
            return invoice
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def record_payment(
        invoice_id: int,
        amount: Decimal,
        payment_method: str,
        received_by_id: Optional[int] = None,
        reference: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Payment:
        """
        Records a partial or full payment against an invoice.
        Enforces Decimal calculation and strictly prevents overpayment.
        """
        invoice = db.session.get(Invoice, invoice_id)
        if not invoice:
            raise BillingError("Invoice not found.")

        if invoice.status == InvoiceStatus.CANCELLED:
            raise BillingError("Cannot post payment to a cancelled invoice.")

        amount_decimal = Decimal(str(amount))
        if amount_decimal <= Decimal('0.00'):
            raise BillingError("Payment amount must be greater than zero.")

        current_balance = invoice.balance_due
        if amount_decimal > current_balance:
            raise OverpaymentError(
                f"Payment amount (${amount_decimal:.2f}) exceeds outstanding balance (${current_balance:.2f}). "
                "Overpayments are strictly prevented without a documented credit/refund process."
            )

        if payment_method not in PaymentMethod.ALL_METHODS:
            raise BillingError(f"Invalid payment method '{payment_method}'.")

        payment = Payment(
            invoice_id=invoice.id,
            amount=amount_decimal,
            payment_method=payment_method,
            received_by_id=received_by_id,
            reference=reference.strip() if reference else None,
            notes=notes.strip() if notes else None
        )
        db.session.add(payment)

        # Update invoice amount_paid and status
        new_paid = Decimal(str(invoice.amount_paid)) + amount_decimal
        invoice.amount_paid = new_paid

        if new_paid >= invoice.total_amount:
            invoice.status = InvoiceStatus.PAID
        elif new_paid > Decimal('0.00'):
            invoice.status = InvoiceStatus.PARTIALLY_PAID

        db.session.commit()
        return payment

    @staticmethod
    def cancel_invoice(invoice_id: int, reason: str, user_id: Optional[int] = None) -> Invoice:
        """
        Cancels an invoice instead of silently deleting it.
        Only unpaid invoices can be cancelled without an explicit refund workflow.
        """
        invoice = db.session.get(Invoice, invoice_id)
        if not invoice:
            raise BillingError("Invoice not found.")

        if invoice.status == InvoiceStatus.CANCELLED:
            raise BillingError("Invoice is already cancelled.")

        if Decimal(str(invoice.amount_paid)) > Decimal('0.00'):
            raise BillingError("Cannot cancel an invoice with posted payments. Process a refund or credit adjustment first.")

        if not reason or len(reason.strip()) < 3:
            raise BillingError("A valid cancellation reason is required.")

        invoice.status = InvoiceStatus.CANCELLED
        invoice.cancellation_reason = reason.strip()
        db.session.commit()
        return invoice

    @staticmethod
    def get_financial_summary(start_date: date, end_date: date) -> Dict[str, Any]:
        """
        Calculates total billed, discounts, collections (payments), and outstanding balances.
        """
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        invoices = Invoice.query.filter(
            Invoice.created_at >= start_dt,
            Invoice.created_at <= end_dt
        ).all()

        payments = Payment.query.filter(
            Payment.payment_date >= start_dt,
            Payment.payment_date <= end_dt
        ).all()

        total_invoiced = Decimal('0.00')
        total_discount = Decimal('0.00')
        total_outstanding = Decimal('0.00')

        for inv in invoices:
            if inv.status != InvoiceStatus.CANCELLED:
                total_invoiced += Decimal(str(inv.total_amount))
                total_discount += Decimal(str(inv.discount))
                total_outstanding += inv.balance_due

        total_collected = sum([Decimal(str(p.amount)) for p in payments], Decimal('0.00'))

        return {
            'start_date': start_date,
            'end_date': end_date,
            'invoice_count': len(invoices),
            'total_invoiced': total_invoiced,
            'total_discount': total_discount,
            'total_collected': total_collected,
            'total_outstanding': total_outstanding,
            'payment_count': len(payments)
        }
