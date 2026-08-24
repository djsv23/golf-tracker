from app.extensions import db
from app.models.course import Course, Hole, TeeSet


def persist_detail(detail, external_source):
    """Create or update a Course (+ tee sets + holes) from a CourseDetail DTO.

    Idempotent on (external_source, external_id): re-importing the same
    course replaces its tee sets and holes rather than duplicating them.
    Shared by both the seed loader and the "import from API" flow so they
    can't drift into different persistence behavior.
    """
    course = Course.query.filter_by(
        external_source=external_source, external_id=detail.external_id
    ).first()
    if course is None:
        course = Course(external_source=external_source,
                         external_id=detail.external_id)
        db.session.add(course)

    course.club_name = detail.club_name
    course.course_name = detail.course_name
    course.address = detail.address
    course.city = detail.city
    course.state = detail.state
    course.country = detail.country
    course.scorecard_url = detail.scorecard_url
    course.tee_sets = [_build_tee_set(ts) for ts in detail.tee_sets]

    db.session.commit()
    return course


def _build_tee_set(tee_set_data):
    tee_set = TeeSet(
        name=tee_set_data.name,
        gender=tee_set_data.gender,
        par=tee_set_data.par,
        course_rating=tee_set_data.course_rating,
        slope_rating=tee_set_data.slope_rating,
        yardage=tee_set_data.yardage,
        meters=tee_set_data.meters,
        hole_count=tee_set_data.hole_count,
    )
    tee_set.holes = [
        Hole(number=h.number, par=h.par, stroke_index=h.stroke_index,
             yardage=h.yardage)
        for h in tee_set_data.holes
    ]
    return tee_set
