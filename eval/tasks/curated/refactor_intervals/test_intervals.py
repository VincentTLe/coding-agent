import random

from intervals import merge_intervals


def _covered_points(intervals):
    """Set of every integer point covered by a list of closed intervals."""
    pts = set()
    for a, b in intervals:
        lo, hi = (a, b) if a <= b else (b, a)
        pts.update(range(lo, hi + 1))
    return pts


def _is_disjoint_sorted(merged):
    """Result must be sorted by start with no overlapping/touching intervals."""
    for (s, e) in merged:
        assert s <= e, f"interval {(s, e)} is not normalized (start <= end)"
    for i in range(1, len(merged)):
        prev_end = merged[i - 1][1]
        cur_start = merged[i][0]
        # Strictly greater: intervals sharing an endpoint (touching) or
        # overlapping should already have been merged into one.
        assert cur_start > prev_end, f"intervals {merged[i-1]} and {merged[i]} touch/overlap"


def test_basic_overlap():
    assert merge_intervals([(1, 3), (2, 6), (8, 10)]) == [(1, 6), (8, 10)]


def test_empty():
    assert merge_intervals([]) == []


def test_single():
    assert merge_intervals([(5, 7)]) == [(5, 7)]


def test_touching_intervals_merge():
    # (1,2) and (2,3) share endpoint 2 -> must merge into (1,3).
    assert merge_intervals([(1, 2), (2, 3)]) == [(1, 3)]
    assert merge_intervals([(2, 3), (1, 2), (3, 4)]) == [(1, 4)]


def test_contained_interval_does_not_shrink():
    # The inner interval must not overwrite the wider end.
    assert merge_intervals([(1, 10), (2, 3)]) == [(1, 10)]
    assert merge_intervals([(2, 3), (1, 10)]) == [(1, 10)]


def test_reversed_inputs_are_normalized():
    # (6,2) means the same as (2,6).
    assert merge_intervals([(6, 2), (1, 3)]) == [(1, 6)]


def test_no_overlap_preserved():
    assert merge_intervals([(8, 10), (1, 3), (4, 5)]) == [(1, 3), (4, 5), (8, 10)]


def test_invariant_random():
    """Property test: output is disjoint+sorted and covers exactly the same
    integer point-set as the input. Any near-miss (dropped touch, shrunk
    span, lost interval) breaks one of these."""
    rng = random.Random(20260524)
    for _ in range(300):
        n = rng.randint(0, 8)
        raw = []
        for _ in range(n):
            a = rng.randint(0, 12)
            b = rng.randint(0, 12)
            raw.append((a, b))
        out = merge_intervals(raw)
        _is_disjoint_sorted(out)
        assert _covered_points(out) == _covered_points(raw)
