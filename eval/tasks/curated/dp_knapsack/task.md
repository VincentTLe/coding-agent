# dp_knapsack — 0/1 knapsack maximum value under capacity

## Goal
Implement `knapsack(weights: list, values: list, capacity: int) -> int` in
`knapsack.py`.

You are given `n` items. Item `i` has weight `weights[i]` and value
`values[i]`. Given an integer `capacity`, choose a **subset** of the items so
that the **sum of weights does not exceed `capacity`** and the **sum of values
is maximised**. Return that maximum total value.

This is the classic **0/1 knapsack**: each item is either taken (once) or left
behind — items cannot be split (no fractional knapsack) and cannot be taken
multiple times (no unbounded knapsack).

### Specification
- Input:
  - `weights`: list of non-negative integers, length `n`.
  - `values`: list of non-negative integers, length `n` (same length as
    `weights`; `values[i]` pairs with `weights[i]`).
  - `capacity`: a non-negative integer — the maximum total weight allowed.
- Output: a single `int` — the maximum total value of a subset whose total
  weight is `<= capacity`.
- The empty subset (total weight 0, total value 0) is always allowed, so the
  answer is **never negative** and is at least `0`.
- If `weights` (and `values`) are empty, the answer is `0`.
- If `capacity == 0`, only zero-weight items can be included; the answer is the
  sum of values of all items with weight `0` (often `0`).
- An item whose weight alone exceeds `capacity` can never be chosen.

### Examples
```
knapsack([1, 3, 4, 5], [1, 4, 5, 7], 7) == 9    # take items of weight 3 and 4 (value 4 + 5)
knapsack([2, 3, 4], [3, 4, 5], 5)       == 7    # weights 2 + 3, values 3 + 4
knapsack([], [], 10)                    == 0
knapsack([5], [10], 4)                  == 0    # the only item doesn't fit
knapsack([1, 2, 3], [10, 20, 30], 6)    == 60   # everything fits
knapsack([4, 5, 1], [1, 2, 3], 4)       == 3    # only the weight-1 item (value 3) fits within 4
knapsack([0, 0, 2], [5, 7, 3], 0)       == 12   # both zero-weight items, value 5 + 7
```

### Constraints / notes
- Pure standard library only.
- `capacity` may be up to a few thousand and `n` up to a few hundred; an
  O(n * capacity) dynamic-programming solution is expected. Do not enumerate
  all 2**n subsets.
- Do not mutate the input lists.

## Category
dp

## Difficulty
hard

## Tests
hidden

## Source/License
Authored for coding-agent eval. MIT.
