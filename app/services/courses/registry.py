from flask import current_app

from app.services.courses.golfcourseapi import GolfCourseApiProvider
from app.services.courses.local import LocalCourseProvider


def init_course_provider(app):
    """Build the one course-data provider this process will use, once.

    A single instance is stashed on the app so GolfCourseApiProvider's
    DailyQuota counter actually persists across requests -- constructing a
    fresh provider per request would reset the quota every time.
    """
    api_key = app.config.get('GOLF_API_KEY')
    if api_key:
        provider = GolfCourseApiProvider(
            api_key=api_key,
            base_url=app.config['GOLF_API_BASE_URL'],
            daily_quota=app.config['GOLF_API_DAILY_QUOTA'],
        )
    else:
        provider = LocalCourseProvider()
    app.extensions['course_provider'] = provider


def get_course_provider():
    return current_app.extensions['course_provider']


def external_provider_configured():
    return isinstance(get_course_provider(), GolfCourseApiProvider)
