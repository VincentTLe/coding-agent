# he_132 — is_nested

## Goal
def is_nested(string):
    '''
    Create a function that takes a string as input which contains only square brackets.
    The function should return True if and only if there is a valid subsequence of brackets 
    where at least one bracket in the subsequence is nested.

    is_nested('[[]]') ➞ True
    is_nested('[]]]]]]][[[[[]') ➞ False
    is_nested('[][]') ➞ False
    is_nested('[]') ➞ False
    is_nested('[[][]]') ➞ True
    is_nested('[[]][[') ➞ True
    '''

Implement `is_nested` in `is_nested.py` so all tests pass.

## Category
strings

## Difficulty
hard

## Tests
hidden

## Source/License
HumanEval/132 via EvalPlus (HumanEval+). HumanEval: MIT; EvalPlus augmented tests: Apache-2.0.
