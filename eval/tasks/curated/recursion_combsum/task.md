# recursion_combsum — Combination sum (unique combinations to a target)

## Goal
Implement `combination_sum(candidates, target) -> list` in
`combination_sum.py`.

`candidates` is a list of positive integers; `target` is an integer. Find every
**unique** multiset of candidate values whose sum is exactly `target`. The same
candidate value may be reused **any number of times**. Two combinations are
considered identical if they use the same values the same number of times,
regardless of order.

### Output format (must match exactly)
- Each combination is a `list[int]` sorted in **non-decreasing** order.
- The return value is a `list` of those combinations sorted in ascending
  lexicographic order (element-by-element comparison of the sorted
  combinations).
- `target == 0` yields exactly one (empty) combination: return `[[]]`.
- If nothing sums to `target` (e.g. negative `target`, or every candidate too
  large), return `[]`.

### Input rules
- Every element of `candidates` must be a positive `int` (`> 0`); a value `<= 0`
  or a `bool` raises `ValueError`.
- `target` must be an `int` and not a `bool`; otherwise raise `ValueError`.
- Duplicate values in `candidates` must not yield duplicate combinations
  (deduplicate the candidate set).
- `candidates` must not be mutated.

### Examples
```
combination_sum([2, 3, 6, 7], 7) == [[2, 2, 3], [7]]
combination_sum([2, 3, 5], 8)    == [[2, 2, 2, 2], [2, 3, 3], [3, 5]]
combination_sum([2], 1)          == []
combination_sum([3, 5, 8], 0)    == [[]]
combination_sum([2, 4, 2, 3], 6) == [[2, 2, 2], [2, 4], [3, 3]]   # deduped
combination_sum([2, 3], -1)      == []
combination_sum([2, 3], 1.5)     -> ValueError
combination_sum([0, 2], 5)       -> ValueError
```

### Constraints / notes
- Pure standard library only. Solve by recursive backtracking over the sorted
  unique candidates (each recursive branch may reuse the current candidate).
- Inputs are small (a handful of candidates, modest targets); correctness and
  exact output formatting matter more than micro-optimization.

## Category
recursion

## Difficulty
hard

## Tests
hidden

## Source/License
Authored for coding-agent eval. MIT.
