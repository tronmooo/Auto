from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length

class ProfileForm(FlaskForm):
    business_name = StringField('Business Name', validators=[DataRequired(), Length(min=2, max=120)])
    service_area = StringField('Service Area (e.g., "Redondo Beach, CA")', validators=[DataRequired(), Length(min=2, max=200)])
    specialties = TextAreaField('Specialties (comma-separated)', validators=[DataRequired()])

    google_account_id = StringField('Google Account ID', validators=[DataRequired()])
    google_location_id = StringField('Google Location ID', validators=[DataRequired()])
    google_ads_customer_id = StringField('Google Ads Customer ID (without hyphens)', validators=[DataRequired()])

    # The API keys are large text areas
    google_api_key = TextAreaField('Google API Key (Service Account JSON)', validators=[DataRequired()])
    gemini_api_key = StringField('Gemini API Key', validators=[DataRequired()])

    submit = SubmitField('Save Profile')
