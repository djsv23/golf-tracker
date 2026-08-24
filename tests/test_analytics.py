from datetime import date

from app.extensions import db as _db
from app.models.course import Course, Hole, TeeSet
from app.services.analytics import (best_worst_rounds,
                                     fairway_and_gir_percentage,
                                     gross_score_distribution,
                                     putts_per_round, scoring_average_by_par,
                                     scoring_trend)
from tests.conftest import login


def _make_tee_set():
    course = Course(club_name='Analytics CC', course_name='Analytics CC')
    tee_set = TeeSet(course=course, name='Blue', gender='M',
                      course_rating=72.0, slope_rating=113, par=72, hole_count=18)
    # 4 par-3s, 10 par-4s, 4 par-5s (par 72), matching the seed data pattern.
    pars = [4, 5, 4, 3, 4, 4, 3, 5, 4, 4, 3, 4, 5, 4, 3, 4, 5, 4]
    tee_set.holes = [
        Hole(number=i + 1, par=pars[i], stroke_index=i + 1, yardage=400)
        for i in range(18)
    ]
    _db.session.add(course)
    _db.session.commit()
    return tee_set


def _play_round(client, tee_set_id, played_date, strokes=4, putts=2,
                 fairway=None, gir=None):
    data = {'tee_set_id': str(tee_set_id), 'played_date': played_date, 'notes': ''}
    for i in range(18):
        data[f'holes-{i}-strokes'] = str(strokes)
        if putts is not None:
            data[f'holes-{i}-putts'] = str(putts)
        if fairway:
            data[f'holes-{i}-fairway_hit'] = 'y'
        if gir:
            data[f'holes-{i}-gir'] = 'y'
    client.post(f'/rounds/new/scorecard?tee_set_id={tee_set_id}', data=data)


def test_empty_dashboard_has_no_rounds(client, auth_user, db):
    login(client)
    resp = client.get('/dashboard/')
    assert resp.status_code == 200
    assert b'No rounds recorded yet' in resp.data


def test_dashboard_data_json_empty(client, auth_user, db):
    login(client)
    resp = client.get('/dashboard/data.json')
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload['round_count'] == 0
    assert payload['scoring_trend'] == []
    assert payload['gross_score_distribution'] == {}
    assert payload['putts_per_round'] is None
    assert payload['fairway_pct'] is None
    assert payload['gir_pct'] is None
    assert payload['best'] is None
    assert payload['worst'] is None


def test_scoring_trend_excludes_rounds_without_differential(app, db, make_user):
    user = make_user()
    tee_set = _make_tee_set()
    from app.models.round import HoleScore, Round
    # A round with no course rating/slope tee set -> no differential.
    bare_course = Course(club_name='Bare', course_name='Bare')
    bare_tee = TeeSet(course=bare_course, name='Blue', gender='M', par=72, hole_count=18)
    bare_tee.holes = [Hole(number=i + 1, par=4, stroke_index=i + 1) for i in range(18)]
    _db.session.add(bare_course)
    _db.session.commit()

    r1 = Round(user_id=user.id, course_id=tee_set.course_id, tee_set_id=tee_set.id,
               played_date=date(2024, 1, 1), gross_score=90, score_differential=18.0)
    r2 = Round(user_id=user.id, course_id=bare_tee.course_id, tee_set_id=bare_tee.id,
               played_date=date(2024, 1, 2), gross_score=95, score_differential=None)
    _db.session.add_all([r1, r2])
    _db.session.commit()

    trend = scoring_trend([r1, r2])
    assert len(trend) == 1
    assert trend[0]['differential'] == 18.0


def test_gross_score_distribution_counts_by_score(client, auth_user, db):
    tee_set = _make_tee_set()
    login(client)
    _play_round(client, tee_set.id, '2024-01-01', strokes=4)  # gross 72
    _play_round(client, tee_set.id, '2024-01-02', strokes=4)  # gross 72
    _play_round(client, tee_set.id, '2024-01-03', strokes=5)  # gross 90

    resp = client.get('/dashboard/data.json')
    dist = resp.get_json()['gross_score_distribution']
    assert dist == {'72': 2, '90': 1}


def test_scoring_average_by_par(client, auth_user, db):
    tee_set = _make_tee_set()
    login(client)
    _play_round(client, tee_set.id, '2024-01-01', strokes=4)

    from app.models.round import Round
    rounds = Round.query.all()
    avg = scoring_average_by_par(rounds)
    # Every hole was scored 4 regardless of its par, so each par bucket's
    # average is exactly 4.0.
    assert avg == {3: 4.0, 4: 4.0, 5: 4.0}


def test_putts_per_round_requires_putts_on_every_hole(app, db, make_user):
    user = make_user()
    tee_set = _make_tee_set()
    from app.models.round import HoleScore, Round
    complete = Round(user_id=user.id, course_id=tee_set.course_id,
                      tee_set_id=tee_set.id, played_date=date(2024, 1, 1))
    complete.hole_scores = [
        HoleScore(hole_id=h.id, strokes=4, putts=2) for h in tee_set.holes
    ]
    incomplete = Round(user_id=user.id, course_id=tee_set.course_id,
                        tee_set_id=tee_set.id, played_date=date(2024, 1, 2))
    incomplete.hole_scores = [
        HoleScore(hole_id=h.id, strokes=4, putts=(2 if i > 0 else None))
        for i, h in enumerate(tee_set.holes)
    ]
    _db.session.add_all([complete, incomplete])
    _db.session.commit()

    result = putts_per_round([complete, incomplete])
    assert result == 36  # only the complete round counts: 18 holes x 2 putts


def test_fairway_and_gir_percentage_excludes_par3_from_fairway(app, db, make_user):
    user = make_user()
    tee_set = _make_tee_set()  # 4 par-3s, 14 non-par-3s
    from app.models.round import HoleScore, Round
    round_ = Round(user_id=user.id, course_id=tee_set.course_id,
                    tee_set_id=tee_set.id, played_date=date(2024, 1, 1))
    round_.hole_scores = [
        HoleScore(hole_id=h.id, strokes=4, fairway_hit=True, gir=True)
        for h in tee_set.holes
    ]
    _db.session.add(round_)
    _db.session.commit()

    result = fairway_and_gir_percentage([round_])
    assert result['fairway_pct'] == 100.0  # all 14 eligible (non-par-3) holes hit
    assert result['gir_pct'] == 100.0  # all 18 holes count toward GIR


def test_best_worst_rounds(app, db, make_user):
    user = make_user()
    tee_set = _make_tee_set()
    from app.models.round import Round
    r1 = Round(user_id=user.id, course_id=tee_set.course_id, tee_set_id=tee_set.id,
               played_date=date(2024, 1, 1), gross_score=95)
    r2 = Round(user_id=user.id, course_id=tee_set.course_id, tee_set_id=tee_set.id,
               played_date=date(2024, 1, 2), gross_score=80)
    _db.session.add_all([r1, r2])
    _db.session.commit()

    result = best_worst_rounds([r1, r2])
    assert result['best']['gross_score'] == 80
    assert result['worst']['gross_score'] == 95


def test_dashboard_shows_charts_when_rounds_exist(client, auth_user, db):
    tee_set = _make_tee_set()
    login(client)
    _play_round(client, tee_set.id, '2024-01-01', strokes=4)

    resp = client.get('/dashboard/')
    assert resp.status_code == 200
    assert b'trend-chart' in resp.data
    assert b'distribution-chart' in resp.data
    assert b'chart.umd.min.js' in resp.data
