from flask import render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from . import bp
from .forms import ClientForm
from ..models import Client
from ..extensions import db

@bp.route('/clients')
@login_required
def list_clients():
    clients = current_user.business_profile.clients.order_by(Client.job_completion_date.desc()).all()
    return render_template('clients/list.html', clients=clients, title="Clients")

@bp.route('/clients/add', methods=['GET', 'POST'])
@login_required
def add_client():
    form = ClientForm()
    if form.validate_on_submit():
        new_client = Client(
            business_profile_id=current_user.business_profile.id,
            name=form.name.data,
            email=form.email.data,
            job_description=form.job_description.data,
            job_completion_date=form.job_completion_date.data
        )
        db.session.add(new_client)
        db.session.commit()
        flash('Client added successfully.', 'success')
        return redirect(url_for('clients.list_clients'))
    return render_template('clients/form.html', form=form, title="Add Client")

@bp.route('/clients/edit/<int:client_id>', methods=['GET', 'POST'])
@login_required
def edit_client(client_id):
    client = Client.query.get_or_404(client_id)
    # Ensure the client belongs to the current user's business
    if client.business_profile_id != current_user.business_profile.id:
        abort(403)

    form = ClientForm(obj=client)
    if form.validate_on_submit():
        form.populate_obj(client)
        db.session.commit()
        flash('Client updated successfully.', 'success')
        return redirect(url_for('clients.list_clients'))
    return render_template('clients/form.html', form=form, title="Edit Client")

@bp.route('/clients/delete/<int:client_id>', methods=['POST'])
@login_required
def delete_client(client_id):
    client = Client.query.get_or_404(client_id)
    if client.business_profile_id != current_user.business_profile.id:
        abort(403)

    db.session.delete(client)
    db.session.commit()
    flash('Client deleted successfully.', 'success')
    return redirect(url_for('clients.list_clients'))
