from app.models.course import Course
from app.services.courses.local import LocalCourseProvider
from app.services.courses.seed import load_seed_courses
from tests.conftest import login


def test_seed_courses_creates_expected_courses(app, db):
    courses = load_seed_courses()
    assert len(courses) == 3
    names = {c.course_name for c in courses}
    assert 'Pinehurst No. 2' in names

    pinehurst = Course.query.filter_by(course_name='Pinehurst No. 2').first()
    assert len(pinehurst.tee_sets) == 2
    black = next(ts for ts in pinehurst.tee_sets if ts.name == 'Black')
    assert len(black.holes) == 18
    assert sum(h.par for h in black.holes) == 72
    assert sorted(h.stroke_index for h in black.holes) == list(range(1, 19))


def test_seed_courses_is_idempotent(app, db):
    load_seed_courses()
    first_count = Course.query.count()
    load_seed_courses()
    assert Course.query.count() == first_count


def test_local_provider_search_and_fetch(app, db):
    load_seed_courses()
    provider = LocalCourseProvider()
    results = provider.search('Pinehurst')
    assert len(results) == 1
    detail = provider.fetch(results[0].external_id)
    assert detail.course_name == 'Pinehurst No. 2'
    assert len(detail.tee_sets) == 2


def test_courses_list_requires_login(client):
    resp = client.get('/courses/', follow_redirects=True)
    assert b'Sign In' in resp.data


def test_courses_list_shows_seeded_courses(client, auth_user, db):
    load_seed_courses()
    login(client)
    resp = client.get('/courses/')
    assert b'Pinehurst' in resp.data
    assert b'Pebble Beach' in resp.data


def test_create_course_manually(client, auth_user, db):
    login(client)
    resp = client.post('/courses/new', data={
        'club_name': 'Test Club',
        'course_name': 'Test Course',
        'address': '',
        'city': 'Testville',
        'state': 'TX',
        'country': 'USA',
        'scorecard_url': '',
    }, follow_redirects=True)
    assert resp.status_code == 200
    course = Course.query.filter_by(course_name='Test Course').first()
    assert course is not None
    assert course.city == 'Testville'


def _tee_set_form_data():
    data = {
        'name': 'Blue',
        'color': 'blue',
        'gender': 'M',
        'course_rating': '72.5',
        'slope_rating': '128',
        'yardage': '6800',
        'meters': '',
    }
    for i in range(18):
        data[f'holes-{i}-par'] = '4'
        data[f'holes-{i}-stroke_index'] = str(i + 1)
        data[f'holes-{i}-yardage'] = '400'
    return data


def _make_course(client):
    client.post('/courses/new', data={
        'club_name': 'Test Club', 'course_name': 'Test Course',
        'address': '', 'city': '', 'state': '', 'country': '', 'scorecard_url': '',
    })
    return Course.query.filter_by(course_name='Test Course').first()


def test_add_tee_set_to_course(client, auth_user, db):
    login(client)
    course = _make_course(client)

    resp = client.post(f'/courses/{course.id}/tee_sets/new',
                        data=_tee_set_form_data(), follow_redirects=True)
    assert resp.status_code == 200
    assert len(course.tee_sets) == 1
    tee_set = course.tee_sets[0]
    assert len(tee_set.holes) == 18
    assert tee_set.par == 72
    assert sorted(h.stroke_index for h in tee_set.holes) == list(range(1, 19))


def test_add_tee_set_rejects_duplicate_stroke_indexes(client, auth_user, db):
    login(client)
    course = _make_course(client)

    data = _tee_set_form_data()
    data['holes-1-stroke_index'] = '1'  # duplicate of holes-0
    resp = client.post(f'/courses/{course.id}/tee_sets/new', data=data)
    assert b'permutation of 1..18' in resp.data
    assert len(course.tee_sets) == 0


def test_edit_tee_set_prefills_existing_holes(client, auth_user, db):
    login(client)
    course = _make_course(client)
    client.post(f'/courses/{course.id}/tee_sets/new', data=_tee_set_form_data())
    tee_set = course.tee_sets[0]

    resp = client.get(f'/courses/{course.id}/tee_sets/{tee_set.id}/edit')
    assert resp.status_code == 200
    assert b'value="4"' in resp.data  # par prefilled


def test_delete_course_cascades_tee_sets(client, auth_user, db):
    login(client)
    course = _make_course(client)
    client.post(f'/courses/{course.id}/tee_sets/new', data=_tee_set_form_data())
    course_id = course.id

    resp = client.post(f'/courses/{course_id}/delete', follow_redirects=True)
    assert resp.status_code == 200
    assert db.session.get(Course, course_id) is None


def test_import_disabled_without_api_key(client, auth_user, db):
    login(client)
    resp = client.get('/courses/import')
    assert resp.status_code == 404
