from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Course(db.Model):
    __tablename__ = 'course'
    __table_args__ = (
        UniqueConstraint('external_source', 'external_id',
                          name='uq_course_external'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    club_name: Mapped[str] = mapped_column(db.String(128))
    course_name: Mapped[str] = mapped_column(db.String(128))
    address: Mapped[Optional[str]] = mapped_column(db.String(255))
    city: Mapped[Optional[str]] = mapped_column(db.String(64))
    state: Mapped[Optional[str]] = mapped_column(db.String(64))
    country: Mapped[Optional[str]] = mapped_column(db.String(64))
    scorecard_url: Mapped[Optional[str]] = mapped_column(db.String(255))
    external_source: Mapped[Optional[str]] = mapped_column(db.String(32))
    external_id: Mapped[Optional[str]] = mapped_column(db.String(8))
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc))

    tee_sets: Mapped[list['TeeSet']] = relationship(
        back_populates='course', cascade='all, delete-orphan',
        order_by='TeeSet.id')
    # No delete cascade here (unlike tee_sets above): a course with
    # recorded rounds against it must not be deletable -- see the guard
    # in app/courses/routes.py:delete().
    rounds: Mapped[list['Round']] = relationship(back_populates='course')

    @property
    def display_name(self):
        if self.club_name and self.course_name and self.club_name != self.course_name:
            return f'{self.club_name} — {self.course_name}'
        return self.course_name or self.club_name

    def __repr__(self):
        return f'<Course {self.display_name!r}>'


class TeeSet(db.Model):
    __tablename__ = 'tee_set'

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey('course.id'), index=True)
    name: Mapped[str] = mapped_column(db.String(64))
    color: Mapped[Optional[str]] = mapped_column(db.String(32))
    gender: Mapped[str] = mapped_column(db.String(1))
    par: Mapped[Optional[int]] = mapped_column()
    course_rating: Mapped[Optional[float]] = mapped_column(Numeric(3, 1))
    slope_rating: Mapped[Optional[int]] = mapped_column()
    yardage: Mapped[Optional[int]] = mapped_column()
    meters: Mapped[Optional[int]] = mapped_column()
    hole_count: Mapped[int] = mapped_column(default=18)

    course: Mapped['Course'] = relationship(back_populates='tee_sets')
    holes: Mapped[list['Hole']] = relationship(
        back_populates='tee_set', cascade='all, delete-orphan',
        order_by='Hole.number')

    def __repr__(self):
        return f'<TeeSet {self.name} ({self.gender})>'


class Hole(db.Model):
    __tablename__ = 'hole'
    __table_args__ = (
        UniqueConstraint('tee_set_id', 'number', name='uq_hole_tee_set_number'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tee_set_id: Mapped[int] = mapped_column(ForeignKey('tee_set.id'), index=True)
    number: Mapped[int] = mapped_column()
    par: Mapped[int] = mapped_column()
    stroke_index: Mapped[int] = mapped_column()
    yardage: Mapped[Optional[int]] = mapped_column()

    tee_set: Mapped['TeeSet'] = relationship(back_populates='holes')

    def __repr__(self):
        return f'<Hole {self.number} par {self.par}>'
