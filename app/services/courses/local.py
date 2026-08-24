from app.extensions import db
from app.models.course import Course
from app.services.courses.base import (
    CourseDetail,
    CourseProvider,
    CourseProviderNotFound,
    CourseSummary,
    HoleData,
    TeeSetData,
)


class LocalCourseProvider(CourseProvider):
    """Searches courses already stored in this app's own database.

    This is the default provider, used whenever no external API key is
    configured, and it is the only provider the test suite exercises --
    it never makes a network call.
    """

    source_name = 'local'

    def search(self, query):
        like = f'%{query}%'
        courses = (
            Course.query
            .filter(db.or_(Course.course_name.ilike(like),
                            Course.club_name.ilike(like)))
            .order_by(Course.course_name)
            .limit(20)
            .all()
        )
        return [_to_summary(c) for c in courses]

    def fetch(self, external_id):
        course = db.session.get(Course, int(external_id))
        if course is None:
            raise CourseProviderNotFound(external_id)
        return _to_detail(course)


def _to_summary(course):
    return CourseSummary(
        external_id=str(course.id),
        club_name=course.club_name,
        course_name=course.course_name,
        address=course.address,
        city=course.city,
        state=course.state,
        country=course.country,
    )


def _to_detail(course):
    return CourseDetail(
        external_id=str(course.id),
        club_name=course.club_name,
        course_name=course.course_name,
        address=course.address,
        city=course.city,
        state=course.state,
        country=course.country,
        scorecard_url=course.scorecard_url,
        tee_sets=tuple(_to_tee_set_data(ts) for ts in course.tee_sets),
    )


def _to_tee_set_data(tee_set):
    return TeeSetData(
        name=tee_set.name,
        gender=tee_set.gender,
        par=tee_set.par,
        course_rating=(float(tee_set.course_rating)
                        if tee_set.course_rating is not None else None),
        slope_rating=tee_set.slope_rating,
        yardage=tee_set.yardage,
        meters=tee_set.meters,
        hole_count=tee_set.hole_count,
        holes=tuple(
            HoleData(number=h.number, par=h.par,
                     stroke_index=h.stroke_index, yardage=h.yardage)
            for h in tee_set.holes
        ),
    )
