from flask import Flask
from config import Config
from .extensions import db, login_manager, migrate, scheduler

from flask_dance.contrib.google import make_google_blueprint

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Flask extensions here
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login' # Set the login view

    if not scheduler.running:
        scheduler.init_app(app)
        scheduler.start()

    # Schedule the jobs
    if scheduler.get_job('schedule-review-processing') is None:
        scheduler.add_job(id='schedule-review-processing', func='app.reputation:schedule_review_processing', trigger='interval', minutes=60)

    if scheduler.get_job('schedule-follow-up-processing') is None:
        scheduler.add_job(id='schedule-follow-up-processing', func='app.followup:process_client_follow_ups', trigger='interval', days=1)


    # Register blueprints here
    from .main import bp as main_bp
    app.register_blueprint(main_bp)

    from .auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    google_bp = make_google_blueprint(
        client_id=app.config['GOOGLE_OAUTH_CLIENT_ID'],
        client_secret=app.config['GOOGLE_OAUTH_CLIENT_SECRET'],
        scope=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"],
        redirect_url="/auth/login/google"
    )
    app.register_blueprint(google_bp, url_prefix="/login")

    from .payments_bp import bp as payments_bp
    app.register_blueprint(payments_bp)

    from .profile_bp import bp as profile_bp
    app.register_blueprint(profile_bp)

    from .clients_bp import bp as clients_bp
    app.register_blueprint(clients_bp)

    # Import models here to ensure they are registered with SQLAlchemy
    from . import models

    @login_manager.user_loader
    def load_user(user_id):
        return models.User.query.get(int(user_id))

    return app
