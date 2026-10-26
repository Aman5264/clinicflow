from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db, login_manager

class Role:
    ADMIN = 'admin'
    DOCTOR = 'doctor'
    RECEPTIONIST = 'receptionist'
    ALL_ROLES = [ADMIN, DOCTOR, RECEPTIONIST]

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(30), nullable=False, default=Role.RECEPTIONIST)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def set_password(self, password: str) -> None:
        if not password or len(password) < 8:
            raise ValueError('Password must be at least 8 characters long.')
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash or not password:
            return False
        return check_password_hash(self.password_hash, password)

    def has_role(self, *roles: str) -> bool:
        return self.role in roles

    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    def is_doctor(self) -> bool:
        return self.role == Role.DOCTOR

    def is_receptionist(self) -> bool:
        return self.role == Role.RECEPTIONIST

    def __repr__(self) -> str:
        return f'<User {self.email} ({self.role})>'

@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None
