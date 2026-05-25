import random

import pytest

from trapping_rain import trap


def _brute(heights):
    """O(n^2) reference: water over i = min(max left, max right) - h[i] if > 0."""
    n = len(heights)
    total = 0
    for i in range(n):
        left = max(heights[: i + 1])
        right = max(heights[i:])
        water = min(left, right) - heights[i]
        if water > 0:
            total += water
    return total


# ---------------------------------------------------------------- canonical

def test_classic_example():
    assert trap([0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1]) == 6


def test_second_classic_example():
    assert trap([4, 2, 0, 3, 2, 5]) == 9


def test_deep_single_well():
    assert trap([5, 0, 5]) == 5
    assert trap([5, 0, 0, 0, 5]) == 15
    assert trap([3, 0, 2, 0, 4]) == 7


# ---------------------------------------------------------------- empty / tiny

def test_empty():
    assert trap([]) == 0


def test_single_bar():
    assert trap([0]) == 0
    assert trap([7]) == 0


def test_two_bars_never_trap():
    assert trap([5, 5]) == 0
    assert trap([0, 9]) == 0
    assert trap([9, 0]) == 0


# ---------------------------------------------------------------- monotonic / flat

def test_monotonic_increasing_traps_nothing():
    assert trap([1, 2, 3, 4, 5]) == 0


def test_monotonic_decreasing_traps_nothing():
    assert trap([5, 4, 3, 2, 1]) == 0


def test_flat_traps_nothing():
    assert trap([3, 3, 3, 3]) == 0
    assert trap([0, 0, 0]) == 0


# ---------------------------------------------------------------- plateaus / duplicates

def test_plateau_walls():
    # Equal-height walls on both sides of a flat floor.
    assert trap([2, 2, 0, 0, 2, 2]) == 4
    assert trap([4, 1, 1, 1, 4]) == 9


def test_descending_then_ascending():
    assert trap([4, 3, 2, 1, 2, 3, 4]) == 9


# ---------------------------------------------------------------- validation / safety

def test_negative_height_raises():
    with pytest.raises(ValueError):
        trap([1, -1, 2])
    with pytest.raises(ValueError):
        trap([-3])


def test_does_not_mutate_input():
    heights = [0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1]
    snapshot = list(heights)
    trap(heights)
    assert heights == snapshot


# ---------------------------------------------------------------- random oracle / scale

def test_random_matches_brute_force():
    rng = random.Random(524)
    for _ in range(200):
        n = rng.randint(0, 60)
        heights = [rng.randint(0, 20) for _ in range(n)]
        assert trap(heights) == _brute(heights)


def test_large_input():
    # A long sawtooth: peaks of height 100 every other index, valleys of 0.
    # Each interior valley between two height-100 peaks holds 100 units.
    n = 20_001
    heights = [0 if i % 2 == 0 else 100 for i in range(n)]
    # Valleys at even indices 2,4,...,n-3 are bounded by height-100 peaks.
    interior_valleys = (n - 1) // 2 - 1
    assert trap(heights) == interior_valleys * 100
