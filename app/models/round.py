from datetime import date as date_type
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Round(db.Model):
    __tablename__ = 'round'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('user.id'), index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey('course.id'), index=True)
    tee_set_id: Mapped[int] = mapped_column(ForeignKey('tee_set.id'), index=True)
    played_date: Mapped[date_type] = mapped_column()
    notes: Mapped[Optional[str]] = mapped_column(db.String(500))
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc))

    # Cached/derived, never entered directly -- written by
    # app/services/scoring.py::recalculate() from the hole scores below.
    gross_score: Mapped[Optional[int]] = mapped_column()
    adjusted_gross_score: Mapped[Optional[int]] = mapped_column()
    score_differential: Mapped[Optional[float]] = mapped_column(Numeric(4, 1))

    user: Mapped['User'] = relationship(back_populates='rounds')
    course: Mapped['Course'] = relationship(back_populates='rounds')
    tee_set: Mapped['TeeSet'] = relationship()
    hole_scores: Mapped[list['HoleScore']] = relationship(
        back_populates='round', cascade='all, delete-orphan',
        order_by='HoleScore.hole_id')

    def __repr__(self):
        return f'<Round {self.played_date} user={self.user_id} course={self.course_id}>'


class HoleScore(db.Model):
    __tablename__ = 'hole_score'
    __table_args__ = (
        UniqueConstraint('round_id', 'hole_id', name='uq_hole_score_round_hole'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    round_id: Mapped[int] = mapped_column(ForeignKey('round.id'), index=True)
    hole_id: Mapped[int] = mapped_column(ForeignKey('hole.id'), index=True)
    strokes: Mapped[int] = mapped_column()
    putts: Mapped[Optional[int]] = mapped_column()
    fairway_hit: Mapped[Optional[bool]] = mapped_column()
    gir: Mapped[Optional[bool]] = mapped_column()

    round: Mapped['Round'] = relationship(back_populates='hole_scores')
    hole: Mapped['Hole'] = relationship()

    def __repr__(self):
        return f'<HoleScore round={self.round_id} hole={self.hole_id} strokes={self.strokes}>'
