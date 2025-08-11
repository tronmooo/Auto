from flask import render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from . import bp
from ..auth.forms import AdBudgetForm
from ..ads import manage_ad_campaign

@bp.route('/')
@bp.route('/index')
def index():
    return "<h1>Welcome to LocalVortex AI</h1>"

@bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if not current_user.is_subscribed:
        return redirect(url_for('payments.subscribe'))

    form = AdBudgetForm()
    if form.validate_on_submit():
        budget_decimal = form.budget.data
        budget_micros = int(budget_decimal * 1_000_000)

        if not current_user.business_profile or not current_user.business_profile.google_ads_customer_id:
            flash('Please complete your business profile, including the Google Ads Customer ID.', 'warning')
            return redirect(url_for('profile.profile'))

        manage_ad_campaign(current_user.business_profile, budget_micros)
        flash(f'Ad campaign creation process has been started with a daily budget of ${budget_decimal}. Check the status on your dashboard.', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('main/dashboard.html', title='Dashboard', form=form)
