# algorithms_trapping_rain — Trapping rain water

## Goal
Implement `trap(heights) -> int` in `trapping_rain.py`.

`heights` is a list of non-negative integers representing an elevation map of
unit-width bars, where `heights[i]` is the height of the bar at position `i`.
After it rains, water pools in the valleys between taller bars. Return the
**total units of water trapped**.

### Specification
- For any index `i`, the water resting on top of bar `i` is
  `min(max(heights[:i+1]), max(heights[i:])) - heights[i]` when that value is
  positive, else `0`. The answer is the sum of trapped water across all
  indices.
- Water cannot spill past the ends: the leftmost and rightmost bars are the
  only outer walls.
- An empty list, a single bar, or two bars trap `0` (no valley exists).
- If any element of `heights` is negative, raise `ValueError`.
- `heights` must not be mutated.

### Examples
```
trap([0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1]) == 6
trap([4, 2, 0, 3, 2, 5])                    == 9
trap([5, 0, 5])                             == 5
trap([1, 2, 3, 4, 5])                       == 0   # monotonic, nothing trapped
trap([])                                    == 0
trap([1, -1, 2])                            -> ValueError
```

### Constraints / notes
- Pure standard library only.
- Solve in O(len(heights)) time with O(1) extra space (the two-pointer
  technique). The suite includes inputs with ~20,000 bars, so an O(n^2)
  per-index scan is too slow; an O(n) prefix/suffix-array method is correct but
  the two-pointer approach is the intended solution.

## Category
algorithms

## Difficulty
hard

## Tests
hidden

## Source/License
Authored for coding-agent eval. MIT.
