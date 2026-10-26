from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user

def role_required(*allowed_roles):
    """
    Decorator to restrict route access to specific roles.
    Redirects unauthenticated users or raises 403 Forbidden for unauthorized roles.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            if not current_user.is_active:
                flash('Your account has been deactivated.', 'danger')
                return redirect(url_for('auth.logout'))
            if current_user.role not in allowed_roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    return role_required('admin')(f)

def staff_required(f):
    """Allows admin, doctor, and receptionist."""
    return role_required('admin', 'doctor', 'receptionist')(f)

def clinical_required(f):
    """Allows admin and doctor for clinical information/records."""
    return role_required('admin', 'doctor')(f)
