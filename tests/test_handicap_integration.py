"""End-to-end check that recording rounds through the real routes produces
the handicap numbers app/services/handicap.py's unit tests say they should.
Complements test_handicap.py's pure-function coverage by exercising the
actual wiring in app/services/scoring.py.
"""
from datetime import date

from app.extensions import db as _db
from app.models.course import Course, Hole, TeeSet
from app.models.round import Round
from tests.conftest import login


def _make_scratch_tee_set():
    # Rating == par and slope == 113 keeps the differential arithmetic to
    # (adjusted_gross - 72), so the expected numbers are easy to hand-check.
    course = Course(club_name='Scratch CC', course_name='Scratch CC')
    tee_set = TeeSet(course=course, name='Blue', gender='M',
                      course_rating=72.0, slope_rating=113, par=72, hole_count=18)
    tee_set.holes = [
        Hole(number=i + 1, par=4, stroke_index=i + 1, yardage=400)
        for i in range(18)
    ]
    _db.session.add(course)
    _db.session.commit()
    return tee_set


def _play_round(client, tee_set_id, played_date, strokes_per_hole):
    data = {'tee_set_id': str(tee_set_id), 'played_date': played_date, 'notes': ''}
    for i in range(18):
        data[f'holes-{i}-strokes'] = str(strokes_per_hole)
        data[f'holes-{i}-putts'] = '2'
    resp = client.post(f'/rounds/new/scorecard?tee_set_id={tee_set_id}', data=data,
                        follow_redirects=True)
    assert resp.status_code == 200
    assert b'Round saved' in resp.data


def test_index_is_none_until_third_round_then_follows_whs_table(client, auth_user, db):
    tee_set = _make_scratch_tee_set()
    login(client)

    # Round 1 (gross 90, all bogeys): differential = (113/113)*(90-72) =
    # 18.0. Fewer than 3 rounds -> no index yet.
    _play_round(client, tee_set.id, '2024-01-01', strokes_per_hole=5)
    rounds = Round.query.order_by(Round.played_date).all()
    assert len(rounds) == 1
    assert rounds[0].score_differential == 18.0
    assert auth_user.hdcp_index is None

    # Round 2: still fewer than 3 rounds.
    _play_round(client, tee_set.id, '2024-01-02', strokes_per_hole=5)
    assert auth_user.hdcp_index is None

    # Round 3: WHS table for N=3 is (use lowest 1, adjustment -2.0).
    # All three differentials are 18.0, so index = 18.0 - 2.0 = 16.0.
    _play_round(client, tee_set.id, '2024-01-03', strokes_per_hole=5)
    assert auth_user.hdcp_index is not None
    assert float(auth_user.hdcp_index) == 16.0

    # Round 4: WHS table for N=4 is (use lowest 1, adjustment -1.0).
    # Course handicap is now derived from the 16.0 index (course_handicap(
    # 16.0, 113, 72.0, 72) == 16), but every hole is scored well under its
    # net-double-bogey cap, so the differential is unaffected: still 18.0.
    # index = 18.0 - 1.0 = 17.0.
    _play_round(client, tee_set.id, '2024-01-04', strokes_per_hole=5)
    assert float(auth_user.hdcp_index) == 17.0


def test_blowup_hole_is_capped_end_to_end(client, auth_user, db):
    tee_set = _make_scratch_tee_set()
    login(client)

    # Establish an index first so course handicap isn't 0.
    for d in ('2024-01-01', '2024-01-02', '2024-01-03'):
        _play_round(client, tee_set.id, d, strokes_per_hole=5)
    index_before = float(auth_user.hdcp_index)
    assert index_before == 16.0
    # course_handicap(16.0, 113, 72.0, 72) == 16 -> every hole (stroke
    # index 1-18, remainder 16) gets at least 1 stroke; holes 17-18 get 0.
    # Net double bogey cap on hole 1 (stroke index 1): par 4 + 2 + 1 = 7.

    data = {'tee_set_id': str(tee_set.id), 'played_date': '2024-01-04', 'notes': ''}
    for i in range(18):
        data[f'holes-{i}-strokes'] = '4'
        data[f'holes-{i}-putts'] = '2'
    data['holes-0-strokes'] = '15'  # blow-up on hole 1 (stroke index 1, cap 7)
    resp = client.post(f'/rounds/new/scorecard?tee_set_id={tee_set.id}', data=data,
                        follow_redirects=True)
    assert resp.status_code == 200

    round_ = Round.query.filter_by(played_date=date(2024, 1, 4)).first()
    assert round_.gross_score == 17 * 4 + 15 == 83
    assert round_.adjusted_gross_score == 17 * 4 + 7 == 75
    assert round_.adjusted_gross_score < round_.gross_score
