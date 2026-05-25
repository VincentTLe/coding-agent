import random

import pytest

from sliding_window import first_max_window_start, max_subarray_sum_k


def _brute_max(nums, k):
    return max(sum(nums[i : i + k]) for i in range(len(nums) - k + 1))


def _brute_first_start(nums, k):
    best = _brute_max(nums, k)
    for i in range(len(nums) - k + 1):
        if sum(nums[i : i + k]) == best:
            return i
    raise AssertionError("unreachable")


# ---------------------------------------------------------------- basic spec

def test_basic_example():
    assert max_subarray_sum_k([2, 1, 5, 1, 3, 2], 3) == 9
    assert first_max_window_start([2, 1, 5, 1, 3, 2], 3) == 2


def test_single_element_window_and_list():
    assert max_subarray_sum_k([5], 1) == 5
    assert first_max_window_start([5], 1) == 0
    assert max_subarray_sum_k([7, 2, 9, 4], 1) == 9
    assert first_max_window_start([7, 2, 9, 4], 1) == 2


def test_window_equals_full_length():
    assert max_subarray_sum_k([1, 2, 3, 4], 4) == 10
    assert first_max_window_start([1, 2, 3, 4], 4) == 0
    assert max_subarray_sum_k([-2, -2, -2], 3) == -6
    assert first_max_window_start([-2, -2, -2], 3) == 0


# ---------------------------------------------------------------- negatives

def test_all_negative():
    assert max_subarray_sum_k([-1, -2, -3, -4], 2) == -3
    assert first_max_window_start([-1, -2, -3, -4], 2) == 0


def test_mixed_signs():
    nums = [3, -1, -1, 3, 5, -2, 4]
    # Windows of size 3 at starts 2 and 4 both sum to 7; the leftmost is start 2.
    assert max_subarray_sum_k(nums, 3) == 7
    assert max_subarray_sum_k(nums, 3) == _brute_max(nums, 3)
    assert first_max_window_start(nums, 3) == 2
    assert first_max_window_start(nums, 3) == _brute_first_start(nums, 3)


# ---------------------------------------------------------------- ties / leftmost

def test_leftmost_tie():
    # Two windows of size 2 both sum to 2; the leftmost start (0) must win.
    assert first_max_window_start([1, 1, 1, 1], 2) == 0
    # Equal single-element maxima -> leftmost.
    assert first_max_window_start([4, 4, 4, 1], 1) == 0
    # Tie further along.
    nums = [0, 5, 5, 0, 5, 5]
    assert first_max_window_start(nums, 2) == 1


def test_duplicates_values():
    nums = [2, 2, 2, 2, 2]
    assert max_subarray_sum_k(nums, 3) == 6
    assert first_max_window_start(nums, 3) == 0


# ---------------------------------------------------------------- validation

def test_invalid_k_too_large():
    with pytest.raises(ValueError):
        max_subarray_sum_k([2, 3], 3)
    with pytest.raises(ValueError):
        first_max_window_start([2, 3], 3)


def test_invalid_k_zero_or_negative():
    for bad in (0, -1, -5):
        with pytest.raises(ValueError):
            max_subarray_sum_k([1, 2, 3], bad)
        with pytest.raises(ValueError):
            first_max_window_start([1, 2, 3], bad)


def test_invalid_empty_nums():
    with pytest.raises(ValueError):
        max_subarray_sum_k([], 1)
    with pytest.raises(ValueError):
        first_max_window_start([], 0)


# ---------------------------------------------------------------- safety

def test_does_not_mutate_input():
    nums = [5, -3, 2, 8, -1]
    snapshot = list(nums)
    max_subarray_sum_k(nums, 2)
    first_max_window_start(nums, 2)
    assert nums == snapshot


# ---------------------------------------------------------------- large / random cross-check

def test_large_random_matches_brute_force():
    rng = random.Random(20260524)
    for _ in range(40):
        n = rng.randint(1, 400)
        nums = [rng.randint(-50, 50) for _ in range(n)]
        k = rng.randint(1, n)
        assert max_subarray_sum_k(nums, k) == _brute_max(nums, k)
        assert first_max_window_start(nums, k) == _brute_first_start(nums, k)


def test_large_input_runs():
    # A large array; an O(n*k) re-sum would be ~5e7 ops here but still under the
    # validator's per-test budget. The correctness check is the point.
    nums = list(range(100_000))
    assert max_subarray_sum_k(nums, 100) == sum(range(99_900, 100_000))
    assert first_max_window_start(nums, 100) == 99_900
