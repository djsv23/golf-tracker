import json
from pathlib import Path

import responses

from app.services.courses.registry import init_course_provider
from tests.conftest import GOLF_API_TEST_BASE_URL as BASE_URL

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


def test_import_link_visible_when_api_configured(api_client, api_app):
    _register_and_login(api_client)
    resp = api_client.get('/courses/')
    assert b'Import from API' in resp.data


@responses.activate
def test_import_search_and_import_course_end_to_end(api_client, api_app):
    responses.add(responses.GET, f'{BASE_URL}/v1/search',
                   json=load_fixture('search_response.json'), status=200)
    responses.add(responses.GET, f'{BASE_URL}/v1/courses/7k2m9qb4',
                   json=load_fixture('course_full.json'), status=200)
    _register_and_login(api_client)

    resp = api_client.post('/courses/import', data={'search_query': 'lubbock'})
    assert resp.status_code == 200
    assert b'Lubbock Country Club' in resp.data

    resp = api_client.post('/courses/import/7k2m9qb4', follow_redirects=True)
    assert resp.status_code == 200
    assert b'Imported' in resp.data

    from app.models.course import Course
    with api_app.app_context():
        course = Course.query.filter_by(external_source='golfcourseapi').first()
        assert course is not None
        assert course.course_name == 'Course No. 1'
        assert len(course.tee_sets) == 2


@responses.activate
def test_import_quota_exceeded_shows_flash_not_traceback(api_client, api_app):
    api_app.config['GOLF_API_DAILY_QUOTA'] = 1
    init_course_provider(api_app)
    responses.add(responses.GET, f'{BASE_URL}/v1/search',
                   json=load_fixture('search_response.json'), status=200)
    _register_and_login(api_client)

    api_client.post('/courses/import', data={'search_query': 'first'})
    resp = api_client.post('/courses/import', data={'search_query': 'second'},
                            follow_redirects=True)
    assert resp.status_code == 200
    assert b'Daily limit' in resp.data
