from flask import Blueprint

bp = Blueprint('clients', __name__)

from . import routes
