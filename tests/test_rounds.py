from app.extensions import db as _db
from app.models.course import Course, Hole, TeeSet
from app.models.round import Round
from tests.conftest import login


def _make_tee_set(course_name='Test Course'):
    course = Course(club_name=course_name, course_name=course_name)
    tee_set = TeeSet(course=course, name='Blue', gender='M',
                      course_rating=72.0, slope_rating=125, par=72, hole_count=18)
    tee_set.holes = [
        Hole(number=i + 1, par=4, stroke_index=i + 1, yardage=400)
        for i in range(18)
    ]
    _db.session.add(course)
    _db.session.commit()
    return tee_set


def _scorecard_data(tee_set_id, played_date='2024-06-01', notes='', strokes=None):
    data = {
        'tee_set_id': str(tee_set_id),
        'played_date': played_date,
        'notes': notes,
    }
    for i in range(18):
        data[f'holes-{i}-strokes'] = str(strokes[i] if strokes else 4)
        data[f'holes-{i}-putts'] = '2'
    return data


def test_new_round_setup_lists_tee_sets(client, auth_user, db):
    tee_set = _make_tee_set()
    login(client)
    resp = client.get('/rounds/new')
    assert resp.status_code == 200
    assert tee_set.course.display_name.encode() in resp.data


def test_record_round_end_to_end(client, auth_user, db):
    tee_set = _make_tee_set()
    login(client)

    resp = client.post('/rounds/new', data={'tee_set_id': tee_set.id},
                        follow_redirects=True)
    assert resp.status_code == 200
    assert b'Enter Scores' in resp.data

    strokes = [4] * 17 + [7]  # one blown-up hole
    resp = client.post(f'/rounds/new/scorecard?tee_set_id={tee_set.id}',
                        data=_scorecard_data(tee_set.id, strokes=strokes),
                        follow_redirects=True)
    assert resp.status_code == 200
    assert b'Round saved' in resp.data

    round_ = Round.query.filter_by(user_id=auth_user.id).first()
    assert round_ is not None
    assert round_.gross_score == sum(strokes)
    assert len(round_.hole_scores) == 18
    assert round_.tee_set_id == tee_set.id
    assert round_.course_id == tee_set.course_id


def test_round_appears_on_homepage_and_profile(client, auth_user, db):
    tee_set = _make_tee_set()
    login(client)
    client.post(f'/rounds/new/scorecard?tee_set_id={tee_set.id}',
                data=_scorecard_data(tee_set.id))

    resp = client.get('/')
    assert b'>72<' in resp.data
    assert tee_set.course.display_name.encode() in resp.data

    resp = client.get(f'/user/{auth_user.username}')
    assert b'>72<' in resp.data


def test_edit_round_recalculates_gross(client, auth_user, db):
    tee_set = _make_tee_set()
    login(client)
    client.post(f'/rounds/new/scorecard?tee_set_id={tee_set.id}',
                data=_scorecard_data(tee_set.id))
    round_ = Round.query.filter_by(user_id=auth_user.id).first()
    assert round_.gross_score == 72

    new_strokes = [5] * 18
    resp = client.post(f'/rounds/{round_.id}/edit',
                        data=_scorecard_data(tee_set.id, strokes=new_strokes),
                        follow_redirects=True)
    assert resp.status_code == 200
    assert b'Round updated' in resp.data
    _db.session.refresh(round_)
    assert round_.gross_score == 90
    assert len(round_.hole_scores) == 18


def test_delete_round(client, auth_user, db):
    tee_set = _make_tee_set()
    login(client)
    client.post(f'/rounds/new/scorecard?tee_set_id={tee_set.id}',
                data=_scorecard_data(tee_set.id))
    round_ = Round.query.filter_by(user_id=auth_user.id).first()
    round_id = round_.id

    resp = client.post(f'/rounds/{round_id}/delete', follow_redirects=True)
    assert resp.status_code == 200
    assert _db.session.get(Round, round_id) is None


def test_round_ownership_enforced(client, make_user, db):
    tee_set = _make_tee_set()
    owner = make_user(username='owner', email='owner@example.com')
    other = make_user(username='other', email='other@example.com')

    login(client, username='owner')
    client.post(f'/rounds/new/scorecard?tee_set_id={tee_set.id}',
                data=_scorecard_data(tee_set.id))
    round_ = Round.query.filter_by(user_id=owner.id).first()
    client.get('/logout')

    login(client, username='other')
    resp = client.get(f'/rounds/{round_.id}')
    assert resp.status_code == 403
    resp = client.get(f'/rounds/{round_.id}/edit')
    assert resp.status_code == 403
    resp = client.post(f'/rounds/{round_.id}/delete')
    assert resp.status_code == 403


def test_rounds_list_scoped_to_current_user(client, make_user, db):
    tee_set = _make_tee_set()
    make_user(username='alice', email='alice@example.com')
    make_user(username='bob', email='bob@example.com')

    login(client, username='alice')
    client.post(f'/rounds/new/scorecard?tee_set_id={tee_set.id}',
                data=_scorecard_data(tee_set.id))
    client.get('/logout')

    login(client, username='bob')
    resp = client.get('/rounds/')
    assert b'No rounds recorded yet' in resp.data


def test_course_with_rounds_cannot_be_deleted(client, auth_user, db):
    tee_set = _make_tee_set()
    course_id = tee_set.course_id
    login(client)
    client.post(f'/rounds/new/scorecard?tee_set_id={tee_set.id}',
                data=_scorecard_data(tee_set.id))

    resp = client.post(f'/courses/{course_id}/delete', follow_redirects=True)
    assert resp.status_code == 200
    assert b'Cannot delete a course' in resp.data
    assert db.session.get(Course, course_id) is not None


def test_tee_set_with_rounds_cannot_be_deleted(client, auth_user, db):
    tee_set = _make_tee_set()
    course_id = tee_set.course_id
    tee_set_id = tee_set.id
    login(client)
    client.post(f'/rounds/new/scorecard?tee_set_id={tee_set.id}',
                data=_scorecard_data(tee_set.id))

    resp = client.post(f'/courses/{course_id}/tee_sets/{tee_set_id}/delete',
                        follow_redirects=True)
    assert resp.status_code == 200
    assert b'Cannot delete a tee set' in resp.data
    assert db.session.get(TeeSet, tee_set_id) is not None
