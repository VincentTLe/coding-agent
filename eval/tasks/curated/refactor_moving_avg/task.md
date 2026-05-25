# refactor_moving_avg — trailing moving average with correct boundaries

## Goal
`moving_avg.py` implements `moving_average(data, k)`, a trailing moving average
over a list of numbers. Its test suite (`test_moving_avg.py`) is currently RED:
the implementation is correct in the middle of the series but breaks at the
window boundaries.

Refactor `moving_average` so every test passes, keeping the signature
`moving_average(data: List[float], k: int) -> List[float]`.

The contract the tests enforce:
- The output has the SAME length as `data` (one value per element; no
  warm-up trimming).
- `output[i]` is the mean of the window ending at `i` and spanning at most `k`
  elements: indices `max(0, i - k + 1) .. i` inclusive. So `output[0]` is just
  `data[0]`, `output[1]` is the mean of the first two, etc., until the window
  fills.
- `k` must be a positive integer; raise `ValueError` otherwise.
- Empty `data` yields `[]`.

Examples:
- `moving_average([1, 2, 3, 4], 2) == [1.0, 1.5, 2.5, 3.5]`
- `moving_average([10, 20, 30], 5) == [10.0, 15.0, 20.0]`

The current code uses a slice `data[i-k+1:i+1]` and always divides by `k`. For
the first `k-1` positions the start index is negative, so the slice wraps
around from the END of the list, and the divisor is wrong at the boundary.
There is also a randomized property test comparing against an independent
clamped-window reference. Read the failing tests and fix the boundary
handling.

## Category
refactor

## Difficulty
hard

## Tests
visible

## Source/License
Authored for coding-agent eval. MIT.
