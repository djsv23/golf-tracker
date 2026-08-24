from flask import jsonify, render_template
from flask_login import current_user, login_required

from app.dashboard import bp
from app.services.analytics import dashboard_data


@bp.route('/')
@login_required
def index():
    data = dashboard_data(current_user.id)
    return render_template('dashboard/index.html', data=data)


@bp.route('/data.json')
@login_required
def data_json():
    return jsonify(dashboard_data(current_user.id))
