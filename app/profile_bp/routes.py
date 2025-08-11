from flask import render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from . import bp
from .forms import ProfileForm
from ..models import BusinessProfile
from ..extensions import db

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    # Get the user's existing profile or create a new one
    business_profile = current_user.business_profile or BusinessProfile(user=current_user)
    form = ProfileForm(obj=business_profile)

    if form.validate_on_submit():
        form.populate_obj(business_profile)

        # If it's a new profile, add it to the session
        if not current_user.business_profile:
            db.session.add(business_profile)

        db.session.commit()
        flash('Your profile has been updated.', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('profile/profile.html', title='Business Profile', form=form)
