import random
import string
from decimal import Decimal
from datetime import datetime, timezone
from app.extensions import db

def generate_invoice_number():
    timestamp = datetime.now().strftime('%y%m%d')
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f'INV-{timestamp}-{suffix}'

def generate_receipt_number():
    timestamp = datetime.now().strftime('%y%m%d')
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f'RCP-{timestamp}-{suffix}'

class InvoiceStatus:
    UNPAID = 'unpaid'
    PARTIALLY_PAID = 'partially_paid'
    PAID = 'paid'
    CANCELLED = 'cancelled'

    ALL_STATUSES = [UNPAID, PARTIALLY_PAID, PAID, CANCELLED]

class PaymentMethod:
    CASH = 'cash'
    CARD = 'card'
    BANK_TRANSFER = 'bank_transfer'
    INSURANCE = 'insurance'
    UPI = 'upi'

    ALL_METHODS = [CASH, CARD, BANK_TRANSFER, INSURANCE, UPI]

class Invoice(db.Model):
    __tablename__ = 'invoices'

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(32), unique=True, nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False, index=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id', ondelete='SET NULL'), nullable=True, index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    # Financial sums stored as Numeric(10, 2)
    subtotal = db.Column(db.Numeric(10, 2), default=Decimal('0.00'), nullable=False)
    discount = db.Column(db.Numeric(10, 2), default=Decimal('0.00'), nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), default=Decimal('0.00'), nullable=False)
    amount_paid = db.Column(db.Numeric(10, 2), default=Decimal('0.00'), nullable=False)
    status = db.Column(db.String(30), default=InvoiceStatus.UNPAID, nullable=False, index=True)

    cancellation_reason = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def __init__(self, **kwargs):
        if 'invoice_number' not in kwargs or not kwargs['invoice_number']:
            kwargs['invoice_number'] = generate_invoice_number()
        super().__init__(**kwargs)

    # Relationships
    patient = db.relationship('Patient', backref=db.backref('invoices', lazy='dynamic', cascade='all, delete-orphan'))
    visit = db.relationship('Visit', backref=db.backref('invoices', lazy='dynamic'))
    created_by = db.relationship('User', backref=db.backref('created_invoices', lazy='dynamic'))
    items = db.relationship('InvoiceItem', backref='invoice', cascade='all, delete-orphan', lazy='joined')
    payments = db.relationship('Payment', backref='invoice', cascade='all, delete-orphan', lazy='dynamic')

    @property
    def balance_due(self) -> Decimal:
        if self.status == InvoiceStatus.CANCELLED:
            return Decimal('0.00')
        due = Decimal(str(self.total_amount)) - Decimal(str(self.amount_paid))
        return due if due > Decimal('0.00') else Decimal('0.00')

    def recalculate_totals(self) -> None:
        """Sum item totals with Decimal accuracy and update invoice status."""
        new_subtotal = Decimal('0.00')
        for item in self.items:
            new_subtotal += Decimal(str(item.total_price))

        self.subtotal = new_subtotal
        disc = Decimal(str(self.discount or '0.00'))
        if disc > new_subtotal:
            disc = new_subtotal
            self.discount = disc

        self.total_amount = new_subtotal - disc

        # Update status based on paid amount
        paid = Decimal(str(self.amount_paid or '0.00'))
        if self.status != InvoiceStatus.CANCELLED:
            if paid >= self.total_amount and self.total_amount > Decimal('0.00'):
                self.status = InvoiceStatus.PAID
            elif paid > Decimal('0.00'):
                self.status = InvoiceStatus.PARTIALLY_PAID
            else:
                self.status = InvoiceStatus.UNPAID

    def __repr__(self):
        return f'<Invoice {self.invoice_number}: ${self.total_amount} ({self.status})>'

class InvoiceItem(db.Model):
    __tablename__ = 'invoice_items'

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id', ondelete='CASCADE'), nullable=False, index=True)
    description = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)

    def calculate_total(self) -> Decimal:
        qty = Decimal(str(self.quantity))
        price = Decimal(str(self.unit_price))
        self.total_price = qty * price
        return self.total_price

    def __repr__(self):
        return f'<InvoiceItem {self.description} x{self.quantity}: ${self.total_price}>'

class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    receipt_number = db.Column(db.String(32), unique=True, nullable=False, index=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id', ondelete='CASCADE'), nullable=False, index=True)
    received_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(30), default=PaymentMethod.CASH, nullable=False)
    reference = db.Column(db.String(100), nullable=True)  # Transaction ID, check number, receipt ref
    notes = db.Column(db.Text, nullable=True)
    payment_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    def __init__(self, **kwargs):
        if 'receipt_number' not in kwargs or not kwargs['receipt_number']:
            kwargs['receipt_number'] = generate_receipt_number()
        super().__init__(**kwargs)

    received_by = db.relationship('User', backref=db.backref('received_payments', lazy='dynamic'))

    def __repr__(self):
        return f'<Payment {self.receipt_number}: ${self.amount} ({self.payment_method})>'
