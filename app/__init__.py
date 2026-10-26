from flask import Flask, render_template
from config import Config
from app.extensions import db, login_manager, csrf

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Register Blueprints
    from app.routes.auth import bp as auth_bp
    from app.routes.patients import bp as patients_bp
    from app.routes.main import bp as main_bp
    from app.routes.appointments import bp as appointments_bp
    from app.routes.consultations import bp as consultations_bp
    from app.routes.prescriptions import bp as prescriptions_bp
    from app.routes.billing import bp as billing_bp
    from app.routes.reports import bp as reports_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(patients_bp, url_prefix='/patients')
    app.register_blueprint(appointments_bp, url_prefix='/appointments')
    app.register_blueprint(consultations_bp, url_prefix='/consultations')
    app.register_blueprint(prescriptions_bp, url_prefix='/prescriptions')
    app.register_blueprint(billing_bp, url_prefix='/billing')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(main_bp)

    # Register CLI Commands
    from app.commands import register_commands
    register_commands(app)

    # Register Error Handlers
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    return app
