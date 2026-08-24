import threading
from datetime import date

import requests

from app.services.courses.base import (
    CourseDetail,
    CourseProvider,
    CourseProviderError,
    CourseProviderNotFound,
    CourseProviderQuotaExceeded,
    CourseProviderUnavailable,
    CourseSummary,
    HoleData,
    TeeSetData,
)


class DailyQuota:
    """Client-side best-effort limiter for the free tier's daily request cap.

    Counts reset at UTC midnight and live only in this process's memory --
    the API documents no rate-limit headers, so this cannot be exact across
    restarts or multiple workers. It exists to fail fast with a clear
    message before burning through the day's allotment, not to be the
    authoritative limiter (the API itself is that).
    """

    def __init__(self, limit):
        self.limit = limit
        self._lock = threading.Lock()
        self._day = None
        self._count = 0

    def consume(self):
        with self._lock:
            today = date.today()
            if today != self._day:
                self._day = today
                self._count = 0
            if self._count >= self.limit:
                raise CourseProviderQuotaExceeded(
                    f'Daily limit of {self.limit} course-API requests reached; '
                    'try again tomorrow or add the course manually.')
            self._count += 1


class GolfCourseApiProvider(CourseProvider):
    """Adapter for https://api.golfcourseapi.com (see openapi.yml).

    Free tier is read-only: only the GET endpoints used here (search,
    fetch-by-id, healthcheck) are available without a paid plan.
    """

    source_name = 'golfcourseapi'

    def __init__(self, api_key, base_url, daily_quota=50, session=None, quota=None):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.session = session or requests.Session()
        self.quota = quota or DailyQuota(daily_quota)

    def _headers(self):
        return {'Authorization': f'Bearer {self.api_key}'}

    def _get(self, path, params=None):
        self.quota.consume()
        response = self.session.get(
            f'{self.base_url}{path}', headers=self._headers(),
            params=params, timeout=10)
        if response.status_code == 429:
            raise CourseProviderQuotaExceeded(
                'The course API reported a rate limit; try again later.')
        if response.status_code in (401, 403):
            raise CourseProviderUnavailable(_error_message(response))
        if response.status_code == 404:
            raise CourseProviderNotFound(_error_message(response))
        if response.status_code >= 400:
            raise CourseProviderError(_error_message(response))
        return response.json()

    def search(self, query):
        payload = self._get('/v1/search', params={
            'search_query': query,
            'fuzzy_match': 'true',
        })
        return [_summary_from_payload(c) for c in payload.get('courses', [])]

    def fetch(self, external_id):
        payload = self._get(f'/v1/courses/{external_id.lower()}')
        return _detail_from_payload(payload)

    def health_check(self):
        response = self.session.get(f'{self.base_url}/v1/healthcheck', timeout=10)
        response.raise_for_status()
        return response.json()


def _error_message(response):
    try:
        body = response.json()
    except ValueError:
        return f'Course API request failed with status {response.status_code}.'
    error = body.get('error')
    if isinstance(error, dict):
        # 422 validation errors come back as {"error": {"field": "message"}}
        return '; '.join(f'{field}: {msg}' for field, msg in error.items())
    return error or f'Course API request failed with status {response.status_code}.'


def _summary_from_payload(payload):
    location = payload.get('location') or {}
    return CourseSummary(
        external_id=payload['id'].lower(),
        club_name=payload.get('club_name', ''),
        course_name=payload.get('course_name', ''),
        address=location.get('address'),
        city=location.get('city'),
        state=location.get('state'),
        country=location.get('country'),
    )


def _detail_from_payload(payload):
    # NOTE: GET /v1/courses/{id} returns the course at the top level, while
    # POST/PATCH wrap it as {"course": {...}}. This adapter only ever reads
    # (free tier is read-only), so it only needs the unwrapped shape.
    location = payload.get('location') or {}
    tees = payload.get('tees') or {}
    tee_sets = []
    for gender, code in (('male', 'M'), ('female', 'F')):
        for tee_box in tees.get(gender) or []:
            tee_sets.append(_tee_set_from_payload(tee_box, code))
    return CourseDetail(
        external_id=payload['id'].lower(),
        club_name=payload.get('club_name', ''),
        course_name=payload.get('course_name', ''),
        address=location.get('address'),
        city=location.get('city'),
        state=location.get('state'),
        country=location.get('country'),
        scorecard_url=payload.get('scorecard_url'),
        tee_sets=tuple(tee_sets),
    )


def _tee_set_from_payload(tee_box, gender_code):
    raw_holes = tee_box.get('holes') or []
    declared_count = tee_box.get('number_of_holes')
    if declared_count is not None and declared_count != len(raw_holes):
        raise CourseProviderError(
            f"Tee set {tee_box.get('tee_name')!r} declares {declared_count} "
            f'holes but the API returned {len(raw_holes)}; refusing to '
            'import an incomplete scorecard.')
    # Holes carry no hole number in this API -- number them by array
    # position, and never sort or dedupe the array.
    holes = tuple(
        HoleData(
            number=i + 1,
            par=hole['par'],
            stroke_index=hole['handicap'],
            yardage=hole.get('yardage'),
        )
        for i, hole in enumerate(raw_holes)
    )
    return TeeSetData(
        name=tee_box.get('tee_name', ''),
        gender=gender_code,
        par=tee_box.get('par_total'),
        course_rating=tee_box.get('course_rating'),
        slope_rating=tee_box.get('slope_rating'),
        yardage=tee_box.get('total_yards'),
        meters=tee_box.get('total_meters'),
        hole_count=declared_count if declared_count is not None else len(raw_holes),
        holes=holes,
    )
