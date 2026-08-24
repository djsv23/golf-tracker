import json
from pathlib import Path

import responses

from app.models.course import Course
from tests.conftest import GOLF_API_TEST_BASE_URL as BASE_URL
from tests.conftest import login

FIXTURES = Path(__file__).parent / 'fixtures' / 'golfcourseapi'


def load_fixture(name):
    with open(FIXTURES / name) as f:
        return json.load(f)


def _register_and_login(client):
    client.post('/register', data={
        'username': 'dan', 'email': 'dan@example.com',
        'password': 'password123', 'password2': 'password123',
    })
    client.post('/login', data={'username': 'dan', 'password': 'password123'})


def test_search_panel_hidden_without_api_key(client, auth_user):
    login(client)
    resp = client.get('/rounds/new')
    assert resp.status_code == 200
    assert b'Search for a course' not in resp.data


def test_search_panel_shown_with_api_key(api_client):
    _register_and_login(api_client)
    resp = api_client.get('/rounds/new')
    assert resp.status_code == 200
    assert b'Search for a course' in resp.data


@responses.activate
def test_search_renders_results(api_client):
    responses.add(responses.GET, f'{BASE_URL}/v1/search',
                   json=load_fixture('search_response.json'), status=200)
    _register_and_login(api_client)

    resp = api_client.post('/rounds/new', data={
        'search_query': 'lubbock', 'search_submit': 'Search',
    })
    assert resp.status_code == 200
    assert b'Lubbock Country Club' in resp.data


@responses.activate
def test_import_persists_course_and_preselects_tee_set(api_client, api_app):
    responses.add(responses.GET, f'{BASE_URL}/v1/courses/7k2m9qb4',
                   json=load_fixture('course_full.json'), status=200)
    _register_and_login(api_client)

    resp = api_client.post('/rounds/new/import/7k2m9qb4', follow_redirects=True)
    assert resp.status_code == 200
    assert b'Imported' in resp.data

    with api_app.app_context():
        course = Course.query.filter_by(external_source='golfcourseapi').first()
        assert course is not None
        assert len(course.tee_sets) == 2
        tee_set_id = course.tee_sets[0].id

    assert f'selected value="{tee_set_id}"'.encode() in resp.data


def test_import_disabled_without_api_key(client, auth_user):
    login(client)
    resp = client.post('/rounds/new/import/7k2m9qb4')
    assert resp.status_code == 404


@responses.activate
def test_search_quota_exceeded_shows_flash_not_traceback(api_client, api_app):
    api_app.config['GOLF_API_DAILY_QUOTA'] = 1
    from app.services.courses.registry import init_course_provider
    init_course_provider(api_app)
    responses.add(responses.GET, f'{BASE_URL}/v1/search',
                   json=load_fixture('search_response.json'), status=200)
    _register_and_login(api_client)

    api_client.post('/rounds/new', data={'search_query': 'first', 'search_submit': 'Search'})
    resp = api_client.post('/rounds/new', data={'search_query': 'second', 'search_submit': 'Search'},
                            follow_redirects=True)
    assert resp.status_code == 200
    assert b'Daily limit' in resp.data


def test_round_setup_submit_unaffected_by_search_form(api_client):
    from tests.test_rounds import _make_tee_set
    _register_and_login(api_client)
    tee_set = _make_tee_set()

    resp = api_client.post('/rounds/new', data={'tee_set_id': tee_set.id},
                            follow_redirects=True)
    assert resp.status_code == 200
    assert b'Enter Scores' in resp.data
