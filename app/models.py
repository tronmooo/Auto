import os
from dotenv import load_dotenv
from sqlalchemy_utils import EncryptedType
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from .extensions import db

load_dotenv()

# The secret key for encryption should be loaded from environment variables
# and should be a 32-byte URL-safe base64-encoded key.
# For demonstration, we're using a key from the environment.
# In a real production app, this key management would be more robust.
secret_key = os.environ.get('SECRET_ENCRYPTION_KEY', 'default-key-is-not-secure-at-all')


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

    # Encrypted API keys
    google_api_key = db.Column(EncryptedType(db.String(512), secret_key))
    gemini_api_key = db.Column(EncryptedType(db.String(512), secret_key))

    # Google Business Profile specific IDs
    google_account_id = db.Column(db.String(128))
    google_location_id = db.Column(db.String(128))

    # Google Ads specific IDs and status
    google_ads_customer_id = db.Column(db.String(128))
    campaign_status = db.Column(db.String(64), default='Not Started')

    clients = db.relationship('Client', backref='business_profile', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<BusinessProfile {self.business_name}>'

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_profile_id = db.Column(db.Integer, db.ForeignKey('business_profile.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    job_description = db.Column(db.Text)
    job_completion_date = db.Column(db.Date)
    follow_up_sent_date = db.Column(db.DateTime)

    def __repr__(self):
        return f'<Client {self.name}>'
