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
        budget = form.budget.data
        if not current_user.business_profile:
            flash('You must create a business profile first.', 'warning')
            return redirect(url_for('main.dashboard')) # Or a profile creation page

        manage_ad_campaign(current_user.business_profile, budget)
        flash(f'Successfully started your ad campaign with a daily budget of ${budget}!', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('main/dashboard.html', title='Dashboard', form=form)
