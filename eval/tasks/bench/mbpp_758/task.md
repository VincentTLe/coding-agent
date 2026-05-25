# mbpp_758 — unique_sublists

## Goal
Write a function to count lists within a list. The function should return a dictionary where every list is converted to a tuple and the value of such tuple is the number of its occurencies in the original list.

Implement `unique_sublists` in `unique_sublists.py` so the tests pass. Example checks:
assert unique_sublists([[1, 3], [5, 7], [1, 3], [13, 15, 17], [5, 7], [9, 11]] )=={(1, 3): 2, (5, 7): 2, (13, 15, 17): 1, (9, 11): 1}
assert unique_sublists([['green', 'orange'], ['black'], ['green', 'orange'], ['white']])=={('green', 'orange'): 2, ('black',): 1, ('white',): 1}

## Category
data_structures

## Difficulty
medium

## Tests
hidden

## Source/License
MBPP sanitized task 758. MBPP: CC-BY-4.0.
