import os
import google.generativeai as genai
from googleapiclient.discovery import build
from google.oauth2 import service_account
from flask import current_app

# It's assumed that the user will provide a service account JSON file
# for authentication with Google APIs. The path to this file would be
# stored in the environment. For now, this is a placeholder.
# In a real app, you would load this from a secure location.
SERVICE_ACCOUNT_FILE = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')

def get_google_api_service(service_name, version):
    """Builds and returns a Google API service object."""
    if not SERVICE_ACCOUNT_FILE:
        raise Exception("GOOGLE_APPLICATION_CREDENTIALS environment variable not set.")

    # Define the scopes needed for the Business Profile API
    scopes = ['https://www.googleapis.com/auth/business.manage']

    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=scopes)

    service = build(service_name, version, credentials=creds)
    return service

def get_google_reviews(business):
    """
    Fetches new reviews from the Google Business Profile API.
    This is a simplified example. A real implementation would need to handle
    pagination and robust error checking.
    """
    print(f"Fetching Google reviews for {business.business_name}...")
    try:
        # These IDs would be stored as part of the business profile
        account_id = business.google_account_id
        location_id = business.google_location_id

        # In a real app, you'd get the service differently, probably
        # reusing a single service object.
        service = get_google_api_service('mybusinessreviews', 'v1')

        # The parent resource name for listing reviews
        parent = f"accounts/{account_id}/locations/{location_id}"

        # List reviews, filtering for those without replies
        reviews_response = service.accounts().locations().reviews().list(
            parent=parent,
            filter='hasReply=false'
        ).execute()

        reviews = reviews_response.get('reviews', [])
        print(f"Found {len(reviews)} new reviews.")
        return reviews

    except Exception as e:
        print(f"Error fetching Google reviews: {e}")
        return []


def generate_reply_with_gemini(review, business):
    """
    Generates a personalized reply using the Gemini API.
    """
    print(f"Generating Gemini reply for review: {review.get('comment', '')[:50]}...")

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
        print(f"Error generating Gemini reply: {e}")
        return "Thank you for your feedback. We appreciate you taking the time to share your experience."


def post_google_reply(review_name, reply_text):
    """
    Posts a reply to a review on Google using the Business Profile API.
    """
    print(f"Posting reply to review {review_name}...")
    try:
        service = get_google_api_service('mybusinessreviews', 'v1')

        # The body of the request contains the reply text
        body = {
            "comment": reply_text
        }

        # The 'name' of the review is its unique identifier for the API
        service.reviews().updateReply(name=review_name, body=body).execute()

        print("Reply posted successfully.")
    except Exception as e:
        print(f"Error posting Google reply: {e}")


def process_reviews_for_business(business):
    """
    Processes new reviews for a single business by fetching, generating a reply,
    and posting it back.
    """
    print(f"Starting review processing for {business.business_name}...")

    if not all([business.google_api_key, business.gemini_api_key, business.google_account_id, business.google_location_id]):
        print(f"Skipping {business.business_name}: Missing API keys or Google account/location IDs.")
        return

    reviews_to_reply = get_google_reviews(business)

    if not reviews_to_reply:
        print(f"No new reviews to process for {business.business_name}.")
        return

    for review in reviews_to_reply:
        reply_text = generate_reply_with_gemini(review, business)
        review_name = review.get('name') # The unique ID for the review
        if review_name:
            post_google_reply(review_name, reply_text)

    print(f"Finished review processing for {business.business_name}.")


def schedule_review_processing():
    """
    A function to be called by the scheduler to process reviews for all businesses.
    """
    app = current_app._get_current_object()
    with app.app_context():
        from .models import BusinessProfile
        print("Scheduler running: Checking for businesses to process...")
        businesses = BusinessProfile.query.all()
        if not businesses:
            print("No businesses found to process.")
            return

        for business in businesses:
            process_reviews_for_business(business)
        print("Scheduler run finished.")
