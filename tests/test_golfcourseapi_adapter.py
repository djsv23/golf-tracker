import datetime as dt
import json
from pathlib import Path

import pytest
import responses

from app.services.courses.base import (
    CourseProviderError,
    CourseProviderNotFound,
    CourseProviderQuotaExceeded,
    CourseProviderUnavailable,
)
from app.services.courses.golfcourseapi import DailyQuota, GolfCourseApiProvider

FIXTURES = Path(__file__).parent / 'fixtures' / 'golfcourseapi'
BASE_URL = 'https://api.golfcourseapi.com'


def load_fixture(name):
    with open(FIXTURES / name) as f:
        return json.load(f)


def make_provider(daily_quota=50):
    return GolfCourseApiProvider(api_key='test-key', base_url=BASE_URL,
                                  daily_quota=daily_quota)


@responses.activate
def test_search_unwraps_courses_envelope():
    responses.add(responses.GET, f'{BASE_URL}/v1/search',
                   json=load_fixture('search_response.json'), status=200)
    results = make_provider().search('lubbock')
    assert len(results) == 1
    assert results[0].external_id == '7k2m9qb4'
    assert results[0].club_name == 'Lubbock Country Club'
    assert results[0].city == 'Murray'


@responses.activate
def test_search_sends_bearer_auth_header():
    responses.add(responses.GET, f'{BASE_URL}/v1/search',
                   json=load_fixture('search_response.json'), status=200)
    make_provider().search('lubbock')
    assert responses.calls[0].request.headers['Authorization'] == 'Bearer test-key'


@responses.activate
def test_fetch_reads_bare_course_object_not_wrapped():
    responses.add(responses.GET, f'{BASE_URL}/v1/courses/7k2m9qb4',
                   json=load_fixture('course_full.json'), status=200)
    detail = make_provider().fetch('7k2m9qb4')
    assert detail.club_name == 'Murray Golf Club'
    assert detail.course_name == 'Course No. 1'
    assert detail.scorecard_url == 'https://example.com/scorecards/course-no-1.pdf'
    assert len(detail.tee_sets) == 2


@responses.activate
def test_fetch_numbers_holes_positionally():
    responses.add(responses.GET, f'{BASE_URL}/v1/courses/7k2m9qb4',
                   json=load_fixture('course_full.json'), status=200)
    detail = make_provider().fetch('7k2m9qb4')
    male_tee = next(ts for ts in detail.tee_sets if ts.gender == 'M')
    assert [h.number for h in male_tee.holes] == list(range(1, 19))
    assert male_tee.holes[0].par == 4
    assert male_tee.holes[0].stroke_index == 7
    assert male_tee.holes[1].stroke_index == 1


@responses.activate
def test_fetch_lowercases_id_in_request_and_result():
    responses.add(responses.GET, f'{BASE_URL}/v1/courses/7k2m9qb4',
                   json=load_fixture('course_full.json'), status=200)
    detail = make_provider().fetch('7K2M9QB4')
    assert responses.calls[0].request.url.endswith('/v1/courses/7k2m9qb4')
    assert detail.external_id == '7k2m9qb4'


@responses.activate
def test_fetch_rejects_mismatched_hole_count():
    responses.add(responses.GET, f'{BASE_URL}/v1/courses/abcdefgh',
                   json=load_fixture('course_mismatched_holes.json'), status=200)
    with pytest.raises(CourseProviderError, match='declares 18 holes but the API returned 9'):
        make_provider().fetch('abcdefgh')


@responses.activate
def test_fetch_404_raises_not_found():
    responses.add(responses.GET, f'{BASE_URL}/v1/courses/zzzzzzzz',
                   json=load_fixture('error_404.json'), status=404)
    with pytest.raises(CourseProviderNotFound, match='could not be found'):
        make_provider().fetch('zzzzzzzz')


@responses.activate
def test_search_401_raises_unavailable():
    responses.add(responses.GET, f'{BASE_URL}/v1/search',
                   json=load_fixture('error_401.json'), status=401)
    with pytest.raises(CourseProviderUnavailable, match='API key is missing'):
        make_provider().search('x')


@responses.activate
def test_search_403_raises_unavailable():
    responses.add(responses.GET, f'{BASE_URL}/v1/search',
                   json=load_fixture('error_403.json'), status=403)
    with pytest.raises(CourseProviderUnavailable, match="doesn't have the necessary permissions"):
        make_provider().search('x')


@responses.activate
def test_422_error_body_is_dict_shaped_not_string():
    responses.add(responses.GET, f'{BASE_URL}/v1/search',
                   json=load_fixture('error_422.json'), status=422)
    with pytest.raises(CourseProviderError) as exc_info:
        make_provider().search('x')
    message = str(exc_info.value)
    assert 'club_name: must be provided' in message
    assert 'tees: must include at least one tee box' in message


@responses.activate
def test_undocumented_429_raises_quota_exceeded():
    responses.add(responses.GET, f'{BASE_URL}/v1/search', json={}, status=429)
    with pytest.raises(CourseProviderQuotaExceeded):
        make_provider().search('x')


@responses.activate
def test_daily_quota_blocks_before_network_call():
    responses.add(responses.GET, f'{BASE_URL}/v1/search',
                   json=load_fixture('search_response.json'), status=200)
    provider = make_provider(daily_quota=1)
    provider.search('first call uses up the quota')
    with pytest.raises(CourseProviderQuotaExceeded):
        provider.search('second call should be blocked client-side')
    assert len(responses.calls) == 1


def test_daily_quota_resets_on_new_day(monkeypatch):
    quota = DailyQuota(limit=1)
    quota.consume()
    with pytest.raises(CourseProviderQuotaExceeded):
        quota.consume()

    tomorrow = dt.date.today() + dt.timedelta(days=1)

    class FakeDate(dt.date):
        @classmethod
        def today(cls):
            return tomorrow

    monkeypatch.setattr('app.services.courses.golfcourseapi.date', FakeDate)
    quota.consume()  # does not raise -- new day resets the counter
