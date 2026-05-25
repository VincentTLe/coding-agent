# he_021 — rescale_to_unit

## Goal
from typing import List


def rescale_to_unit(numbers: List[float]) -> List[float]:
    """ Given list of numbers (of at least two elements), apply a linear transform to that list,
    such that the smallest number will become 0 and the largest will become 1
    >>> rescale_to_unit([1.0, 2.0, 3.0, 4.0, 5.0])
    [0.0, 0.25, 0.5, 0.75, 1.0]
    """

Implement `rescale_to_unit` in `rescale_to_unit.py` so all tests pass.

## Category
arrays

## Difficulty
medium

## Tests
hidden

## Source/License
HumanEval/21 via EvalPlus (HumanEval+). HumanEval: MIT; EvalPlus augmented tests: Apache-2.0.
