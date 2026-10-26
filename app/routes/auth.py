from urllib.parse import urlsplit
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.user import User, Role
from app.forms import LoginForm, ChangePasswordForm, UserCreateForm, UserEditForm
from app.security import admin_required

bp = Blueprint('auth', __name__)

def is_safe_redirect_url(target):
    if not target:
        return False
    ref_url = urlsplit(request.host_url)
    test_url = urlsplit(target)
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc or not test_url.netloc

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact an administrator.', 'danger')
                return render_template('auth/login.html', form=form)

            login_user(user, remember=form.remember.data)
            flash(f'Welcome back, {user.name}!', 'success')
            next_page = request.args.get('next')
            if next_page and is_safe_redirect_url(next_page):
                return redirect(next_page)
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('auth/login.html', form=form)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been successfully logged out.', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    password_form = ChangePasswordForm()
    if password_form.validate_on_submit():
        if not current_user.check_password(password_form.current_password.data):
            flash('Current password verification failed.', 'danger')
        else:
            try:
                current_user.set_password(password_form.new_password.data)
                db.session.commit()
                flash('Your password has been updated successfully.', 'success')
                return redirect(url_for('auth.account'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error updating password: {str(e)}', 'danger')

    return render_template('auth/account.html', password_form=password_form)

# Admin User Management Routes
@bp.route('/users')
@admin_required
def user_list():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('auth/users.html', users=users)

@bp.route('/users/new', methods=['GET', 'POST'])
@admin_required
def user_create():
    form = UserCreateForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        existing = User.query.filter_by(email=email).first()
        if existing:
            flash(f'User with email {email} already exists.', 'danger')
            return render_template('auth/user_form.html', form=form, title='Create New User')

        user = User(
            name=form.name.data.strip(),
            email=email,
            role=form.role.data,
            is_active=True
        )
        try:
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash(f'User {user.name} ({user.role}) created successfully.', 'success')
            return redirect(url_for('auth.user_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to create user: {str(e)}', 'danger')

    return render_template('auth/user_form.html', form=form, title='Create New User')

@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def user_edit(user_id):
    user = db.get_or_404(User, user_id)
    form = UserEditForm(obj=user)

    if form.validate_on_submit():
        new_email = form.email.data.strip().lower()
        existing = User.query.filter(User.email == new_email, User.id != user.id).first()
        if existing:
            flash(f'Another user with email {new_email} already exists.', 'danger')
            return render_template('auth/user_form.html', form=form, title=f'Edit User: {user.name}')

        # Prevent admin from deactivating or demoting the last active admin
        if user.is_admin() and (not form.is_active.data or form.role.data != Role.ADMIN):
            admin_count = User.query.filter_by(role=Role.ADMIN, is_active=True).count()
            if admin_count <= 1:
                flash('Cannot deactivate or remove admin role from the only active administrator.', 'danger')
                return render_template('auth/user_form.html', form=form, title=f'Edit User: {user.name}')

        user.name = form.name.data.strip()
        user.email = new_email
        user.role = form.role.data
        user.is_active = form.is_active.data
        try:
            db.session.commit()
            flash(f'User {user.name} updated successfully.', 'success')
            return redirect(url_for('auth.user_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to update user: {str(e)}', 'danger')

    return render_template('auth/user_form.html', form=form, title=f'Edit User: {user.name}')
