from datetime import date

from flask_wtf import FlaskForm
from wtforms import (BooleanField, DateField, FieldList, FormField,
                      HiddenField, IntegerField, SelectField, StringField,
                      SubmitField)
from wtforms.validators import DataRequired, Length, NumberRange
from wtforms.validators import Optional as OptionalValidator

from app.models.course import Course, TeeSet


class RoundSetupForm(FlaskForm):
    tee_set_id = SelectField('Tee', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Next: Enter Scores')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        tee_sets = (TeeSet.query.join(Course)
                    .order_by(Course.course_name, TeeSet.name).all())
        self.tee_set_id.choices = [
            (ts.id, f'{ts.course.display_name} — {ts.name} '
                     f'({"Men" if ts.gender == "M" else "Women"})')
            for ts in tee_sets
        ]


class CourseSearchForm(FlaskForm):
    # Field name intentionally not "submit" -- this form and RoundSetupForm
    # both post to rounds.new, and each needs its own submit-button name so
    # the route can tell which one fired.
    search_query = StringField('Search for a course', validators=[DataRequired()])
    search_submit = SubmitField('Search')


class HoleScoreEntryForm(FlaskForm):
    class Meta:
        csrf = False

    strokes = IntegerField('Strokes', validators=[DataRequired(), NumberRange(min=1, max=20)])
    putts = IntegerField('Putts', validators=[OptionalValidator(), NumberRange(min=0, max=10)])
    fairway_hit = BooleanField('Fairway')
    gir = BooleanField('GIR')


class ScorecardForm(FlaskForm):
    tee_set_id = HiddenField(validators=[DataRequired()])
    played_date = DateField('Date played', validators=[DataRequired()], default=date.today)
    notes = StringField('Notes', validators=[OptionalValidator(), Length(max=500)])
    holes = FieldList(FormField(HoleScoreEntryForm))
    submit = SubmitField('Save Round')
