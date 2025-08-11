import stripe
from flask import current_app, request, jsonify
from .models import User
from .extensions import db

def create_checkout_session(user):
    """
    Creates a Stripe Checkout session for a subscription.
    """
    stripe.api_key = current_app.config['STRIPE_SECRET_KEY']

    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    'price': current_app.config['STRIPE_PRICE_ID'],
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=request.host_url + 'dashboard?success=true',
            cancel_url=request.host_url + 'dashboard?canceled=true',
            customer_email=user.email,
            metadata={
                'user_id': user.id
            }
        )
        return checkout_session
    except Exception as e:
        return str(e)


def handle_stripe_webhook():
    """
    Handles incoming webhooks from Stripe.
    """
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    webhook_secret = current_app.config['STRIPE_WEBHOOK_SECRET']

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        # Invalid payload
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return 'Invalid signature', 400

    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session.get('metadata', {}).get('user_id')
        if user_id:
            user = User.query.get(user_id)
            if user:
                user.is_subscribed = True
                db.session.commit()
                print(f"User {user.email} (ID: {user_id}) has successfully subscribed.")

    return 'Success', 200
