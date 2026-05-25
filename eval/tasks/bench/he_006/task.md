# he_006 — parse_nested_parens

## Goal
from typing import List


def parse_nested_parens(paren_string: str) -> List[int]:
    """ Input to this function is a string represented multiple groups for nested parentheses separated by spaces.
    For each of the group, output the deepest level of nesting of parentheses.
    E.g. (()()) has maximum two levels of nesting while ((())) has three.

    >>> parse_nested_parens('(()()) ((())) () ((())()())')
    [2, 3, 1, 3]
    """

Implement `parse_nested_parens` in `parse_nested_parens.py` so all tests pass.

## Category
recursion

## Difficulty
hard

## Tests
hidden

## Source/License
HumanEval/6 via EvalPlus (HumanEval+). HumanEval: MIT; EvalPlus augmented tests: Apache-2.0.
