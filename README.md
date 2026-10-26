# ClinicFlow - Clinical Workflow, Scheduling & Consultation Management System

A healthcare management application developed with Flask, SQLAlchemy, Flask-Login, and Bootstrap 5.

---

## Core Capabilities

### 1. Authentication & Role-Based Access Control (RBAC)
- **User Model**: `id`, `name`, `email`, `password_hash`, `role`, `is_active`, `created_at`.
- **Roles**:
  - `admin`: Full system control, create/edit staff accounts, reset access, manage all patient records.
  - `doctor`: Clinical consultations access, record symptoms/diagnoses, manage appointments and waiting room calls.
  - `receptionist`: Register patients, book and reschedule appointments, perform patient check-in into the lobby queue.
- **Flask-Login** session authentication with `remember_me` support.
- **Secure Password Hashing** using Werkzeug PBKDF2/SHA256 with salting.
- **Safe Initial Admin Creation CLI**: Public registration is disabled to prevent unauthorized account creation. Administrators create staff accounts directly or via CLI.
- **Account Management**: Logged-in staff can update their password and view account roles.

### 2. Patient Management System
- **Patient Model**: `patient_code` (unique generated format `PAT-YYMMDD-XXXX`), `full_name`, `date_of_birth`, `phone`, `address`, `emergency_contact`, `is_archived`, `archive_reason`, `created_at`, `updated_at`.
- **Duplicate Prevention**: Checks for matching full name, date of birth, and phone number on active records before submission.
- **Search & Filter**: Search patients by patient code, name, or phone number. Supports active vs. archived filtering.
- **Pagination**: Server-side pagination with query preservation.
- **Validation**:
  - Date of birth cannot be in the future.
  - Valid telephone format check (7–15 digits).
  - Required addresses and emergency contacts.
- **Archive & Restore**: Archive patients with required reason tracking, and ability to restore archived records.

### 3. Appointment Management & Scheduling
- **Appointment Model**: `patient_id`, `doctor_id`, `scheduled_time`, `duration_minutes`, `status`, `reason`, `notes`, `check_in_time`, timestamps.
- **Statuses & Transitions**:
  - `scheduled` &rarr; `checked_in` | `cancelled` | `no_show`
  - `checked_in` &rarr; `in_consultation` | `cancelled`
  - `in_consultation` &rarr; `completed` | `cancelled`
  - Invalid transitions are strictly blocked with validation exceptions on the server.
- **Conflict Prevention**: Prevents overlapping bookings for the same doctor across active appointments (`startA < endB and endA > startB`).
- **Daily Schedule View**: Filterable by date, attending doctor, and status.
- **Live Waiting Queue**: Sorts patients in clinic lobby by consultation state and arrival time.

### 4. Consultations & Clinical Records
- **Visit Model**: `patient_id`, `doctor_id`, `appointment_id`, `symptoms`, `diagnosis`, `clinical_notes`, `start_time`, `end_time`.
- **Duplicate Visit Prevention**: Once an appointment consultation is recorded, subsequent attempts to create duplicate visits for that same appointment are blocked.
- **Clinical Audit Logging**: Records every creation and edit with JSON delta diffs (`ClinicalAuditLog`).
- **Role-Restricted Views**: Clinical diagnoses and consultation notes are accessible only to Doctors and Administrators. Receptionists see patient scheduling and demographics.

---

## Setup Instructions

### 1. Activate the Virtual Environment
**PowerShell:**
```powershell
.\venv\Scripts\Activate.ps1
```

**Command Prompt:**
```cmd
venv\Scripts\activate.bat
```

**Git Bash / Linux / macOS:**
```bash
source venv/Scripts/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Initialize the Database
```bash
flask init-db
```

### 4. Create Initial Administrator
```bash
flask create-admin
```
Or with CLI arguments:
```bash
flask create-admin --name "Admin User" --email "admin@clinicflow.local" --password "Admin1234!"
```

### 5. Seed Fictional Test Dataset
Populates realistic fictional patients, doctors, scheduled appointments, waiting queue entries, and completed consultation visits:
```bash
flask seed-demo-data
```

**Pre-seeded Demo Accounts:**
- **Doctor**: `dr.sarah@clinicflow.local` / `Doctor1234!`
- **Doctor**: `dr.raj@clinicflow.local` / `Doctor1234!`
- **Receptionist**: `reception@clinicflow.local` / `Recep1234!`
- **Administrator**: Created via `flask create-admin`

### 6. Run the Application
```bash
python run.py
```
Open `http://127.0.0.1:5000` in your web browser.

---

## Running the Automated Test Suite

Run all 20 automated pytest tests:
```bash
pytest -v
```

The test suite covers:
1. `test_password_hashing`: Salted hash verification
2. `test_login_success_and_logout`: Authentication lifecycle
3. `test_login_invalid_credentials`: Credential security
4. `test_login_inactive_user_blocked`: Deactivated account blocking
5. `test_cli_create_admin`: Safe CLI administration
6. `test_role_authorization_receptionist_blocked_from_admin_users`: 403 authorization guard
7. `test_admin_access_user_management`: Admin role access
8. `test_unauthenticated_redirect`: Login redirection
9. `test_patient_registration_and_detail`: Patient CRUD
10. `test_patient_validation_future_dob`: Server-side DOB validation
11. `test_patient_duplicate_record_check`: Patient duplicate detection
12. `test_patient_search_and_pagination`: Multi-attribute search & pagination
13. `test_patient_archive_and_restore`: Patient soft deletion and recovery
14. `test_appointment_booking_and_doctor_conflict`: Overlap detection for doctors
15. `test_appointment_reschedule_and_conflict`: Rescheduling collision validation
16. `test_appointment_lifecycle_and_state_transitions`: State machine enforcement
17. `test_waiting_queue_ordering`: Queue sorting based on check-in arrival time
18. `test_consultation_creation_and_duplicate_prevention`: Duplicate visit prevention
19. `test_consultation_audit_logging`: Clinical audit trail with changes diff
20. `test_clinical_route_permissions`: Role permission guards for clinical routes
