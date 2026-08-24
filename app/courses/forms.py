from flask_wtf import FlaskForm
from wtforms import (DecimalField, FieldList, FormField, IntegerField,
                      SelectField, StringField, SubmitField)
from wtforms.validators import DataRequired, Length, NumberRange
from wtforms.validators import Optional as OptionalValidator
from wtforms.validators import ValidationError


class CourseForm(FlaskForm):
    club_name = StringField('Club name', validators=[DataRequired(), Length(max=128)])
    course_name = StringField('Course name', validators=[DataRequired(), Length(max=128)])
    address = StringField('Address', validators=[OptionalValidator(), Length(max=255)])
    city = StringField('City', validators=[OptionalValidator(), Length(max=64)])
    state = StringField('State', validators=[OptionalValidator(), Length(max=64)])
    country = StringField('Country', validators=[OptionalValidator(), Length(max=64)])
    scorecard_url = StringField('Scorecard URL', validators=[OptionalValidator(), Length(max=255)])
    submit = SubmitField('Save')


class HoleForm(FlaskForm):
    class Meta:
        csrf = False

    par = IntegerField('Par', validators=[DataRequired(), NumberRange(min=3, max=6)])
    stroke_index = IntegerField('Stroke Index', validators=[DataRequired(), NumberRange(min=1, max=18)])
    yardage = IntegerField('Yardage', validators=[OptionalValidator(), NumberRange(min=0)])


class TeeSetForm(FlaskForm):
    # Manual entry only supports 18-hole tee sets; 9-hole tee sets can only
    # arrive via API import (see app/services/courses/golfcourseapi.py).
    name = StringField('Tee name', validators=[DataRequired(), Length(max=64)])
    color = StringField('Color', validators=[OptionalValidator(), Length(max=32)])
    gender = SelectField('Gender', choices=[('M', 'Men'), ('F', 'Women')],
                          validators=[DataRequired()])
    course_rating = DecimalField('Course rating', places=1,
                                  validators=[DataRequired(), NumberRange(min=50, max=99.9)])
    slope_rating = IntegerField('Slope rating',
                                 validators=[DataRequired(), NumberRange(min=55, max=155)])
    yardage = IntegerField('Total yardage', validators=[OptionalValidator(), NumberRange(min=0)])
    meters = IntegerField('Total meters', validators=[OptionalValidator(), NumberRange(min=0)])
    holes = FieldList(FormField(HoleForm), min_entries=18, max_entries=18)
    submit = SubmitField('Save')

    def validate_holes(self, field):
        stroke_indexes = [entry.form.stroke_index.data for entry in field.entries]
        if sorted(i for i in stroke_indexes if i is not None) != list(range(1, len(stroke_indexes) + 1)):
            raise ValidationError(
                'Stroke indexes must be a permutation of 1..18 with no duplicates or gaps.')


class ImportSearchForm(FlaskForm):
    search_query = StringField('Search for a course', validators=[DataRequired()])
    submit = SubmitField('Search')


class ImportConfirmForm(FlaskForm):
    """CSRF-only form for the per-result "Import" button on the search page."""
    submit = SubmitField('Import')
