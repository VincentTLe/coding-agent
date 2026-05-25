# refactor_intervals — merge overlapping intervals correctly

## Goal
`intervals.py` contains a `merge_intervals(intervals)` function that merges a
list of closed `(start, end)` integer intervals. It handles the obvious case
but the test suite (`test_intervals.py`) is currently RED: the naive logic
violates several documented invariants.

Refactor `merge_intervals` so every test passes, keeping the public signature
`merge_intervals(intervals: List[Tuple[int, int]]) -> List[Tuple[int, int]]`.

The contract the tests enforce:
- Intervals may arrive in any order and may be "reversed" (`(6, 2)` means the
  same interval as `(2, 6)`); output intervals must be normalized to
  `start <= end`.
- Intervals that merely *touch* (the end of one equals the start of the next,
  e.g. `(1, 2)` and `(2, 3)`) overlap and must merge into one (`(1, 3)`).
- An interval fully contained in another must NOT shrink the enclosing span:
  `[(1, 10), (2, 3)]` -> `[(1, 10)]`.
- The result is sorted by start with no overlapping or touching intervals.

There is also a randomized property test asserting that the merged output
covers exactly the same set of integer points as the input and is itself
disjoint and sorted. Read the failing tests, find the edge cases the current
code mishandles, and fix them.

## Category
refactor

## Difficulty
hard

## Tests
visible

## Source/License
Authored for coding-agent eval. MIT.
