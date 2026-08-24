from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.courses import bp
from app.courses.forms import CourseForm, ImportConfirmForm, ImportSearchForm, TeeSetForm
from app.extensions import db
from app.models.course import Course, Hole, TeeSet
from app.services.courses.base import CourseProviderError
from app.services.courses.persist import persist_detail
from app.services.courses.registry import (external_provider_configured,
                                             get_course_provider)


@bp.route('/')
@login_required
def list_courses():
    courses = Course.query.order_by(Course.course_name).all()
    return render_template('courses/list.html', courses=courses,
                            import_enabled=external_provider_configured())


@bp.route('/<int:course_id>')
@login_required
def detail(course_id):
    course = db.get_or_404(Course, course_id)
    return render_template('courses/detail.html', course=course)


@bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    form = CourseForm()
    if form.validate_on_submit():
        course = Course()
        _apply_course_form(course, form)
        db.session.add(course)
        db.session.commit()
        flash('Course created. Add a tee set to record rounds on it.')
        return redirect(url_for('courses.detail', course_id=course.id))
    return render_template('courses/form.html', form=form, title='New Course')


@bp.route('/<int:course_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(course_id):
    course = db.get_or_404(Course, course_id)
    form = CourseForm(obj=course)
    if form.validate_on_submit():
        _apply_course_form(course, form)
        db.session.commit()
        flash('Course updated.')
        return redirect(url_for('courses.detail', course_id=course.id))
    return render_template('courses/form.html', form=form, title='Edit Course')


@bp.route('/<int:course_id>/delete', methods=['POST'])
@login_required
def delete(course_id):
    course = db.get_or_404(Course, course_id)
    db.session.delete(course)
    db.session.commit()
    flash('Course deleted.')
    return redirect(url_for('courses.list_courses'))


def _apply_course_form(course, form):
    course.club_name = form.club_name.data
    course.course_name = form.course_name.data
    course.address = form.address.data
    course.city = form.city.data
    course.state = form.state.data
    course.country = form.country.data
    course.scorecard_url = form.scorecard_url.data


@bp.route('/<int:course_id>/tee_sets/new', methods=['GET', 'POST'])
@login_required
def new_tee_set(course_id):
    course = db.get_or_404(Course, course_id)
    form = TeeSetForm()
    if form.validate_on_submit():
        tee_set = TeeSet(course=course)
        _apply_tee_set_form(tee_set, form)
        db.session.add(tee_set)
        db.session.commit()
        flash('Tee set added.')
        return redirect(url_for('courses.detail', course_id=course.id))
    return render_template('courses/tee_set_form.html', form=form, course=course,
                            title='New Tee Set')


@bp.route('/<int:course_id>/tee_sets/<int:tee_set_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_tee_set(course_id, tee_set_id):
    course = db.get_or_404(Course, course_id)
    tee_set = TeeSet.query.filter_by(id=tee_set_id, course_id=course.id).first_or_404()
    form = TeeSetForm(obj=tee_set) if request.method == 'GET' else TeeSetForm()
    if form.validate_on_submit():
        _apply_tee_set_form(tee_set, form)
        db.session.commit()
        flash('Tee set updated.')
        return redirect(url_for('courses.detail', course_id=course.id))
    return render_template('courses/tee_set_form.html', form=form, course=course,
                            title='Edit Tee Set')


@bp.route('/<int:course_id>/tee_sets/<int:tee_set_id>/delete', methods=['POST'])
@login_required
def delete_tee_set(course_id, tee_set_id):
    tee_set = TeeSet.query.filter_by(id=tee_set_id, course_id=course_id).first_or_404()
    db.session.delete(tee_set)
    db.session.commit()
    flash('Tee set deleted.')
    return redirect(url_for('courses.detail', course_id=course_id))


def _apply_tee_set_form(tee_set, form):
    tee_set.name = form.name.data
    tee_set.color = form.color.data
    tee_set.gender = form.gender.data
    tee_set.course_rating = form.course_rating.data
    tee_set.slope_rating = form.slope_rating.data
    tee_set.yardage = form.yardage.data
    tee_set.meters = form.meters.data
    tee_set.hole_count = len(form.holes.entries)
    tee_set.par = sum(entry.form.par.data for entry in form.holes.entries)
    tee_set.holes = [
        Hole(number=i + 1, par=entry.form.par.data,
             stroke_index=entry.form.stroke_index.data,
             yardage=entry.form.yardage.data)
        for i, entry in enumerate(form.holes.entries)
    ]


@bp.route('/import', methods=['GET', 'POST'])
@login_required
def import_search():
    if not external_provider_configured():
        abort(404)
    form = ImportSearchForm()
    results = None
    if form.validate_on_submit():
        provider = get_course_provider()
        try:
            results = provider.search(form.search_query.data)
        except CourseProviderError as exc:
            flash(str(exc))
            results = []
    return render_template('courses/import.html', form=form, results=results,
                            import_form=ImportConfirmForm())


@bp.route('/import/<external_id>', methods=['POST'])
@login_required
def import_course(external_id):
    if not external_provider_configured():
        abort(404)
    provider = get_course_provider()
    try:
        course_detail = provider.fetch(external_id)
        course = persist_detail(course_detail, provider.source_name)
    except CourseProviderError as exc:
        flash(str(exc))
        return redirect(url_for('courses.import_search'))
    flash(f'Imported {course.display_name}.')
    return redirect(url_for('courses.detail', course_id=course.id))
