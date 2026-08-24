from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.main import bp
from app.main.forms import EditProfileForm
from app.models import Round, User


@bp.route('/')
@bp.route('/index')
@login_required
def index():
    rounds = (Round.query.filter_by(user_id=current_user.id)
              .order_by(Round.played_date.desc(), Round.id.desc())
              .limit(10).all())
    return render_template('main/index.html', title='Home', rounds=rounds)


@bp.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    rounds = (Round.query.filter_by(user_id=user.id)
              .order_by(Round.played_date.desc(), Round.id.desc())
              .limit(10).all())
    return render_template('main/user.html', user=user, rounds=rounds)


@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('main.edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('main/edit_profile.html', title='Edit Profile',
                            form=form)
