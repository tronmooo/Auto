import os
import datetime
from flask import current_app
import google.generativeai as genai
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from .models import Client, BusinessProfile
from .extensions import db

def generate_follow_up_email(client, business):
    """
    Generates a personalized follow-up email using the Gemini API.
    """
    current_app.logger.info(f"Generating follow-up email for client {client.name}...")
    try:
        genai.api_key = business.gemini_api_key
        model = genai.GenerativeModel('gemini-pro')

        prompt = f"""
        You are an AI assistant for a high-end home service business named "{business.business_name}".
        Your task is to draft a personalized, friendly, and professional follow-up email to a past client.
        The business specializes in: {business.specialties}.

        Client & Job Details:
        - Client Name: {client.name}
        - Job Description: {client.job_description}
        - Job Completion Date: {client.job_completion_date}

        Instructions:
        1.  Address the client by name.
        2.  Mention the specific job that was completed and when it was completed to personalize the email.
        3.  The primary goal is to thank them for their business and gently ask for a review on Google. Do NOT include a link, just mention they can find the business on Google.
        4.  The secondary goal is to ask for referrals. Mention that referrals are the cornerstone of the business.
        5.  Keep the tone light, appreciative, and not overly "salesy".
        6.  Sign off with the business owner's name (use a placeholder like "[Owner's Name]") and the business name.

        The email should have a subject line and a body. Format the output as:
        Subject: [Your Subject Line]
        Body: [Your Email Body]
        """

        response = model.generate_content(prompt)

        subject = "Following up on your recent project"
        body = response.text
        if "Subject:" in response.text and "Body:" in response.text:
            parts = response.text.split("Body:")
            subject = parts[0].replace("Subject:", "").strip()
            body = parts[1].strip()

        return {"subject": subject, "body": body}

    except Exception as e:
        current_app.logger.error(f"Error generating Gemini follow-up email: {e}")
        return None


def send_email(to_email, subject, body):
    """
    Sends an email using the SendGrid API.
    """
    sendgrid_api_key = current_app.config.get('SENDGRID_API_KEY')
    if not sendgrid_api_key:
        current_app.logger.error("SENDGRID_API_KEY not set. Cannot send email.")
        return

    from_email = 'no-reply@localvortex.ai'
    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=subject,
        html_content=body.replace('\n', '<br>'))
    try:
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(message)
        current_app.logger.info(f"Email sent to {to_email} with status code {response.status_code}")
    except Exception as e:
        current_app.logger.error(f"Error sending email via SendGrid: {e}")


def process_client_follow_ups():
    """
    Finds clients who are due for a follow-up email and sends it.
    """
    app = current_app._get_current_object()
    with app.app_context():
        app.logger.info("Scheduler: Running client follow-up job.")

        seven_days_ago = datetime.date.today() - datetime.timedelta(days=7)
        clients_to_follow_up = Client.query.filter(
            Client.job_completion_date == seven_days_ago,
            Client.follow_up_sent_date.is_(None)
        ).all()

        if not clients_to_follow_up:
            app.logger.info("Scheduler: No clients due for follow-up today.")
            return

        for client in clients_to_follow_up:
            business = client.business_profile
            email_content = generate_follow_up_email(client, business)
            if email_content:
                send_email(client.email, email_content['subject'], email_content['body'])
                client.follow_up_sent_date = datetime.datetime.utcnow()
                db.session.commit()

        app.logger.info("Scheduler: Client follow-up job finished.")
