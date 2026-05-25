"""Interval merging utilities.

NOTE (for the agent): this module works for the common case but is naive and
violates the documented contract on several edge cases. Run the tests to see
which invariants fail, then refactor `merge_intervals` so every test passes
while keeping the same public signature.
"""

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

    ordered = sorted(intervals)
    merged: List[Interval] = [ordered[0]]
    for start, end in ordered[1:]:
        last_start, last_end = merged[-1]
        # BUG: strict '<' treats touching intervals (start == last_end) as
        # disjoint, and blindly overwrites the end so a contained interval can
        # shrink the merged span.
        if start < last_end:
            merged[-1] = (last_start, end)
        else:
            merged.append((start, end))
    return merged
