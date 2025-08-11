from flask import redirect, flash, render_template
from flask_login import login_required, current_user
from . import bp
from app.payments import create_checkout_session, handle_stripe_webhook

@bp.route('/subscribe')
@login_required
def subscribe():
    """Renders the subscription page."""
    return render_template('payments/subscribe.html', title='Subscribe')

@bp.route('/create-checkout-session')
@login_required
def create_stripe_checkout():
    """Creates and redirects the user to a Stripe checkout page."""
    checkout_session = create_checkout_session(current_user)
    if isinstance(checkout_session, str):
        flash(f'Error creating checkout session: {checkout_session}', 'danger')
        return redirect(url_for('main.dashboard'))
    return redirect(checkout_session.url, code=303)

@bp.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    """Endpoint for Stripe to send webhook events."""
    return handle_stripe_webhook()
