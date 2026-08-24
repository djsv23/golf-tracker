"""Dashboard aggregations over a user's round history.

Every function returns plain dicts/lists (JSON-ready) and is guarded
against both the empty case (no rounds yet) and rounds with missing
optional detail (differential, putts, fairway/GIR) -- those rounds are
excluded from the relevant aggregate rather than treated as zero.
"""
from collections import defaultdict

from app.models.round import Round


def _user_rounds(user_id):
    return (Round.query.filter_by(user_id=user_id)
            .order_by(Round.played_date.asc(), Round.id.asc())
            .all())


def scoring_trend(rounds):
    """[{date, differential}] oldest first, for rounds with a differential."""
    return [
        {'date': r.played_date.isoformat(), 'differential': float(r.score_differential)}
        for r in rounds if r.score_differential is not None
    ]


def gross_score_distribution(rounds):
    """{gross_score: count}, sorted by score."""
    counts = defaultdict(int)
    for r in rounds:
        if r.gross_score is not None:
            counts[r.gross_score] += 1
    return dict(sorted(counts.items()))


def scoring_average_by_par(rounds):
    """{par: average strokes per hole of that par}, e.g. {3: 3.8, 4: 4.9, 5: 5.6}."""
    totals = defaultdict(lambda: [0, 0])  # par -> [stroke total, hole count]
    for r in rounds:
        for hs in r.hole_scores:
            totals[hs.hole.par][0] += hs.strokes
            totals[hs.hole.par][1] += 1
    return {
        par: round(total / count, 2)
        for par, (total, count) in sorted(totals.items())
    }


def putts_per_round(rounds):
    """Average total putts per round, only over rounds with putts on every hole."""
    values = []
    for r in rounds:
        hole_putts = [hs.putts for hs in r.hole_scores]
        if hole_putts and all(p is not None for p in hole_putts):
            values.append(sum(hole_putts))
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def fairway_and_gir_percentage(rounds):
    """Percent of eligible holes where the fairway/green was hit.

    Par-3 holes have no tee shot "fairway" to hit and are excluded from
    the fairway count; they still count toward GIR.
    """
    fairway_eligible = fairway_hit = gir_eligible = gir_hit = 0
    for r in rounds:
        for hs in r.hole_scores:
            if hs.hole.par != 3 and hs.fairway_hit is not None:
                fairway_eligible += 1
                fairway_hit += int(hs.fairway_hit)
            if hs.gir is not None:
                gir_eligible += 1
                gir_hit += int(hs.gir)
    return {
        'fairway_pct': (round(100 * fairway_hit / fairway_eligible, 1)
                         if fairway_eligible else None),
        'gir_pct': round(100 * gir_hit / gir_eligible, 1) if gir_eligible else None,
    }


def best_worst_rounds(rounds):
    scored = [r for r in rounds if r.gross_score is not None]
    if not scored:
        return {'best': None, 'worst': None}
    return {
        'best': _round_summary(min(scored, key=lambda r: r.gross_score)),
        'worst': _round_summary(max(scored, key=lambda r: r.gross_score)),
    }


def _round_summary(round_):
    return {
        'id': round_.id,
        'date': round_.played_date.isoformat(),
        'course': round_.course.display_name,
        'gross_score': round_.gross_score,
    }


def dashboard_data(user_id):
    rounds = _user_rounds(user_id)
    return {
        'round_count': len(rounds),
        'scoring_trend': scoring_trend(rounds),
        'gross_score_distribution': gross_score_distribution(rounds),
        'scoring_average_by_par': scoring_average_by_par(rounds),
        'putts_per_round': putts_per_round(rounds),
        **fairway_and_gir_percentage(rounds),
        **best_worst_rounds(rounds),
    }
