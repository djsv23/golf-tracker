from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import select

from app.extensions import db
from app.models.course import TeeSet
from app.models.round import HoleScore, Round
from app.rounds import bp
from app.rounds.forms import RoundSetupForm, ScorecardForm
from app.services.scoring import recalculate


@bp.route('/')
@login_required
def list_rounds():
    page = request.args.get('page', 1, type=int)
    stmt = (select(Round).filter_by(user_id=current_user.id)
            .order_by(Round.played_date.desc(), Round.id.desc()))
    pagination = db.paginate(stmt, page=page, per_page=20, error_out=False)
    return render_template('rounds/list.html', pagination=pagination,
                            rounds=pagination.items)


@bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    form = RoundSetupForm()
    if form.validate_on_submit():
        return redirect(url_for('rounds.new_scorecard', tee_set_id=form.tee_set_id.data))
    return render_template('rounds/setup.html', form=form)


@bp.route('/new/scorecard', methods=['GET', 'POST'])
@login_required
def new_scorecard():
    tee_set_id = request.values.get('tee_set_id', type=int)
    if not tee_set_id:
        abort(400)
    tee_set = db.get_or_404(TeeSet, tee_set_id)

    if request.method == 'GET':
        form = ScorecardForm(tee_set_id=tee_set_id)
        for _ in tee_set.holes:
            form.holes.append_entry()
    else:
        form = ScorecardForm()

    if form.validate_on_submit():
        round_ = Round(user_id=current_user.id, course_id=tee_set.course_id,
                        tee_set_id=tee_set.id, played_date=form.played_date.data,
                        notes=form.notes.data or None)
        round_.hole_scores = _hole_scores_from_form(form, tee_set)
        db.session.add(round_)
        db.session.flush()
        recalculate(round_)
        flash('Round saved.')
        return redirect(url_for('rounds.detail', round_id=round_.id))

    return render_template('rounds/scorecard.html', form=form, tee_set=tee_set)


@bp.route('/<int:round_id>')
@login_required
def detail(round_id):
    round_ = _get_owned_round_or_404(round_id)
    return render_template('rounds/detail.html', round=round_)


@bp.route('/<int:round_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(round_id):
    round_ = _get_owned_round_or_404(round_id)
    tee_set = round_.tee_set
    scores_by_hole = {hs.hole_id: hs for hs in round_.hole_scores}

    if request.method == 'GET':
        form = ScorecardForm(tee_set_id=tee_set.id, played_date=round_.played_date,
                              notes=round_.notes)
        for hole in tee_set.holes:
            hs = scores_by_hole.get(hole.id)
            form.holes.append_entry({
                'strokes': hs.strokes if hs else None,
                'putts': hs.putts if hs else None,
                'fairway_hit': bool(hs.fairway_hit) if hs else False,
                'gir': bool(hs.gir) if hs else False,
            })
    else:
        form = ScorecardForm()

    if form.validate_on_submit():
        round_.played_date = form.played_date.data
        round_.notes = form.notes.data or None
        # Replacing the collection in one step would insert the new rows
        # before deleting the old ones and collide on the (round_id,
        # hole_id) unique constraint, so clear it and flush first.
        round_.hole_scores = []
        db.session.flush()
        round_.hole_scores = _hole_scores_from_form(form, tee_set)
        db.session.flush()
        recalculate(round_)
        flash('Round updated.')
        return redirect(url_for('rounds.detail', round_id=round_.id))

    return render_template('rounds/scorecard.html', form=form, tee_set=tee_set, editing=True)


@bp.route('/<int:round_id>/delete', methods=['POST'])
@login_required
def delete(round_id):
    round_ = _get_owned_round_or_404(round_id)
    db.session.delete(round_)
    db.session.commit()
    flash('Round deleted.')
    return redirect(url_for('rounds.list_rounds'))


def _hole_scores_from_form(form, tee_set):
    return [
        HoleScore(hole_id=hole.id, strokes=entry.form.strokes.data,
                  putts=entry.form.putts.data,
                  fairway_hit=entry.form.fairway_hit.data,
                  gir=entry.form.gir.data)
        for hole, entry in zip(tee_set.holes, form.holes.entries)
    ]


def _get_owned_round_or_404(round_id):
    round_ = db.get_or_404(Round, round_id)
    if round_.user_id != current_user.id:
        abort(403)
    return round_
