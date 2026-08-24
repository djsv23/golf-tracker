from app.services.courses.persist import persist_detail
from app.services.courses.registry import get_course_provider


def import_course_by_external_id(external_id):
    """Fetch a course from the configured provider and persist it.

    Shared by the courses-management import flow, the round-setup import
    flow, and the `flask import-course` CLI command so they can't drift
    into different fetch/persist behavior.
    """
    provider = get_course_provider()
    return persist_detail(provider.fetch(external_id), provider.source_name)
