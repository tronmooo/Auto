from flask import Blueprint

bp = Blueprint('payments', __name__)

from . import routes
