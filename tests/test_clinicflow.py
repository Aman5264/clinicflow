from datetime import date
import pytest
from app import create_app
from app.extensions import db
from app.models.user import User, Role
from app.models.patient import Patient
from config import TestConfig

@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

@pytest.fixture
def create_test_user(app):
    def _create_user(email='test@clinic.com', password='Password123!', role=Role.RECEPTIONIST, name='Test Staff', is_active=True):
        user = User(email=email, name=name, role=role, is_active=is_active)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user
    return _create_user

@pytest.fixture
def create_test_patient(app):
    def _create_patient(name='Alice Smith', dob=date(1990, 5, 14), phone='+14155550100', address='123 Market St', emergency='Bob - 555-0101'):
        patient = Patient(
            full_name=name,
            date_of_birth=dob,
            phone=phone,
            address=address,
            emergency_contact=emergency
        )
        db.session.add(patient)
        db.session.commit()
        return patient
    return _create_patient

# ================= AUTHENTICATION & CLI TESTS ================= #

def test_password_hashing(app):
    user = User(email='doctor@clinic.com', name='Dr. Dave', role=Role.DOCTOR)
    user.set_password('SecretPass123')
    assert user.password_hash != 'SecretPass123'
    assert user.check_password('SecretPass123') is True
    assert user.check_password('WrongPass') is False

def test_login_success_and_logout(client, create_test_user):
    create_test_user(email='staff@clinic.com', password='SecurePassword123!', role=Role.RECEPTIONIST)

    # Login
    response = client.post('/auth/login', data={
        'email': 'staff@clinic.com',
        'password': 'SecurePassword123!'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Welcome back, Test Staff!' in response.data
    assert b'Dashboard' in response.data

    # Logout
    logout_resp = client.get('/auth/logout', follow_redirects=True)
    assert logout_resp.status_code == 200
    assert b'You have been successfully logged out.' in logout_resp.data

def test_login_invalid_credentials(client, create_test_user):
    create_test_user(email='staff@clinic.com', password='SecurePassword123!')

    response = client.post('/auth/login', data={
        'email': 'staff@clinic.com',
        'password': 'InvalidPassword'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Invalid email or password.' in response.data

def test_login_inactive_user_blocked(client, create_test_user):
    create_test_user(email='inactive@clinic.com', password='SecurePassword123!', is_active=False)

    response = client.post('/auth/login', data={
        'email': 'inactive@clinic.com',
        'password': 'SecurePassword123!'
    }, follow_redirects=True)
    assert b'Your account has been deactivated.' in response.data

def test_cli_create_admin(runner, app):
    result = runner.invoke(args=['create-admin', '--name', 'Super Admin', '--email', 'admin@clinic.com', '--password', 'AdminSecret123'])
    assert result.exit_code == 0
    assert 'created successfully' in result.output

    with app.app_context():
        admin = User.query.filter_by(email='admin@clinic.com').first()
        assert admin is not None
        assert admin.role == Role.ADMIN
        assert admin.check_password('AdminSecret123') is True

# ================= ROLE AUTHORIZATION TESTS ================= #

def test_role_authorization_receptionist_blocked_from_admin_users(client, create_test_user):
    create_test_user(email='recep@clinic.com', password='Password123!', role=Role.RECEPTIONIST)

    # Login as receptionist
    client.post('/auth/login', data={'email': 'recep@clinic.com', 'password': 'Password123!'}, follow_redirects=True)

    # Attempt to access admin-only users list
    resp = client.get('/auth/users')
    assert resp.status_code == 403

def test_admin_access_user_management(client, create_test_user):
    create_test_user(email='admin@clinic.com', password='Password123!', role=Role.ADMIN)

    client.post('/auth/login', data={'email': 'admin@clinic.com', 'password': 'Password123!'}, follow_redirects=True)
    resp = client.get('/auth/users')
    assert resp.status_code == 200
    assert b'User Management' in resp.data

def test_unauthenticated_redirect(client):
    resp = client.get('/patients/')
    assert resp.status_code == 302
    assert '/auth/login' in resp.headers['Location']

# ================= PATIENT WORKFLOW TESTS ================= #

def test_patient_registration_and_detail(client, create_test_user):
    create_test_user(email='recep@clinic.com', password='Password123!', role=Role.RECEPTIONIST)
    client.post('/auth/login', data={'email': 'recep@clinic.com', 'password': 'Password123!'}, follow_redirects=True)

    # Register patient
    resp = client.post('/patients/register', data={
        'full_name': 'Jane Doe',
        'date_of_birth': '1985-04-12',
        'phone': '+14155552345',
        'address': '742 Evergreen Terrace',
        'emergency_contact': 'Homer Simpson - 555-7334'
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert b'Jane Doe' in resp.data
    assert b'registered successfully' in resp.data
    assert b'PAT-' in resp.data

def test_patient_validation_future_dob(client, create_test_user):
    create_test_user(email='recep@clinic.com', password='Password123!', role=Role.RECEPTIONIST)
    client.post('/auth/login', data={'email': 'recep@clinic.com', 'password': 'Password123!'}, follow_redirects=True)

    # Future DOB
    resp = client.post('/patients/register', data={
        'full_name': 'Future Person',
        'date_of_birth': '2099-01-01',
        'phone': '+14155552345',
        'address': 'Space Colony',
        'emergency_contact': 'Robo - 555-0000'
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert b'Date of birth cannot be in the future.' in resp.data

def test_patient_duplicate_record_check(client, create_test_user, create_test_patient):
    create_test_user(email='recep@clinic.com', password='Password123!', role=Role.RECEPTIONIST)
    create_test_patient(name='Charlie Brown', dob=date(2000, 1, 1), phone='+14155559999')

    client.post('/auth/login', data={'email': 'recep@clinic.com', 'password': 'Password123!'}, follow_redirects=True)

    # Submit duplicate
    resp = client.post('/patients/register', data={
        'full_name': 'Charlie Brown',
        'date_of_birth': '2000-01-01',
        'phone': '+14155559999',
        'address': 'New Address',
        'emergency_contact': 'Snoopy - 555-1234'
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert b'A patient with matching name, birth date, and phone number already exists' in resp.data

def test_patient_search_and_pagination(client, create_test_user, create_test_patient):
    create_test_user(email='recep@clinic.com', password='Password123!', role=Role.RECEPTIONIST)
    p1 = create_test_patient(name='Michael Scott', phone='+15551112222')
    p2 = create_test_patient(name='Pam Beesly', phone='+15553334444')

    client.post('/auth/login', data={'email': 'recep@clinic.com', 'password': 'Password123!'}, follow_redirects=True)

    # Search by name
    resp = client.get('/patients/?q=Michael')
    assert b'Michael Scott' in resp.data
    assert b'Pam Beesly' not in resp.data

    # Search by phone
    resp_phone = client.get('/patients/?q=3334444')
    assert b'Pam Beesly' in resp_phone.data
    assert b'Michael Scott' not in resp_phone.data

def test_patient_archive_and_restore(client, create_test_user, create_test_patient):
    create_test_user(email='recep@clinic.com', password='Password123!', role=Role.RECEPTIONIST)
    patient = create_test_patient(name='George Costanza')

    client.post('/auth/login', data={'email': 'recep@clinic.com', 'password': 'Password123!'}, follow_redirects=True)

    # Archive
    resp_archive = client.post(f'/patients/{patient.id}/archive', data={
        'archive_reason': 'Patient moved abroad'
    }, follow_redirects=True)
    assert resp_archive.status_code == 200
    assert b'has been archived' in resp_archive.data
    assert b'Patient moved abroad' in resp_archive.data

    # Should not appear in active search
    resp_active_list = client.get('/patients/')
    assert b'George Costanza' not in resp_active_list.data

    # Should appear when include_archived is requested
    resp_archived_list = client.get('/patients/?archived=1')
    assert b'George Costanza' in resp_archived_list.data

    # Restore
    resp_restore = client.post(f'/patients/{patient.id}/restore', follow_redirects=True)
    assert resp_restore.status_code == 200
    assert b'restored to active status' in resp_restore.data

# ================= APPOINTMENT & CONFLICT TESTS ================= #

def test_appointment_booking_and_doctor_conflict(app, create_test_user, create_test_patient):
    from datetime import datetime
    from app.services.appointment_service import AppointmentService, AppointmentConflictError
    from app.models.appointment import AppointmentStatus

    with app.app_context():
        doc = create_test_user(email='dr.house@clinic.com', role=Role.DOCTOR, name='Dr. Gregory House')
        patient1 = create_test_patient(name='Patient Alpha', phone='+14155551111')
        patient2 = create_test_patient(name='Patient Beta', phone='+14155552222')

        slot = datetime(2026, 11, 10, 10, 0)

        # 1. Book first appointment (10:00 - 10:30)
        apt1 = AppointmentService.book_appointment(
            patient_id=patient1.id,
            doctor_id=doc.id,
            scheduled_time=slot,
            duration_minutes=30,
            reason='Persistent headache'
        )
        assert apt1.id is not None
        assert apt1.status == AppointmentStatus.SCHEDULED

        # 2. Attempt overlapping booking for same doctor at 10:15 (Overlaps 10:00-10:30) -> Should raise conflict
        with pytest.raises(AppointmentConflictError):
            AppointmentService.book_appointment(
                patient_id=patient2.id,
                doctor_id=doc.id,
                scheduled_time=datetime(2026, 11, 10, 10, 15),
                duration_minutes=30,
                reason='Follow-up check'
            )

        # 3. Non-overlapping booking at 10:30 -> Should succeed
        apt2 = AppointmentService.book_appointment(
            patient_id=patient2.id,
            doctor_id=doc.id,
            scheduled_time=datetime(2026, 11, 10, 10, 30),
            duration_minutes=30,
            reason='Checkup'
        )
        assert apt2.id is not None

def test_appointment_reschedule_and_conflict(app, create_test_user, create_test_patient):
    from datetime import datetime
    from app.services.appointment_service import AppointmentService, AppointmentConflictError

    with app.app_context():
        doc = create_test_user(email='dr.cameron@clinic.com', role=Role.DOCTOR, name='Dr. Allison Cameron')
        p1 = create_test_patient(name='Patient Gamma')
        p2 = create_test_patient(name='Patient Delta', phone='+14155554321')

        apt1 = AppointmentService.book_appointment(
            patient_id=p1.id,
            doctor_id=doc.id,
            scheduled_time=datetime(2026, 11, 10, 9, 0),
            duration_minutes=30,
            reason='Knee pain'
        )
        apt2 = AppointmentService.book_appointment(
            patient_id=p2.id,
            doctor_id=doc.id,
            scheduled_time=datetime(2026, 11, 10, 11, 0),
            duration_minutes=30,
            reason='Routine'
        )

        # Reschedule apt2 to collide with apt1 at 09:15 -> Must fail
        with pytest.raises(AppointmentConflictError):
            AppointmentService.reschedule_appointment(
                appointment_id=apt2.id,
                new_scheduled_time=datetime(2026, 11, 10, 9, 15),
                new_duration_minutes=30
            )

        # Reschedule apt2 to free slot 14:00 -> Succeeded
        updated = AppointmentService.reschedule_appointment(
            appointment_id=apt2.id,
            new_scheduled_time=datetime(2026, 11, 10, 14, 0),
            new_duration_minutes=30
        )
        assert updated.scheduled_time == datetime(2026, 11, 10, 14, 0)

def test_appointment_lifecycle_and_state_transitions(app, create_test_user, create_test_patient):
    from datetime import datetime
    from app.services.appointment_service import AppointmentService, AppointmentStateError
    from app.models.appointment import AppointmentStatus

    with app.app_context():
        doc = create_test_user(email='dr.wilson@clinic.com', role=Role.DOCTOR, name='Dr. James Wilson')
        patient = create_test_patient(name='Patient Epsilon')

        apt = AppointmentService.book_appointment(
            patient_id=patient.id,
            doctor_id=doc.id,
            scheduled_time=datetime(2026, 11, 10, 9, 0),
            reason='General consultation'
        )
        assert apt.status == AppointmentStatus.SCHEDULED

        # Invalid transition: directly SCHEDULED -> COMPLETED
        with pytest.raises(AppointmentStateError):
            AppointmentService.transition_status(apt.id, AppointmentStatus.COMPLETED)

        # Valid transition: SCHEDULED -> CHECKED_IN
        checked_in = AppointmentService.transition_status(apt.id, AppointmentStatus.CHECKED_IN)
        assert checked_in.status == AppointmentStatus.CHECKED_IN
        assert checked_in.check_in_time is not None

        # Valid transition: CHECKED_IN -> IN_CONSULTATION
        in_consult = AppointmentService.transition_status(apt.id, AppointmentStatus.IN_CONSULTATION)
        assert in_consult.status == AppointmentStatus.IN_CONSULTATION

def test_waiting_queue_ordering(app, create_test_user, create_test_patient):
    from datetime import datetime, timedelta
    from app.services.appointment_service import AppointmentService
    from app.models.appointment import AppointmentStatus

    with app.app_context():
        doc = create_test_user(email='dr.cuddy@clinic.com', role=Role.DOCTOR, name='Dr. Lisa Cuddy')
        p1 = create_test_patient(name='First Arrival', phone='+15550000001')
        p2 = create_test_patient(name='Second Arrival', phone='+15550000002')

        today = datetime.now().date()
        t1 = datetime.combine(today, datetime.strptime("09:00", "%H:%M").time())
        t2 = datetime.combine(today, datetime.strptime("09:30", "%H:%M").time())

        apt1 = AppointmentService.book_appointment(p1.id, doc.id, t1, 'Checkup 1')
        apt2 = AppointmentService.book_appointment(p2.id, doc.id, t2, 'Checkup 2')

        # Check in p2 first, then p1
        AppointmentService.transition_status(apt2.id, AppointmentStatus.CHECKED_IN)
        # Artificially set check in times to verify ordering
        apt2.check_in_time = datetime.now() - timedelta(minutes=15)
        AppointmentService.transition_status(apt1.id, AppointmentStatus.CHECKED_IN)
        apt1.check_in_time = datetime.now() - timedelta(minutes=5)
        db.session.commit()

        queue = AppointmentService.get_waiting_queue(target_date=today)
        assert len(queue) == 2
        # Earliest check in should be first in queue
        assert queue[0].id == apt2.id
        assert queue[1].id == apt1.id

# ================= CONSULTATION & VISIT TESTS ================= #

def test_consultation_creation_and_duplicate_prevention(app, create_test_user, create_test_patient):
    from datetime import datetime
    from app.services.appointment_service import AppointmentService
    from app.services.consultation_service import ConsultationService, ConsultationError
    from app.models.appointment import AppointmentStatus

    with app.app_context():
        doc = create_test_user(email='dr.chase@clinic.com', role=Role.DOCTOR, name='Dr. Robert Chase')
        patient = create_test_patient(name='Patient Zeta')

        apt = AppointmentService.book_appointment(
            patient_id=patient.id,
            doctor_id=doc.id,
            scheduled_time=datetime(2026, 11, 10, 10, 0),
            reason='Chest discomfort'
        )
        AppointmentService.transition_status(apt.id, AppointmentStatus.CHECKED_IN)
        AppointmentService.transition_status(apt.id, AppointmentStatus.IN_CONSULTATION)

        # Create visit
        visit = ConsultationService.create_visit(
            patient_id=patient.id,
            doctor_id=doc.id,
            symptoms='Mild precordial tightness after exertion',
            diagnosis='Costochondritis / Musculoskeletal strain',
            clinical_notes='Normal ECG, prescribed NSAIDs',
            appointment_id=apt.id,
            author_user_id=doc.id
        )
        assert visit.id is not None
        assert visit.patient_id == patient.id
        assert visit.appointment_id == apt.id
        # Appointment should now be marked completed
        assert apt.status == AppointmentStatus.COMPLETED

        # Attempting second visit for same appointment must raise ConsultationError
        with pytest.raises(ConsultationError):
            ConsultationService.create_visit(
                patient_id=patient.id,
                doctor_id=doc.id,
                symptoms='Duplicate complaint',
                diagnosis='Duplicate assessment',
                appointment_id=apt.id
            )

def test_consultation_audit_logging(app, create_test_user, create_test_patient):
    from app.services.consultation_service import ConsultationService
    from app.models.visit import ClinicalAuditLog

    with app.app_context():
        doc = create_test_user(email='dr.foreman@clinic.com', role=Role.DOCTOR, name='Dr. Eric Foreman')
        patient = create_test_patient(name='Patient Eta')

        visit = ConsultationService.create_visit(
            patient_id=patient.id,
            doctor_id=doc.id,
            symptoms='Fever and sore throat',
            diagnosis='Acute pharyngitis',
            author_user_id=doc.id
        )

        assert visit.audit_logs.count() == 1
        created_log = visit.audit_logs.first()
        assert created_log.action == 'created'
        assert 'Acute pharyngitis' in created_log.changes_json

        # Update visit
        updated_visit = ConsultationService.update_visit(
            visit_id=visit.id,
            symptoms='Fever and severe sore throat',
            diagnosis='Streptococcal pharyngitis (Rapid Strep Positive)',
            clinical_notes='Penicillin VK 500mg PO BID x 10 days',
            author_user_id=doc.id
        )
        assert updated_visit.diagnosis == 'Streptococcal pharyngitis (Rapid Strep Positive)'
        assert visit.audit_logs.count() == 2
        update_log = visit.audit_logs.order_by(ClinicalAuditLog.timestamp.desc()).first()
        assert update_log.action == 'updated'
        assert 'old' in update_log.changes_json

def test_clinical_route_permissions(client, create_test_user, create_test_patient):
    recep = create_test_user(email='recep2@clinic.com', password='Password123!', role=Role.RECEPTIONIST)
    doc = create_test_user(email='doctor2@clinic.com', password='Password123!', role=Role.DOCTOR)
    patient = create_test_patient(name='Patient Theta')

    # Receptionist attempts to access new consultation route -> 403 Forbidden
    client.post('/auth/login', data={'email': 'recep2@clinic.com', 'password': 'Password123!'}, follow_redirects=True)
    resp = client.get(f'/consultations/new?patient_id={patient.id}')
    assert resp.status_code == 403

    # Doctor accesses consultation route -> 200 OK
    client.get('/auth/logout', follow_redirects=True)
    client.post('/auth/login', data={'email': 'doctor2@clinic.com', 'password': 'Password123!'}, follow_redirects=True)
    doc_resp = client.get(f'/consultations/new?patient_id={patient.id}')
    assert doc_resp.status_code == 200
    assert b'New Clinical Consultation' in doc_resp.data

# ================= PRESCRIPTION & PDF TESTS ================= #

def test_prescription_creation_and_amendment(app, create_test_user, create_test_patient):
    from app.services.consultation_service import ConsultationService
    from app.services.prescription_service import PrescriptionService
    from app.services.pdf_service import PDFService

    with app.app_context():
        doc = create_test_user(email='dr.rx@clinic.com', role=Role.DOCTOR, name='Dr. Emily Thorne')
        patient = create_test_patient(name='Rx Patient 1')

        visit = ConsultationService.create_visit(
            patient_id=patient.id,
            doctor_id=doc.id,
            symptoms='Acute rhinosinusitis and facial pressure',
            diagnosis='Bacterial Sinusitis',
            author_user_id=doc.id
        )

        items_data = [
            {
                'medicine_name': 'Amoxicillin-Clavulanate',
                'strength': '875/125 mg',
                'dosage': '1 tablet',
                'route': 'Oral',
                'frequency': 'BID (twice daily)',
                'duration': '10 days',
                'instructions': 'Take at the start of a meal.'
            },
            {
                'medicine_name': 'Fluticasone Propionate',
                'strength': '50 mcg/actuation',
                'dosage': '2 sprays per nostril',
                'route': 'Inhalation',
                'frequency': 'Once daily',
                'duration': '30 days',
                'instructions': 'Shake well before each use.'
            }
        ]

        rx = PrescriptionService.create_prescription(
            visit_id=visit.id,
            doctor_id=doc.id,
            items_data=items_data,
            notes='Drink plenty of warm fluids. Return if fever persists beyond 3 days.'
        )

        assert rx.id is not None
        assert rx.prescription_number.startswith('RX-')
        assert len(rx.items) == 2
        assert rx.items[0].medicine_name == 'Amoxicillin-Clavulanate'

        # Test PDF generation
        pdf_bytes = PDFService.generate_prescription_pdf(rx)
        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b'%PDF')

        # Test Prescription amendment
        updated_items = [
            {
                'medicine_name': 'Amoxicillin-Clavulanate',
                'strength': '1000 mg',
                'dosage': '1 tablet',
                'route': 'Oral',
                'frequency': 'BID',
                'duration': '14 days',
                'instructions': 'Dosage adjusted.'
            }
        ]
        amended = PrescriptionService.update_prescription(rx.id, updated_items, notes='Extended duration.')
        assert len(amended.items) == 1
        assert amended.items[0].strength == '1000 mg'
        assert amended.notes == 'Extended duration.'

# ================= BILLING & FINANCIAL INTEGRITY TESTS ================= #

def test_invoice_decimal_calculations_and_totals(app, create_test_user, create_test_patient):
    from decimal import Decimal
    from app.services.billing_service import BillingService
    from app.models.billing import InvoiceStatus

    with app.app_context():
        user = create_test_user(email='cashier@clinic.com', role=Role.RECEPTIONIST)
        patient = create_test_patient(name='Billing Patient 1')

        items = [
            {'description': 'Primary Care Consultation', 'quantity': 1, 'unit_price': Decimal('75.50')},
            {'description': 'Rapid Strep Swab Test', 'quantity': 2, 'unit_price': Decimal('19.25')}
        ]

        # 75.50 + (2 * 19.25) = 75.50 + 38.50 = 114.00
        # Discount = 14.00 -> Net Total = 100.00
        invoice = BillingService.create_invoice(
            patient_id=patient.id,
            items_data=items,
            discount=Decimal('14.00'),
            created_by_id=user.id
        )

        assert invoice.subtotal == Decimal('114.00')
        assert invoice.discount == Decimal('14.00')
        assert invoice.total_amount == Decimal('100.00')
        assert invoice.amount_paid == Decimal('0.00')
        assert invoice.balance_due == Decimal('100.00')
        assert invoice.status == InvoiceStatus.UNPAID

def test_partial_payments_and_overpayment_prevention(app, create_test_user, create_test_patient):
    from decimal import Decimal
    from app.services.billing_service import BillingService, OverpaymentError
    from app.models.billing import InvoiceStatus, PaymentMethod

    with app.app_context():
        user = create_test_user(email='clerk@clinic.com', role=Role.RECEPTIONIST)
        patient = create_test_patient(name='Billing Patient 2')

        items = [{'description': 'Cardiology Consultation', 'quantity': 1, 'unit_price': Decimal('200.00')}]
        invoice = BillingService.create_invoice(patient.id, items, created_by_id=user.id)

        # 1. First partial payment: $80.00
        p1 = BillingService.record_payment(
            invoice_id=invoice.id,
            amount=Decimal('80.00'),
            payment_method=PaymentMethod.CASH,
            received_by_id=user.id,
            reference='CASH-001'
        )
        assert p1.receipt_number.startswith('RCP-')
        assert invoice.amount_paid == Decimal('80.00')
        assert invoice.balance_due == Decimal('120.00')
        assert invoice.status == InvoiceStatus.PARTIALLY_PAID

        # 2. Attempt overpayment: paying $130.00 when balance due is $120.00 -> Must raise OverpaymentError
        with pytest.raises(OverpaymentError):
            BillingService.record_payment(
                invoice_id=invoice.id,
                amount=Decimal('130.00'),
                payment_method=PaymentMethod.CARD
            )

        # 3. Pay remaining exact balance: $120.00
        p2 = BillingService.record_payment(
            invoice_id=invoice.id,
            amount=Decimal('120.00'),
            payment_method=PaymentMethod.CARD,
            received_by_id=user.id,
            reference='CARD-AUTH-8821'
        )
        assert invoice.amount_paid == Decimal('200.00')
        assert invoice.balance_due == Decimal('0.00')
        assert invoice.status == InvoiceStatus.PAID

def test_invoice_cancellation_and_protection(app, create_test_user, create_test_patient):
    from decimal import Decimal
    from app.services.billing_service import BillingService, BillingError
    from app.models.billing import InvoiceStatus, PaymentMethod

    with app.app_context():
        user = create_test_user(email='biller@clinic.com', role=Role.RECEPTIONIST)
        patient = create_test_patient(name='Billing Patient 3')

        # Unpaid invoice can be cancelled
        inv1 = BillingService.create_invoice(patient.id, [{'description': 'Consultation', 'quantity': 1, 'unit_price': Decimal('50.00')}])
        cancelled = BillingService.cancel_invoice(inv1.id, reason='Created in error')
        assert cancelled.status == InvoiceStatus.CANCELLED
        assert cancelled.cancellation_reason == 'Created in error'
        assert cancelled.balance_due == Decimal('0.00')

        # Invoice with posted payments cannot be directly cancelled
        inv2 = BillingService.create_invoice(patient.id, [{'description': 'Lab Panel', 'quantity': 1, 'unit_price': Decimal('100.00')}])
        BillingService.record_payment(inv2.id, amount=Decimal('50.00'), payment_method=PaymentMethod.CASH)

        with pytest.raises(BillingError) as exc_info:
            BillingService.cancel_invoice(inv2.id, reason='Patient dispute')
        assert 'posted payments' in str(exc_info.value)

def test_invoice_and_receipt_pdf_generation(app, create_test_user, create_test_patient):
    from decimal import Decimal
    from app.services.billing_service import BillingService
    from app.services.pdf_service import PDFService
    from app.models.billing import PaymentMethod

    with app.app_context():
        user = create_test_user(email='staff_pdf@clinic.com', role=Role.RECEPTIONIST)
        patient = create_test_patient(name='PDF Test Patient')

        items = [{'description': 'Physiotherapy Session', 'quantity': 2, 'unit_price': Decimal('60.00')}]
        invoice = BillingService.create_invoice(patient.id, items, discount=Decimal('10.00'), created_by_id=user.id)
        payment = BillingService.record_payment(invoice.id, amount=Decimal('50.00'), payment_method=PaymentMethod.UPI, reference='UPI-7761')

        # Generate Invoice PDF
        inv_pdf = PDFService.generate_invoice_pdf(invoice)
        assert len(inv_pdf) > 0
        assert inv_pdf.startswith(b'%PDF')

        # Generate Receipt PDF
        rcp_pdf = PDFService.generate_receipt_pdf(payment)
        assert len(rcp_pdf) > 0
        assert rcp_pdf.startswith(b'%PDF')

def test_database_transaction_rollback_on_financial_error(app, create_test_user, create_test_patient):
    from decimal import Decimal
    from app.services.billing_service import BillingService, BillingError
    from app.models.billing import Invoice

    with app.app_context():
        patient = create_test_patient(name='Rollback Patient')
        initial_count = Invoice.query.count()

        # Provide an invalid item with negative price to trigger exception during creation
        bad_items = [
            {'description': 'Valid Item', 'quantity': 1, 'unit_price': Decimal('50.00')},
            {'description': 'Invalid Item', 'quantity': 1, 'unit_price': Decimal('-25.00')}
        ]

        with pytest.raises(BillingError):
            BillingService.create_invoice(patient.id, bad_items)

        # Verify transaction rolled back and no partial records were persisted
        assert Invoice.query.count() == initial_count


