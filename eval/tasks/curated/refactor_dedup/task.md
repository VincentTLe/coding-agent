# refactor_dedup — order-preserving de-duplication for any items

## Goal
`dedup.py` provides two utilities whose test suite (`test_dedup.py`) is
currently RED. Refactor the module so all tests pass, keeping both public
signatures unchanged.

`dedup(items)` must return the items with duplicates removed while preserving
**first-seen order**. Two items are duplicates iff they compare equal (`==`).
Critically, it must work for ANY items — including **unhashable** ones such as
`list` and `dict`, and inputs that mix hashable and unhashable values:
- `dedup([3, 1, 3, 2, 1]) == [3, 1, 2]`
- `dedup([[1], [1], [2]]) == [[1], [2]]`
- `dedup([1, [2], 1, "x", [2]]) == [1, [2], "x"]`

The current implementation uses a `set` of seen items, which is fast for
hashable values but raises `TypeError` the moment an unhashable item appears.
Refactor it to handle unhashable items without losing the order guarantee (and
ideally without making the common all-hashable case quadratic).

`first_unique(items)` must return the first item that appears **exactly once**,
or `None` if every item repeats or the input is empty:
- `first_unique([2, 3, 2, 4, 3]) == 4`
- `first_unique([1, 1, 2, 2]) is None`

The current `first_unique` has a logic error (it returns the first *repeated*
item instead of the first *unique* one). Fix it.

Run the tests, read the contracts in the docstrings, and refactor accordingly.

## Category
refactor

## Difficulty
hard

## Tests
visible

## Source/License
Authored for coding-agent eval. MIT.
