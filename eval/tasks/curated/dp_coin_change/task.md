# dp_coin_change — minimum coins (unbounded), -1 if impossible

## Goal
Implement `coin_change(coins: list, amount: int) -> int` in `coin_change.py`.

You are given a list `coins` of positive integer denominations and a
non-negative integer `amount`. Each denomination may be used an **unlimited**
number of times (this is the *unbounded* coin-change problem). Return the
**minimum number of coins** whose values sum **exactly** to `amount`. If no
combination of the given coins sums to exactly `amount`, return `-1`.

### Specification
- Input:
  - `coins`: a list of positive integers (the available denominations). The
    denominations are distinct. The list may be empty.
  - `amount`: a non-negative integer (the target sum).
- Output: a single `int` — the minimum coin count, or `-1` if `amount` is not
  reachable.
- **`amount == 0`** is always reachable with **0** coins, regardless of the
  coins list (return `0`). This holds even when `coins` is empty.
- If `amount > 0` and `coins` is empty, the answer is `-1`.
- A "greedy" largest-coin-first strategy is **not** always correct; you must
  return the true minimum. For example with `coins = [1, 3, 4]` and
  `amount = 6`, the answer is `2` (3 + 3), not `3` (4 + 1 + 1).

### Examples
```
coin_change([1, 2, 5], 11)          == 3    # 5 + 5 + 1
coin_change([2], 3)                 == -1   # odd target, only even coin
coin_change([1, 2, 5], 0)           == 0
coin_change([], 0)                  == 0
coin_change([], 7)                  == -1
coin_change([1], 0)                 == 0
coin_change([1], 5)                 == 5
coin_change([1, 3, 4], 6)           == 2    # 3 + 3 (greedy would give 3)
coin_change([2, 5, 10, 1], 27)      == 4    # 10 + 10 + 5 + 2
coin_change([186, 419, 83, 408], 6249) == 20
coin_change([5, 10], 3)             == -1
```

### Constraints / notes
- Pure standard library only.
- `amount` can be up to a few thousand and there can be several denominations;
  an O(amount * len(coins)) dynamic-programming solution is expected. Do not
  use exponential brute-force recursion without memoization.
- Do not mutate the input list.

## Category
dp

## Difficulty
hard

## Tests
hidden

## Source/License
Authored for coding-agent eval. MIT.
