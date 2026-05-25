import random
from itertools import combinations

import pytest

from knapsack import knapsack


# --- base / classic cases -------------------------------------------------

def test_classic_capacity_7():
    assert knapsack([1, 3, 4, 5], [1, 4, 5, 7], 7) == 9


def test_classic_small():
    assert knapsack([2, 3, 4], [3, 4, 5], 5) == 7


def test_everything_fits():
    assert knapsack([1, 2, 3], [10, 20, 30], 6) == 60


# --- empty / single / capacity-zero ---------------------------------------

def test_empty_items():
    assert knapsack([], [], 10) == 0
    assert knapsack([], [], 0) == 0


def test_single_item_fits():
    assert knapsack([3], [9], 5) == 9
    assert knapsack([5], [10], 5) == 10


def test_single_item_does_not_fit():
    assert knapsack([5], [10], 4) == 0
    assert knapsack([100], [999], 1) == 0


def test_capacity_zero_only_zero_weight_items():
    assert knapsack([1, 2, 3], [10, 20, 30], 0) == 0
    assert knapsack([0, 0, 2], [5, 7, 3], 0) == 12
    assert knapsack([0], [42], 0) == 42


# --- 0/1 semantics: each item at most once --------------------------------

def test_item_used_at_most_once():
    # If items could be reused (unbounded), 3 copies of (w1,v5) would give 15.
    # 0/1 with one item -> only 5.
    assert knapsack([1], [5], 3) == 5


def test_not_fractional():
    # Fractional knapsack would take part of the heavy high-value item.
    # 0/1: with capacity 3 you cannot take the weight-4 item at all.
    assert knapsack([4, 1, 2], [40, 1, 2], 3) == 3  # take weight 1 + 2 -> value 3


# --- specific reasoning cases ---------------------------------------------

def test_only_light_item_fits():
    assert knapsack([4, 5, 1], [1, 2, 3], 4) == 3


def test_choose_two_lighter_over_one_heavy():
    # weight-2 (v3) + weight-3 (v4) = 7 beats weight-4 (v5) alone within cap 5.
    assert knapsack([2, 3, 4], [3, 4, 5], 5) == 7


def test_high_value_heavy_vs_many_light():
    # capacity 10: either one heavy (w10,v100) or two light (w5,v40 each)=80.
    assert knapsack([10, 5, 5], [100, 40, 40], 10) == 100
    # capacity 10 but heavy is worth less: take the two lights.
    assert knapsack([10, 5, 5], [70, 40, 40], 10) == 80


# --- zero-value / zero-weight handling ------------------------------------

def test_zero_value_items_ignored_effectively():
    assert knapsack([1, 2, 3], [0, 0, 0], 6) == 0


def test_zero_weight_positive_value_always_taken():
    # zero-weight items add value without consuming capacity
    assert knapsack([0, 0, 0], [3, 4, 5], 0) == 12
    assert knapsack([0, 2], [5, 3], 2) == 8


# --- non-negativity / monotonicity ----------------------------------------

def test_never_negative():
    assert knapsack([5, 6, 7], [1, 2, 3], 0) == 0


def test_monotonic_in_capacity():
    w = [3, 4, 5, 8, 2]
    v = [4, 5, 6, 11, 2]
    prev = -1
    for cap in range(0, 25):
        cur = knapsack(w, v, cap)
        assert cur >= prev  # more capacity never reduces optimum
        prev = cur


# --- input not mutated ----------------------------------------------------

def test_inputs_not_mutated():
    w = [1, 3, 4, 5]
    v = [1, 4, 5, 7]
    knapsack(w, v, 7)
    assert w == [1, 3, 4, 5]
    assert v == [1, 4, 5, 7]


# --- return type ----------------------------------------------------------

def test_return_type_is_int():
    assert isinstance(knapsack([1, 3, 4, 5], [1, 4, 5, 7], 7), int)


# --- cross-check against brute force (2**n) for small n -------------------

def test_matches_bruteforce_small():
    def brute(weights, values, capacity):
        n = len(weights)
        best = 0
        idx = range(n)
        for r in range(n + 1):
            for combo in combinations(idx, r):
                w = sum(weights[i] for i in combo)
                if w <= capacity:
                    val = sum(values[i] for i in combo)
                    if val > best:
                        best = val
        return best

    rng = random.Random(99)
    for _ in range(60):
        n = rng.randint(0, 8)
        weights = [rng.randint(0, 10) for _ in range(n)]
        values = [rng.randint(0, 20) for _ in range(n)]
        capacity = rng.randint(0, 25)
        assert knapsack(weights, values, capacity) == brute(weights, values, capacity)


# --- larger-ish performance sanity ----------------------------------------

def test_largeish_runs_fast():
    rng = random.Random(2024)
    n = 200
    weights = [rng.randint(1, 50) for _ in range(n)]
    values = [rng.randint(1, 100) for _ in range(n)]
    capacity = 1000
    result = knapsack(weights, values, capacity)
    assert isinstance(result, int)
    assert 0 <= result <= sum(values)
    # adding capacity cannot decrease the optimum
    assert knapsack(weights, values, capacity + 500) >= result
