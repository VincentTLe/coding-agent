import random

import pytest

from combination_sum import combination_sum


def _brute(candidates, target):
    """Independent oracle: enumerate multiplicities of each unique candidate."""
    uniq = sorted(set(candidates))
    res = set()

    def rec(i, rem, combo):
        if rem == 0:
            res.add(tuple(combo))
            return
        if i >= len(uniq):
            return
        c = uniq[i]
        k = 0
        while c * k <= rem:
            rec(i + 1, rem - c * k, combo + [c] * k)
            k += 1

    if target < 0:
        return []
    rec(0, target, [])
    return sorted(list(t) for t in res)


# -------------------------------------------------------------- canonical

def test_classic_example_one():
    assert combination_sum([2, 3, 6, 7], 7) == [[2, 2, 3], [7]]


def test_classic_example_two():
    assert combination_sum([2, 3, 5], 8) == [[2, 2, 2, 2], [2, 3, 3], [3, 5]]


def test_single_candidate_repeated():
    assert combination_sum([1], 3) == [[1, 1, 1]]
    assert combination_sum([7], 7) == [[7]]


# -------------------------------------------------------------- edge cases

def test_target_zero_gives_empty_combination():
    assert combination_sum([3, 5, 8], 0) == [[]]
    assert combination_sum([2, 3, 5], 0) == [[]]


def test_no_solution_returns_empty_list():
    assert combination_sum([2], 1) == []
    assert combination_sum([5, 10], 3) == []
    assert combination_sum([100], 7) == []


def test_negative_target_returns_empty():
    assert combination_sum([2, 3], -1) == []
    assert combination_sum([5], -100) == []


def test_candidate_equals_target():
    assert combination_sum([7, 2, 3], 7) == [[2, 2, 3], [7]]


# -------------------------------------------------------------- dedup / ordering

def test_duplicate_candidates_deduplicated():
    # Duplicates in the input must not yield duplicate combinations.
    assert combination_sum([2, 4, 2, 3], 6) == [[2, 2, 2], [2, 4], [3, 3]]
    assert combination_sum([3, 3, 3], 6) == [[3, 3]]


def test_each_combination_is_sorted_nondecreasing():
    for combo in combination_sum([8, 7, 6, 5, 4, 3, 2], 10):
        assert combo == sorted(combo)


def test_outer_list_is_lexicographically_sorted():
    out = combination_sum([8, 7, 6, 5, 4, 3, 2], 10)
    assert out == sorted(out)
    # No duplicate combinations.
    assert len({tuple(c) for c in out}) == len(out)
    assert all(sum(c) == 10 for c in out)


def test_unsorted_candidates_still_canonical():
    # Input order must not affect the canonical output.
    a = combination_sum([6, 7, 2, 3], 7)
    b = combination_sum([2, 3, 6, 7], 7)
    assert a == b == [[2, 2, 3], [7]]


# -------------------------------------------------------------- validation

def test_target_must_be_int():
    with pytest.raises(ValueError):
        combination_sum([2, 3], 1.5)
    with pytest.raises(ValueError):
        combination_sum([2, 3], True)  # bool is not a valid target


def test_candidates_must_be_positive_ints():
    with pytest.raises(ValueError):
        combination_sum([0, 2], 5)
    with pytest.raises(ValueError):
        combination_sum([2, -1], 5)
    with pytest.raises(ValueError):
        combination_sum([2, False], 5)  # bool candidate rejected


# -------------------------------------------------------------- safety

def test_does_not_mutate_input():
    candidates = [6, 7, 2, 3]
    snapshot = list(candidates)
    combination_sum(candidates, 7)
    assert candidates == snapshot


# -------------------------------------------------------------- random oracle

def test_random_matches_brute_force():
    rng = random.Random(20260524)
    for _ in range(120):
        size = rng.randint(1, 5)
        candidates = [rng.randint(1, 9) for _ in range(size)]
        target = rng.randint(0, 18)
        assert combination_sum(candidates, target) == _brute(candidates, target)
