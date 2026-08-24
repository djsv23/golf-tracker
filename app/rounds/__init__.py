from flask import Blueprint

bp = Blueprint('rounds', __name__, template_folder='templates')

from app.rounds import routes  # noqa: E402,F401
