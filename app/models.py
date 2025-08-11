from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from .extensions import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    google_oauth_id = db.Column(db.String(128), unique=True)
    is_subscribed = db.Column(db.Boolean, default=False, nullable=False)

    business_profile = db.relationship('BusinessProfile', backref='user', uselist=False, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'

class BusinessProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    business_name = db.Column(db.String(120), nullable=False)
    service_area = db.Column(db.String(200), nullable=False)
    specialties = db.Column(db.Text) # e.g., "kitchen remodel, bathroom remodel"

    # Placeholder for encrypted API keys
    # In a real app, use something like sqlalchemy-utils' EncryptedType
    google_api_key = db.Column(db.String(256))
    gemini_api_key = db.Column(db.String(256))

    def __repr__(self):
        return f'<BusinessProfile {self.business_name}>'
