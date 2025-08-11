from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, DateField
from wtforms.validators import DataRequired, Email, Length

class ClientForm(FlaskForm):
    name = StringField('Client Name', validators=[DataRequired(), Length(max=120)])
    email = StringField('Client Email', validators=[DataRequired(), Email()])
    job_description = TextAreaField('Job Description', validators=[DataRequired()])
    job_completion_date = DateField('Job Completion Date (YYYY-MM-DD)', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Save Client')
