import random

import pytest

from coin_change import coin_change


# --- base / classic cases -------------------------------------------------

def test_classic_11_with_1_2_5():
    assert coin_change([1, 2, 5], 11) == 3  # 5 + 5 + 1


def test_classic_impossible():
    assert coin_change([2], 3) == -1


def test_large_classic():
    assert coin_change([186, 419, 83, 408], 6249) == 20


# --- amount == 0 always 0 -------------------------------------------------

def test_zero_amount_is_zero_coins():
    assert coin_change([1, 2, 5], 0) == 0
    assert coin_change([7], 0) == 0


def test_zero_amount_with_empty_coins():
    assert coin_change([], 0) == 0


# --- empty coin list ------------------------------------------------------

def test_empty_coins_positive_amount_impossible():
    assert coin_change([], 7) == -1
    assert coin_change([], 1) == -1


# --- single denomination --------------------------------------------------

def test_single_coin_divisible():
    assert coin_change([1], 5) == 5
    assert coin_change([5], 25) == 5
    assert coin_change([3], 9) == 3


def test_single_coin_not_divisible():
    assert coin_change([3], 7) == -1
    assert coin_change([5], 3) == -1


def test_single_coin_zero():
    assert coin_change([1], 0) == 0


# --- greedy must NOT be used ----------------------------------------------

def test_greedy_fails_here():
    # Greedy (4 + 1 + 1 = 3 coins) is wrong; optimal is 3 + 3 = 2 coins.
    assert coin_change([1, 3, 4], 6) == 2


def test_greedy_fails_25_amount():
    # Greedy picks 20 then 1s; optimal uses 15+15-like combos.
    assert coin_change([1, 15, 20], 30) == 2  # 15 + 15, greedy gives 20+1*10=11


# --- impossible / reachable mixes -----------------------------------------

def test_impossible_all_even_coins_odd_target():
    assert coin_change([2, 4, 6], 7) == -1
    assert coin_change([5, 10], 3) == -1


def test_reachable_mix():
    assert coin_change([2, 5, 10, 1], 27) == 4   # 10 + 10 + 5 + 2
    assert coin_change([1, 2, 5], 7) == 2        # 5 + 2


def test_exact_single_coin_match():
    assert coin_change([7, 11, 13], 13) == 1
    assert coin_change([7, 11, 13], 11) == 1


# --- order independence ---------------------------------------------------

def test_coin_order_does_not_matter():
    assert coin_change([5, 2, 1], 11) == coin_change([1, 2, 5], 11)
    assert coin_change([4, 3, 1], 6) == coin_change([1, 3, 4], 6)


# --- input not mutated ----------------------------------------------------

def test_input_not_mutated():
    coins = [1, 3, 4]
    coin_change(coins, 6)
    assert coins == [1, 3, 4]


# --- return type ----------------------------------------------------------

def test_return_type_is_int():
    assert isinstance(coin_change([1, 2, 5], 11), int)
    assert isinstance(coin_change([2], 3), int)


# --- structural property: count consistency -------------------------------

def test_answer_at_most_all_ones():
    # When 1 is available, the answer is at most `amount`.
    for amt in [1, 7, 23, 100]:
        assert coin_change([1, 5, 10], amt) <= amt


def test_min_is_truly_minimal_small_bruteforce():
    # Cross-check against an independent brute-force for small inputs.
    def brute(coins, amount):
        INF = float("inf")
        best = [0] + [INF] * amount
        for a in range(1, amount + 1):
            for c in coins:
                if c <= a and best[a - c] + 1 < best[a]:
                    best[a] = best[a - c] + 1
        return -1 if best[amount] == INF else best[amount]

    rng = random.Random(7)
    for _ in range(40):
        k = rng.randint(0, 4)
        coins = rng.sample(range(1, 12), k)
        amount = rng.randint(0, 40)
        assert coin_change(coins, amount) == brute(coins, amount)


# --- larger-ish performance sanity ----------------------------------------

def test_largeish_runs_fast():
    # amount in the thousands with several denominations -> needs real DP.
    # 9999 = 25*399 + 24 ; 24 = 10+10+1+1+1+1 (6 coins) -> 399 + 6 = 405.
    assert coin_change([1, 5, 10, 25], 9999) == 405


def test_largeish_impossible_runs_fast():
    # Frobenius-style gaps: small unreachable values for {6, 9, 20}.
    assert coin_change([6, 9, 20], 1) == -1
    assert coin_change([6, 9, 20], 43) == -1
    # ...but plenty of values ARE reachable:
    assert coin_change([6, 9, 20], 26) == 2   # 6 + 20
    assert coin_change([6, 9, 20], 18) == 2   # 9 + 9
