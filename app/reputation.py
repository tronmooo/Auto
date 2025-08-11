import os
import google.generativeai as genai
from googleapiclient.discovery import build
from google.oauth2 import service_account
from flask import current_app

SERVICE_ACCOUNT_FILE = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')

def get_google_api_service(service_name, version):
    """Builds and returns a Google API service object."""
    if not SERVICE_ACCOUNT_FILE:
        raise Exception("GOOGLE_APPLICATION_CREDENTIALS environment variable not set.")

    scopes = ['https://www.googleapis.com/auth/business.manage']
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=scopes)
    service = build(service_name, version, credentials=creds)
    return service

def get_google_reviews(business):
    """
    Fetches new reviews from the Google Business Profile API.
    """
    current_app.logger.info(f"Fetching Google reviews for {business.business_name}...")
    try:
        account_id = business.google_account_id
        location_id = business.google_location_id
        service = get_google_api_service('mybusinessreviews', 'v1')
        parent = f"accounts/{account_id}/locations/{location_id}"

        reviews_response = service.accounts().locations().reviews().list(
            parent=parent,
            filter='hasReply=false'
        ).execute()

        from googleapiclient.errors import HttpError

        reviews = reviews_response.get('reviews', [])
        current_app.logger.info(f"Found {len(reviews)} new reviews for {business.business_name}.")
        return reviews

    except HttpError as e:
        current_app.logger.error(f"HTTP error fetching Google reviews for {business.business_name}: {e}")
        return []
    except Exception as e:
        current_app.logger.error(f"Unexpected error fetching Google reviews for {business.business_name}: {e}")
        return []

def generate_reply_with_gemini(review, business):
    """
    Generates a personalized reply using the Gemini API.
    """
    current_app.logger.info(f"Generating Gemini reply for review: {review.get('comment', '')[:50]}...")
    try:
        genai.api_key = business.gemini_api_key
        model = genai.GenerativeModel('gemini-pro')

        reviewer_name = review.get('reviewer', {}).get('displayName', 'Valued Customer')
        star_rating = review.get('starRating', 'NOT_SPECIFIED').replace('STAR_RATING_', '')
        comment = review.get('comment', '')

        prompt = f"""
        You are an AI assistant for a high-end home service business named "{business.business_name}".
        Your task is to draft a personalized, professional, and friendly reply to a customer review.
        The business specializes in: {business.specialties}.

        Review Details:
        - Reviewer Name: {reviewer_name}
        - Star Rating: {star_rating} out of 5
        - Customer's Comment: "{comment}"

        Instructions:
        1.  Always thank the reviewer by name for their feedback.
        2.  If the rating is 4 or 5 stars, the tone should be positive and appreciative. Try to incorporate specific positive keywords from their review into your reply.
        3.  If the rating is 3 stars or less, the tone should be empathetic and concerned. Apologize for their experience and offer to make things right. Provide a generic "please contact our office" call to action, but do not invent a phone number or email.
        4.  Keep the reply concise (2-4 sentences).
        5.  Sign off with "The {business.business_name} Team".

        Draft the reply now.
        """

        response = model.generate_content(prompt)
        return response.text.strip()

    except Exception as e:
        current_app.logger.error(f"Error generating Gemini reply: {e}")
        return "Thank you for your feedback. We appreciate you taking the time to share your experience."

def post_google_reply(review_name, reply_text, business):
    """
    Posts a reply to a review on Google using the Business Profile API.
    """
    current_app.logger.info(f"Posting reply to review {review_name}...")
    try:
        service = get_google_api_service('mybusinessreviews', 'v1')
        from googleapiclient.errors import HttpError

        body = {"comment": reply_text}
        service.reviews().updateReply(name=review_name, body=body).execute()
        current_app.logger.info(f"Reply posted successfully to {review_name}.")

        # Increment counter on success
        if business.reviews_replied_count is None:
            business.reviews_replied_count = 0
        business.reviews_replied_count += 1
        # The commit will happen in the parent function `process_reviews_for_business`

    except HttpError as e:
        current_app.logger.error(f"HTTP error posting Google reply to {review_name}: {e}")
    except Exception as e:
        current_app.logger.error(f"Unexpected error posting Google reply to {review_name}: {e}")

def process_reviews_for_business(business):
    """
    Processes new reviews for a single business by fetching, generating a reply,
    and posting it back.
    """
    current_app.logger.info(f"Starting review processing for {business.business_name}...")
    if not all([business.google_api_key, business.gemini_api_key, business.google_account_id, business.google_location_id]):
        current_app.logger.warning(f"Skipping {business.business_name}: Missing API keys or Google account/location IDs.")
        return

    reviews_to_reply = get_google_reviews(business)
    if not reviews_to_reply:
        current_app.logger.info(f"No new reviews to process for {business.business_name}.")
        return

    for review in reviews_to_reply:
        reply_text = generate_reply_with_gemini(review, business)
        review_name = review.get('name')
        if review_name:
            post_google_reply(review_name, reply_text, business)

    # Commit any changes made during the process (e.g., incrementing counters)
    from .extensions import db
    db.session.commit()

    current_app.logger.info(f"Finished review processing for {business.business_name}.")

def schedule_review_processing():
    """
    A function to be called by the scheduler to process reviews for all businesses.
    """
    app = current_app._get_current_object()
    with app.app_context():
        from .models import BusinessProfile
        app.logger.info("Scheduler: Running review processing job.")
        businesses = BusinessProfile.query.all()
        if not businesses:
            app.logger.info("Scheduler: No businesses found to process.")
            return

        for business in businesses:
            process_reviews_for_business(business)
        app.logger.info("Scheduler: Review processing job finished.")
