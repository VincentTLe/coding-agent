# algorithms_sliding_window — Maximum sum of a fixed-size window

## Goal
Implement two functions in `sliding_window.py` operating on a list of integers
`nums` (which may include negatives) and a window length `k`.

### `max_subarray_sum_k(nums, k) -> int`
Return the maximum sum over every contiguous subarray (window) of length
**exactly** `k`.

### `first_max_window_start(nums, k) -> int`
Return the **smallest (leftmost)** starting index of a length-`k` window whose
sum equals `max_subarray_sum_k(nums, k)`.

### Specification
- `k` must be an `int` with `1 <= k <= len(nums)`; otherwise raise
  `ValueError`. This covers `k == 0`, negative `k`, `k > len(nums)`, and any
  `k` against an empty `nums` (no window fits, always invalid). A `bool` is not
  a valid `k`.
- When all elements are negative, the maximum is simply the least-negative
  window sum (windows are never empty, so the answer is never `0` by default).
- On ties for the maximum sum, `first_max_window_start` returns the leftmost
  start index.
- Neither function may mutate `nums`.

### Examples
```
max_subarray_sum_k([2, 1, 5, 1, 3, 2], 3)   == 9    # window [5, 1, 3]
max_subarray_sum_k([-1, -2, -3, -4], 2)     == -3   # window [-1, -2]
max_subarray_sum_k([5], 1)                  == 5
max_subarray_sum_k([1, 2, 3, 4], 4)         == 10
max_subarray_sum_k([2, 3], 3)               -> ValueError

first_max_window_start([2, 1, 5, 1, 3, 2], 3) == 2
first_max_window_start([1, 1, 1, 1], 2)       == 0  # leftmost of tied windows
first_max_window_start([4, 4, 4, 1], 1)       == 0
```

### Constraints / notes
- Pure standard library only.
- Use a single linear pass that maintains a running window sum
  (O(len(nums))), rather than re-summing each window from scratch
  (O(len(nums) * k)). The suite exercises inputs with up to 100,000 elements.

## Category
algorithms

## Difficulty
hard

## Tests
hidden

## Source/License
Authored for coding-agent eval. MIT.
