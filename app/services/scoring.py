from app.extensions import db


def recalculate(round_):
    """Recompute derived score fields on a Round from its HoleScores.

    Called from every create/edit path so gross_score is never entered
    directly and never drifts from the hole-by-hole detail.

    adjusted_gross_score and score_differential are left unset here --
    they depend on the WHS net-double-bogey cap and the player's current
    course handicap, computed in app/services/handicap.py.
    """
    round_.gross_score = sum(hs.strokes for hs in round_.hole_scores)
    db.session.commit()
