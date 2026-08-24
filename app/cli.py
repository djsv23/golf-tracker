import click


def register(app):
    @app.cli.command('seed-courses')
    def seed_courses():
        """Load data/courses.yml into the database."""
        from app.services.courses.seed import load_seed_courses
        courses = load_seed_courses()
        for course in courses:
            click.echo(f'  {course.display_name}')
        click.echo(f'Seeded {len(courses)} course(s).')

    @app.cli.command('import-course')
    @click.argument('external_id')
    def import_course(external_id):
        """Fetch a single course from the configured external provider by id and persist it."""
        from app.services.courses.base import CourseProviderError
        from app.services.courses.persist import persist_detail
        from app.services.courses.registry import (external_provider_configured,
                                                     get_course_provider)
        if not external_provider_configured():
            raise click.ClickException(
                'No external course API is configured (set GOLF_API_KEY).')
        provider = get_course_provider()
        try:
            detail = provider.fetch(external_id)
            course = persist_detail(detail, provider.source_name)
        except CourseProviderError as exc:
            raise click.ClickException(str(exc))
        click.echo(f'Imported {course.display_name} (id={course.id}).')

    @app.cli.command('check-course-api')
    def check_course_api():
        """Probe the external course API's healthcheck endpoint (no auth, no quota use)."""
        from app.services.courses.golfcourseapi import GolfCourseApiProvider
        from app.services.courses.registry import get_course_provider
        provider = get_course_provider()
        if not isinstance(provider, GolfCourseApiProvider):
            click.echo('No external course API is configured (set GOLF_API_KEY); '
                       'using local-only course search.')
            return
        result = provider.health_check()
        click.echo(result)

    @app.cli.command('recalc-handicaps')
    def recalc_handicaps():
        """Rebuild every round's adjusted score/differential and every user's
        handicap index from scratch, oldest round first.

        Needed after changing the handicap math, or to backfill rounds that
        were recorded before this calculation existed.
        """
        from app.models import Round, User
        from app.services.scoring import recalculate
        users = User.query.all()
        for user in users:
            rounds = (Round.query.filter_by(user_id=user.id)
                      .order_by(Round.played_date.asc(), Round.id.asc()).all())
            for round_ in rounds:
                recalculate(round_)
            click.echo(f'  {user.username}: {len(rounds)} round(s), '
                       f'index={user.hdcp_index}')
        click.echo(f'Recalculated {len(users)} user(s).')
