"""World Handicap System (WHS) calculations.

Scope: current WHS rules for Score Differential and Handicap Index
(best-8-of-20 with the sliding table below), the net-double-bogey cap for
adjusted gross score, and Course Handicap. Deliberately out of scope:
Playing Conditions Calculation (needs field-wide scoring data this app
doesn't have, so PCC is always treated as 0), the soft/hard cap against a
trending-down low index, and plus-handicap stroke allocation (a course
handicap <= 0 is treated as receiving no strokes).

Everything in this module except recalculate_index() is a pure function
over plain values -- no DB access, no model imports beyond what's needed
for type context.
"""
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

from app.extensions import db

# WHS Rule 5.1: rounds played -> (how many of the lowest differentials to
# average, adjustment applied to that average). 20+ rounds always use the
# lowest 8 with no adjustment.
_WHS_TABLE = {
    3: (1, -2.0),
    4: (1, -1.0),
    5: (1, 0.0),
    6: (2, -1.0),
    7: (2, 0.0),
    8: (2, 0.0),
    9: (3, 0.0),
    10: (3, 0.0),
    11: (3, 0.0),
    12: (4, 0.0),
    13: (4, 0.0),
    14: (4, 0.0),
    15: (5, 0.0),
    16: (5, 0.0),
    17: (6, 0.0),
    18: (6, 0.0),
    19: (7, 0.0),
    20: (8, 0.0),
}

HANDICAP_INDEX_CAP = Decimal('54.0')


def _to_decimal(value):
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _round_half_up(value, places):
    quantum = Decimal(1).scaleb(-places)
    return value.quantize(quantum, rounding=ROUND_HALF_UP)


def _truncate(value, places):
    quantum = Decimal(1).scaleb(-places)
    return value.quantize(quantum, rounding=ROUND_DOWN)


def strokes_received(course_handicap, stroke_index, hole_count=18):
    """Extra strokes a player gets on one hole under their course handicap.

    Standard WHS stroke allocation: every hole gets floor(course_handicap /
    hole_count) strokes, plus one more on the `course_handicap % hole_count`
    hardest holes (lowest stroke_index). A course handicap <= 0 receives no
    strokes (plus-handicap allocation is out of scope).
    """
    course_handicap = max(course_handicap, 0)
    base, remainder = divmod(course_handicap, hole_count)
    return base + (1 if stroke_index <= remainder else 0)


def net_double_bogey_cap(par, stroke_index, course_handicap, hole_count=18):
    """Max strokes that count toward adjusted gross score on one hole."""
    return par + 2 + strokes_received(course_handicap, stroke_index, hole_count)


def adjusted_gross_score(round_, course_handicap):
    """Sum of each hole's strokes, capped at that hole's net double bogey.

    `round_` needs only a `.hole_scores` iterable of objects with `.strokes`
    and `.hole.par` / `.hole.stroke_index` -- a real Round works, and so
    does a lightweight stand-in, which is what the tests use.
    """
    hole_count = len(round_.hole_scores)
    total = 0
    for hs in round_.hole_scores:
        cap = net_double_bogey_cap(hs.hole.par, hs.hole.stroke_index,
                                    course_handicap, hole_count)
        total += min(hs.strokes, cap)
    return total


def score_differential(adjusted_gross, course_rating, slope_rating):
    """(113 / Slope) x (Adjusted Gross - Course Rating), rounded to 0.1.

    PCC is always 0 here (see module docstring).
    """
    raw = (Decimal(113) / _to_decimal(slope_rating)) * (
        _to_decimal(adjusted_gross) - _to_decimal(course_rating))
    return float(_round_half_up(raw, 1))


def handicap_index(differentials):
    """WHS Handicap Index from score differentials, most-recent-first.

    Returns None with fewer than 3 differentials (WHS requires at least 3
    scores before any index exists). Only the most recent 20 are ever used.
    Truncated (not rounded) to one decimal, per WHS Rule 5.3, and capped at
    54.0.
    """
    count = len(differentials)
    if count < 3:
        return None
    recent = differentials[:20]
    use_lowest, adjustment = _WHS_TABLE.get(len(recent), (8, 0.0))
    lowest = sorted(_to_decimal(d) for d in recent)[:use_lowest]
    average = sum(lowest) / Decimal(len(lowest))
    index = average + _to_decimal(adjustment)
    index = min(index, HANDICAP_INDEX_CAP)
    return float(_truncate(index, 1))


def course_handicap(index, slope_rating, course_rating, par):
    """Course Handicap = round(Index x Slope/113 + (Course Rating - Par))."""
    raw = (_to_decimal(index) * (_to_decimal(slope_rating) / Decimal(113))
           + (_to_decimal(course_rating) - _to_decimal(par)))
    return int(_round_half_up(raw, 0))


def recalculate_index(user):
    """Refresh user.hdcp_index from their rounds' stored score_differential.

    The only DB-touching function in this module -- everything else here
    is pure. Rounds without a differential yet (e.g. a tee set missing
    rating/slope) are skipped rather than treated as 0.
    """
    from app.models.round import Round

    rounds = (Round.query.filter_by(user_id=user.id)
              .filter(Round.score_differential.isnot(None))
              .order_by(Round.played_date.desc(), Round.id.desc())
              .all())
    differentials = [float(r.score_differential) for r in rounds]
    user.hdcp_index = handicap_index(differentials)
    db.session.commit()
