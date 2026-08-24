from pathlib import Path

import yaml

from app.services.courses.base import CourseDetail, HoleData, TeeSetData
from app.services.courses.persist import persist_detail

SEED_SOURCE = 'seed'
DEFAULT_SEED_FILE = Path(__file__).resolve().parents[3] / 'data' / 'courses.yml'


def load_seed_courses(path=None):
    """Load data/courses.yml (or `path`) and persist each course.

    The YAML is written in the same CourseDetail/TeeSetData/HoleData shape
    the golfcourseapi adapter produces, so this shares persist_detail()
    with the API import flow rather than having its own write path.
    """
    path = path or DEFAULT_SEED_FILE
    with open(path) as f:
        raw_courses = yaml.safe_load(f) or []

    courses = []
    for raw in raw_courses:
        detail = _detail_from_dict(raw)
        courses.append(persist_detail(detail, SEED_SOURCE))
    return courses


def _detail_from_dict(raw):
    return CourseDetail(
        external_id=raw['external_id'],
        club_name=raw['club_name'],
        course_name=raw['course_name'],
        address=raw.get('address'),
        city=raw.get('city'),
        state=raw.get('state'),
        country=raw.get('country'),
        scorecard_url=raw.get('scorecard_url'),
        tee_sets=tuple(_tee_set_from_dict(ts) for ts in raw.get('tee_sets', [])),
    )


def _tee_set_from_dict(raw):
    holes = tuple(
        HoleData(number=i + 1, par=h['par'], stroke_index=h['stroke_index'],
                  yardage=h.get('yardage'))
        for i, h in enumerate(raw.get('holes', []))
    )
    return TeeSetData(
        name=raw['name'],
        gender=raw['gender'],
        par=raw.get('par') or sum(h.par for h in holes),
        course_rating=raw.get('course_rating'),
        slope_rating=raw.get('slope_rating'),
        yardage=raw.get('yardage'),
        meters=raw.get('meters'),
        hole_count=len(holes),
        holes=holes,
    )
