# he_074 — total_match

## Goal
def total_match(lst1, lst2):
    '''
    Write a function that accepts two lists of strings and returns the list that has 
    total number of chars in the all strings of the list less than the other list.

    if the two lists have the same number of chars, return the first list.

    Examples
    total_match([], []) ➞ []
    total_match(['hi', 'admin'], ['hI', 'Hi']) ➞ ['hI', 'Hi']
    total_match(['hi', 'admin'], ['hi', 'hi', 'admin', 'project']) ➞ ['hi', 'admin']
    total_match(['hi', 'admin'], ['hI', 'hi', 'hi']) ➞ ['hI', 'hi', 'hi']
    total_match(['4'], ['1', '2', '3', '4', '5']) ➞ ['4']
    '''

Implement `total_match` in `total_match.py` so all tests pass.

## Category
strings

## Difficulty
medium

## Tests
hidden

## Source/License
HumanEval/74 via EvalPlus (HumanEval+). HumanEval: MIT; EvalPlus augmented tests: Apache-2.0.
