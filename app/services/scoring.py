from app.extensions import db
from app.services import handicap


def recalculate(round_):
    """Recompute derived score fields on a Round from its HoleScores, and
    refresh the player's cached handicap index to include this round.

    Called from every create/edit path so gross_score, adjusted_gross_score,
    and score_differential are always derived from the hole-by-hole detail
    rather than entered directly.

    The net-double-bogey cap needs a course handicap, which needs a
    handicap index -- but this round's own differential hasn't been
    computed yet, so it uses the player's *current* cached index (i.e. as
    of their rounds prior to this one), not a value this round could
    circularly affect. Before a player has 3 rounds recorded (no index
    yet), course handicap is treated as 0 -- no bonus strokes.
    """
    round_.gross_score = sum(hs.strokes for hs in round_.hole_scores)

    tee_set = round_.tee_set
    if tee_set.course_rating is None or tee_set.slope_rating is None:
        # No rating/slope on this tee set (e.g. a manually-created one that
        # hasn't been filled in) -- can't compute a differential.
        round_.adjusted_gross_score = None
        round_.score_differential = None
        db.session.commit()
        return

    current_index = (float(round_.user.hdcp_index)
                      if round_.user.hdcp_index is not None else None)
    player_course_handicap = 0
    if current_index is not None:
        player_course_handicap = handicap.course_handicap(
            current_index, tee_set.slope_rating, float(tee_set.course_rating),
            tee_set.par)

    round_.adjusted_gross_score = handicap.adjusted_gross_score(
        round_, player_course_handicap)
    round_.score_differential = handicap.score_differential(
        round_.adjusted_gross_score, float(tee_set.course_rating),
        tee_set.slope_rating)
    db.session.commit()

    handicap.recalculate_index(round_.user)
