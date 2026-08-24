from types import SimpleNamespace

import pytest

from app.services.handicap import (adjusted_gross_score, course_handicap,
                                    handicap_index, net_double_bogey_cap,
                                    score_differential, strokes_received)


# --- strokes_received / net_double_bogey_cap ------------------------------

@pytest.mark.parametrize('stroke_index,expected', [
    (1, 1), (5, 1), (9, 1),   # <= course handicap -> 1 stroke
    (10, 0), (15, 0), (18, 0),  # > course handicap -> 0 strokes
])
def test_strokes_received_single_stroke_band(stroke_index, expected):
    assert strokes_received(course_handicap=9, stroke_index=stroke_index) == expected


@pytest.mark.parametrize('stroke_index,expected', [
    (1, 2), (2, 2),            # within the remainder -> base(1) + 1 = 2
    (3, 1), (10, 1), (18, 1),  # outside the remainder -> base(1) + 0 = 1
])
def test_strokes_received_two_stroke_band(stroke_index, expected):
    # 20 = 1*18 + 2, so every hole gets >=1, and holes 1-2 get a 2nd.
    assert strokes_received(course_handicap=20, stroke_index=stroke_index) == expected


def test_strokes_received_zero_handicap_gets_no_strokes():
    for stroke_index in (1, 9, 18):
        assert strokes_received(course_handicap=0, stroke_index=stroke_index) == 0


def test_strokes_received_negative_handicap_treated_as_zero():
    assert strokes_received(course_handicap=-3, stroke_index=1) == 0


def test_net_double_bogey_cap_par4_with_stroke():
    # par 4 + 2 + 1 stroke (stroke_index 5 <= course handicap 9)
    assert net_double_bogey_cap(par=4, stroke_index=5, course_handicap=9) == 7


def test_net_double_bogey_cap_par4_without_stroke():
    # par 4 + 2 + 0 strokes (stroke_index 15 > course handicap 9)
    assert net_double_bogey_cap(par=4, stroke_index=15, course_handicap=9) == 6


def test_net_double_bogey_cap_nine_hole_tee_set():
    # 9-hole allocation: stroke index range is 1-9, not 1-18.
    assert net_double_bogey_cap(par=4, stroke_index=5, course_handicap=5,
                                 hole_count=9) == 7  # 4+2+1
    assert net_double_bogey_cap(par=4, stroke_index=6, course_handicap=5,
                                 hole_count=9) == 6  # 4+2+0


# --- adjusted_gross_score (blow-up hole capping) ---------------------------

def _hole_score(par, stroke_index, strokes):
    return SimpleNamespace(strokes=strokes,
                            hole=SimpleNamespace(par=par, stroke_index=stroke_index))


def test_adjusted_gross_score_caps_a_blowup_hole():
    # 18 holes, all par 4, stroke indexes 1-18, course handicap 9 (so holes
    # 1-9 get 1 stroke, cap 7; holes 10-18 get 0 strokes, cap 6). One hole
    # (stroke index 5) blows up to 12 strokes and must be capped at 7.
    hole_scores = [_hole_score(par=4, stroke_index=i + 1, strokes=4) for i in range(18)]
    hole_scores[4] = _hole_score(par=4, stroke_index=5, strokes=12)  # blow-up hole
    round_ = SimpleNamespace(hole_scores=hole_scores)

    result = adjusted_gross_score(round_, course_handicap=9)

    # 17 holes at actual 4 strokes (all under their caps) + capped 7 on the
    # blow-up hole, instead of the actual 12.
    assert result == 17 * 4 + 7 == 75
    # Confirm the raw (uncapped) gross would have been higher, so the cap
    # actually did something.
    raw_gross = sum(hs.strokes for hs in hole_scores)
    assert raw_gross == 17 * 4 + 12 == 80
    assert result < raw_gross


def test_adjusted_gross_score_no_capping_needed():
    hole_scores = [_hole_score(par=4, stroke_index=i + 1, strokes=5) for i in range(18)]
    round_ = SimpleNamespace(hole_scores=hole_scores)
    assert adjusted_gross_score(round_, course_handicap=9) == 18 * 5 == 90


# --- score_differential -----------------------------------------------------

def test_score_differential_scratch_slope():
    # (113/113) * (90 - 72) = 18.0 exactly
    assert score_differential(adjusted_gross=90, course_rating=72.0, slope_rating=113) == 18.0


def test_score_differential_rounds_to_nearest_tenth():
    # (113/125) * (90 - 72.0) = 16.272 -> rounds (not truncates) to 16.3
    assert score_differential(adjusted_gross=90, course_rating=72.0, slope_rating=125) == 16.3


# --- course_handicap ---------------------------------------------------------

def test_course_handicap_par_equals_rating():
    # 16.3 * (125/113) + (72.0 - 72) = 18.030975... -> rounds to 18
    assert course_handicap(index=16.3, slope_rating=125, course_rating=72.0, par=72) == 18


def test_course_handicap_rating_above_par_rounds_half_up():
    # 10.0 * (113/113) + (74.5 - 72) = 12.5 -> rounds up (half-up) to 13
    assert course_handicap(index=10.0, slope_rating=113, course_rating=74.5, par=72) == 13


# The tests above all use either rating == par or a scratch slope (113) to
# keep the arithmetic hand-checkable, but real courses look nothing like
# that -- every seeded course (data/courses.yml) has rating well above par
# and slope well above 120 (Bethpage Blue: 74.4/138/72, Pebble Beach Blue:
# 75.5/145/72). A sign or term-order slip in the (rating - par) part of
# either formula could still pass every test above while being wrong for
# every course an actual user plays. Expected values here were computed
# independently via decimal.Decimal, not by running the implementation.

def test_score_differential_realistic_rating_and_high_slope():
    # (113/138) * (88 - 74.4) = 11.136... -> 11.1
    assert score_differential(adjusted_gross=88, course_rating=74.4,
                               slope_rating=138) == 11.1


def test_course_handicap_realistic_rating_and_high_slope():
    # 10.0 * (138/113) + (74.4 - 72) = 14.612... -> 15
    assert course_handicap(index=10.0, slope_rating=138, course_rating=74.4,
                            par=72) == 15


def test_score_differential_pebble_beach_blue_tees():
    # Real seeded values (data/courses.yml): rating 75.5, slope 145, par 72.
    # (113/145) * (90 - 75.5) = 11.3 exactly.
    assert score_differential(adjusted_gross=90, course_rating=75.5,
                               slope_rating=145) == 11.3


def test_course_handicap_pebble_beach_blue_tees():
    # 12.3 * (145/113) + (75.5 - 72) = 19.28... -> 19
    assert course_handicap(index=12.3, slope_rating=145, course_rating=75.5,
                            par=72) == 19


# --- handicap_index: WHS sliding table (Rule 5.1) ---------------------------
# Differentials are N consecutive integers starting at 10.0 -- for any K
# "use lowest K", the K lowest values are always [10, 11, ..., 10+K-1], so
# the expected average is 10 + (K-1)/2, independent of N. This makes every
# table row a hand-checkable one-liner.

@pytest.mark.parametrize('n_rounds,use_lowest,adjustment,expected', [
    (3, 1, -2.0, 8.0),    # avg(10) - 2.0
    (4, 1, -1.0, 9.0),    # avg(10) - 1.0
    (5, 1, 0.0, 10.0),    # avg(10)
    (6, 2, -1.0, 9.5),    # avg(10,11) - 1.0
    (7, 2, 0.0, 10.5),    # avg(10,11)
    (8, 2, 0.0, 10.5),
    (9, 3, 0.0, 11.0),    # avg(10,11,12)
    (10, 3, 0.0, 11.0),
    (11, 3, 0.0, 11.0),
    (12, 4, 0.0, 11.5),   # avg(10,11,12,13)
    (13, 4, 0.0, 11.5),
    (14, 4, 0.0, 11.5),
    (15, 5, 0.0, 12.0),   # avg(10..14)
    (16, 5, 0.0, 12.0),
    (17, 6, 0.0, 12.5),   # avg(10..15)
    (18, 6, 0.0, 12.5),
    (19, 7, 0.0, 13.0),   # avg(10..16)
    (20, 8, 0.0, 13.5),   # avg(10..17)
])
def test_handicap_index_whs_table(n_rounds, use_lowest, adjustment, expected):
    differentials = [10.0 + i for i in range(n_rounds)]
    assert handicap_index(differentials) == expected


def test_handicap_index_fewer_than_3_rounds_is_none():
    assert handicap_index([]) is None
    assert handicap_index([10.0]) is None
    assert handicap_index([10.0, 12.0]) is None


def test_handicap_index_uses_only_most_recent_20_rounds():
    # Most-recent-first: 20 rounds of 10.0, then one much older round of
    # 0.0 (the 21st entry). If the 21st entry were wrongly included in the
    # "lowest 8", it would drag the average down to 8.75; correctly
    # ignoring it (as older than the most recent 20) gives exactly 10.0.
    differentials = [10.0] * 20 + [0.0]
    assert handicap_index(differentials) == 10.0


def test_handicap_index_truncates_not_rounds():
    # lowest 3 of 9 rounds, each exactly 10.16 -> average is exactly 10.16.
    # Standard rounding would give 10.2; WHS truncation must give 10.1.
    differentials = [10.16, 10.16, 10.16] + [99.0] * 6
    assert handicap_index(differentials) == 10.1


def test_handicap_index_capped_at_54():
    # 5 rounds, use lowest 1, no adjustment: raw average would be 60.0.
    differentials = [60.0, 61.0, 62.0, 63.0, 64.0]
    assert handicap_index(differentials) == 54.0
