import click
from app.extensions import db
from app.models.user import User, Role

def register_commands(app):
    @app.cli.command('create-admin')
    @click.option('--name', prompt='Admin Full Name', help='Administrator full name')
    @click.option('--email', prompt='Admin Email Address', help='Administrator email')
    @click.password_option('--password', prompt='Password', confirmation_prompt=True, help='Administrator password')
    def create_admin(name, email, password):
        """Safely create or verify the initial system administrator."""
        email = email.strip().lower()
        if len(password) < 8:
            click.echo(click.style('Error: Password must be at least 8 characters long.', fg='red'))
            return

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            if existing_user.is_admin():
                click.echo(click.style(f'Admin user with email {email} already exists.', fg='yellow'))
                if click.confirm('Do you want to reset their password?'):
                    existing_user.set_password(password)
                    existing_user.name = name.strip()
                    existing_user.is_active = True
                    db.session.commit()
                    click.echo(click.style(f'Admin {email} updated successfully.', fg='green'))
                return
            else:
                click.echo(click.style(f'User {email} exists but has role "{existing_user.role}".', fg='yellow'))
                if click.confirm('Promote this user to Admin and update password?'):
                    existing_user.role = Role.ADMIN
                    existing_user.name = name.strip()
                    existing_user.set_password(password)
                    existing_user.is_active = True
                    db.session.commit()
                    click.echo(click.style(f'User {email} promoted to Administrator.', fg='green'))
                return

        admin = User(
            name=name.strip(),
            email=email,
            role=Role.ADMIN,
            is_active=True
        )
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        click.echo(click.style(f'Initial administrator {name} <{email}> created successfully!', fg='green'))

    @app.cli.command('init-db')
    def init_db():
        """Initialize database tables."""
        db.create_all()
        click.echo(click.style('Database tables created successfully.', fg='green'))

    @app.cli.command('seed-demo-data')
    def seed_demo_data():
        """Seed realistic fictional Indian patients, doctors, appointments, prescriptions, and billing."""
        from datetime import date, datetime, timedelta, timezone
        from app.models.patient import Patient
        from app.models.appointment import Appointment, AppointmentStatus
        from app.models.visit import Visit, ClinicalAuditLog

        db.create_all()

        # 1. Seed Staff / Doctors (Indian Healthcare Context)
        doctor1 = User.query.filter_by(email='dr.sarah@clinicflow.local').first()
        if not doctor1:
            doctor1 = User(name='Dr. Ananya Sharma', email='dr.sarah@clinicflow.local', role=Role.DOCTOR, is_active=True)
            doctor1.set_password('Doctor1234!')
            db.session.add(doctor1)
        else:
            doctor1.name = 'Dr. Ananya Sharma'

        doctor2 = User.query.filter_by(email='dr.raj@clinicflow.local').first()
        if not doctor2:
            doctor2 = User(name='Dr. Rajesh Patel', email='dr.raj@clinicflow.local', role=Role.DOCTOR, is_active=True)
            doctor2.set_password('Doctor1234!')
            db.session.add(doctor2)
        else:
            doctor2.name = 'Dr. Rajesh Patel'

        receptionist = User.query.filter_by(email='reception@clinicflow.local').first()
        if not receptionist:
            receptionist = User(name='Pooja Kulkarni', email='reception@clinicflow.local', role=Role.RECEPTIONIST, is_active=True)
            receptionist.set_password('Recep1234!')
            db.session.add(receptionist)
        else:
            receptionist.name = 'Pooja Kulkarni'

        db.session.commit()

        # 2. Seed Fictional Indian Patients
        fictional_patients = [
            {
                'code': 'PAT-DEMO-001',
                'name': 'Aarav Verma',
                'dob': date(1988, 7, 14),
                'phone': '+91 98201 44521',
                'address': 'Flat 402, Shivam Apts, Andheri West, Mumbai, Maharashtra 400058',
                'emergency': 'Sunita Verma (Wife) - +91 98201 44522'
            },
            {
                'code': 'PAT-DEMO-002',
                'name': 'Priya Sundaram',
                'dob': date(1994, 3, 22),
                'phone': '+91 94440 12890',
                'address': '24/1, 2nd Main Road, Indiranagar, Bengaluru, Karnataka 560038',
                'emergency': 'Sundaram Ramanathan (Father) - +91 94440 12891'
            },
            {
                'code': 'PAT-DEMO-003',
                'name': 'Rohan Deshmukh',
                'dob': date(1976, 11, 5),
                'phone': '+91 98112 30491',
                'address': 'C-12, Sector 44, Noida, Uttar Pradesh 201301',
                'emergency': 'Meera Deshmukh (Wife) - +91 98112 30492'
            },
            {
                'code': 'PAT-DEMO-004',
                'name': 'Deepika Nair',
                'dob': date(2001, 9, 18),
                'phone': '+91 97455 61234',
                'address': '18, Panampilly Nagar, Kochi, Kerala 682036',
                'emergency': 'Anand Nair (Brother) - +91 97455 61235'
            }
        ]

        patient_objs = []
        for pdata in fictional_patients:
            patient = Patient.query.filter_by(patient_code=pdata['code']).first()
            if not patient:
                patient = Patient(
                    patient_code=pdata['code'],
                    full_name=pdata['name'],
                    date_of_birth=pdata['dob'],
                    phone=pdata['phone'],
                    address=pdata['address'],
                    emergency_contact=pdata['emergency']
                )
                db.session.add(patient)
            else:
                patient.full_name = pdata['name']
                patient.date_of_birth = pdata['dob']
                patient.phone = pdata['phone']
                patient.address = pdata['address']
                patient.emergency_contact = pdata['emergency']
            patient_objs.append(patient)

        db.session.commit()

        # 3. Seed Appointments for Today
        today = datetime.now().date()
        time1 = datetime.combine(today, datetime.strptime("09:30", "%H:%M").time())
        time2 = datetime.combine(today, datetime.strptime("10:30", "%H:%M").time())
        time3 = datetime.combine(today, datetime.strptime("11:30", "%H:%M").time())
        time4 = datetime.combine(today, datetime.strptime("14:30", "%H:%M").time())

        # Appointment 1: Checked in (Waiting queue)
        apt1 = Appointment.query.filter_by(patient_id=patient_objs[0].id, scheduled_time=time1).first()
        if not apt1:
            apt1 = Appointment(
                patient_id=patient_objs[0].id,
                doctor_id=doctor1.id,
                scheduled_time=time1,
                duration_minutes=30,
                status=AppointmentStatus.CHECKED_IN,
                reason='Viral fever, throat pain and dry cough since 3 days',
                check_in_time=time1 - timedelta(minutes=10)
            )
            db.session.add(apt1)

        # Appointment 2: In Consultation
        apt2 = Appointment.query.filter_by(patient_id=patient_objs[1].id, scheduled_time=time2).first()
        if not apt2:
            apt2 = Appointment(
                patient_id=patient_objs[1].id,
                doctor_id=doctor1.id,
                scheduled_time=time2,
                duration_minutes=30,
                status=AppointmentStatus.IN_CONSULTATION,
                reason='Follow-up BP check & seasonal allergic rhinitis',
                check_in_time=time2 - timedelta(minutes=15)
            )
            db.session.add(apt2)

        # Appointment 3: Scheduled
        apt3 = Appointment.query.filter_by(patient_id=patient_objs[2].id, scheduled_time=time3).first()
        if not apt3:
            apt3 = Appointment(
                patient_id=patient_objs[2].id,
                doctor_id=doctor2.id,
                scheduled_time=time3,
                duration_minutes=45,
                status=AppointmentStatus.SCHEDULED,
                reason='Annual preventive health checkup & HbA1c screening'
            )
            db.session.add(apt3)

        # Appointment 4: Completed with Consultation Visit
        apt4 = Appointment.query.filter_by(patient_id=patient_objs[3].id, scheduled_time=time4).first()
        if not apt4:
            apt4 = Appointment(
                patient_id=patient_objs[3].id,
                doctor_id=doctor2.id,
                scheduled_time=time4,
                duration_minutes=30,
                status=AppointmentStatus.COMPLETED,
                reason='Twisted left ankle during badminton game, acute swelling',
                check_in_time=time4 - timedelta(minutes=5)
            )
            db.session.add(apt4)
            db.session.flush()

            # Visit record
            visit = Visit(
                patient_id=patient_objs[3].id,
                doctor_id=doctor2.id,
                appointment_id=apt4.id,
                symptoms='Swelling and lateral tenderness over left ankle joint following badminton misstep.',
                diagnosis='Grade 1 lateral ankle ligament sprain (ATFL strain).',
                clinical_notes='Digital X-Ray left ankle shows no bone fracture. Crepe bandage applied. Advised rest, ice application, and elevation.',
                start_time=time4,
                end_time=time4 + timedelta(minutes=25)
            )
            db.session.add(visit)
            db.session.flush()

            audit = ClinicalAuditLog(
                visit_id=visit.id,
                user_id=doctor2.id,
                action='created',
                changes_json='{"diagnosis": "Grade 1 lateral ankle sprain", "status": "completed"}'
            )
            db.session.add(audit)

            # 4. Seed Prescription with familiar Indian pharmaceuticals
            from app.models.prescription import Prescription, PrescriptionItem
            from app.models.billing import Invoice, InvoiceItem, Payment, PaymentMethod, InvoiceStatus
            from decimal import Decimal

            rx = Prescription(
                prescription_number='RX-DEMO-261024',
                visit_id=visit.id,
                doctor_id=doctor2.id,
                patient_id=patient_objs[3].id,
                notes='Apply ice packs for 15 mins thrice daily. Avoid heavy weight bearing for 4 days.'
            )
            db.session.add(rx)
            db.session.flush()

            item1 = PrescriptionItem(
                prescription_id=rx.id,
                medicine_name='Tab. Zerodol-SP (Aceclofenac + Paracetamol + Serratiopeptidase)',
                strength='100mg/325mg/15mg',
                dosage='1 tablet',
                route='Oral',
                frequency='Twice daily after food (BD)',
                duration='5 days',
                instructions='Pain relief and anti-inflammatory.'
            )
            item2 = PrescriptionItem(
                prescription_id=rx.id,
                medicine_name='Cap. Pan-D (Pantoprazole + Domperidone)',
                strength='40mg/30mg',
                dosage='1 capsule',
                route='Oral',
                frequency='Once daily before breakfast (OD)',
                duration='5 days',
                instructions='Antacid for gastric protection.'
            )
            item3 = PrescriptionItem(
                prescription_id=rx.id,
                medicine_name='Dynaplast / Crepe Bandage',
                strength='10 cm',
                dosage='1 application',
                route='Topical',
                frequency='Continuous support',
                duration='7 days',
                instructions='Re-wrap firmly without restricting arterial blood flow.'
            )
            db.session.add_all([item1, item2, item3])

            # 5. Seed Invoice and Payment in Indian Rupees (INR)
            inv = Invoice(
                invoice_number='INV-DEMO-261024',
                patient_id=patient_objs[3].id,
                visit_id=visit.id,
                created_by_id=receptionist.id,
                notes='Outpatient consultation, digital radiography and immobilization bandage.'
            )
            db.session.add(inv)
            db.session.flush()

            line1 = InvoiceItem(
                invoice_id=inv.id,
                description='Specialist Consultation (Orthopedics)',
                quantity=1,
                unit_price=Decimal('800.00'),
                total_price=Decimal('800.00')
            )
            line2 = InvoiceItem(
                invoice_id=inv.id,
                description='Digital X-Ray Left Ankle (AP & Lateral Views)',
                quantity=1,
                unit_price=Decimal('650.00'),
                total_price=Decimal('650.00')
            )
            line3 = InvoiceItem(
                invoice_id=inv.id,
                description='Crepe Bandage & Immobilization Application',
                quantity=1,
                unit_price=Decimal('250.00'),
                total_price=Decimal('250.00')
            )
            db.session.add_all([line1, line2, line3])
            inv.subtotal = Decimal('1700.00')
            inv.discount = Decimal('100.00')
            inv.total_amount = Decimal('1600.00')

            # Payment via UPI (PhonePe / Google Pay / Paytm)
            payment = Payment(
                receipt_number='RCP-DEMO-261024',
                invoice_id=inv.id,
                received_by_id=receptionist.id,
                amount=Decimal('1600.00'),
                payment_method=PaymentMethod.UPI,
                reference='UPI-TXN-429910482910@okaxis',
                notes='Paid via UPI QR code on front desk scanner.'
            )
            db.session.add(payment)
            inv.amount_paid = Decimal('1600.00')
            inv.status = InvoiceStatus.PAID

        db.session.commit()
        click.echo(click.style('Indian demo dataset seeded: Indian patients, doctors, UPI billing and prescription data.', fg='green'))
