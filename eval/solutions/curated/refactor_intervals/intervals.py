"""Interval merging utilities (reference solution)."""

from typing import List, Tuple

Interval = Tuple[int, int]


def merge_intervals(intervals: List[Interval]) -> List[Interval]:
    """Merge a list of ``(start, end)`` closed intervals.

    Contract:
      * Input intervals may be given in any order and may be "reversed"
        (i.e. ``start > end`` means the same interval as ``end, start``).
      * Two intervals that merely *touch* (the end of one equals the start of
        the next, e.g. ``(1, 2)`` and ``(2, 3)``) overlap and must be merged
        into a single interval (``(1, 3)``).
      * An interval fully contained in another must not shrink the enclosing
        one (``[(1, 10), (2, 3)]`` -> ``[(1, 10)]``).
      * The result is sorted by start and contains no overlapping or touching
        intervals.

    Examples:
        >>> merge_intervals([(1, 3), (2, 6), (8, 10)])
        [(1, 6), (8, 10)]
        >>> merge_intervals([(1, 2), (2, 3)])
        [(1, 3)]
    """
    if not intervals:
        return []

    # Normalize reversed intervals so that start <= end, then sort.
    normalized = [(min(a, b), max(a, b)) for a, b in intervals]
    normalized.sort()

    merged: List[Interval] = [normalized[0]]
    for start, end in normalized[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:  # overlapping OR touching -> merge
            merged[-1] = (last_start, max(last_end, end))  # keep the larger end
        else:
            merged.append((start, end))
    return merged
