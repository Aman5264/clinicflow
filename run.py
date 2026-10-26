from app import create_app, db
from app.models.user import User, Role
from app.models.patient import Patient
from app.models.appointment import Appointment, AppointmentStatus
from app.models.visit import Visit, ClinicalAuditLog

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Role': Role,
        'Patient': Patient,
        'Appointment': Appointment,
        'AppointmentStatus': AppointmentStatus,
        'Visit': Visit,
        'ClinicalAuditLog': ClinicalAuditLog
    }

if __name__ == '__main__':
    app.run(debug=True)
