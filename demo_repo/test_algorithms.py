"""Pytest cases for algorithms.py.

Several tests will fail until the agent fixes the bugs in is_prime
and factorial. The fibonacci tests should pass from the start.
"""

import pytest

from algorithms import factorial, fibonacci, is_prime


# ----- is_prime --------------------------------------------------------------

def test_is_prime_basic():
    assert is_prime(2) is True
    assert is_prime(3) is True
    assert is_prime(5) is True
    assert is_prime(7) is True


def test_is_prime_composite():
    assert is_prime(4) is False
    assert is_prime(9) is False
    assert is_prime(100) is False


def test_is_prime_edge_cases():
    assert is_prime(0) is False
    assert is_prime(1) is False
    assert is_prime(17) is True


# ----- factorial -------------------------------------------------------------

def test_factorial_small():
    assert factorial(0) == 1
    assert factorial(1) == 1
    assert factorial(2) == 2


def test_factorial_larger():
    assert factorial(5) == 120
    assert factorial(7) == 5040


def test_factorial_negative_raises():
    with pytest.raises(ValueError):
        factorial(-1)


# ----- fibonacci (should already pass) --------------------------------------

def test_fibonacci_base_cases():
    assert fibonacci(0) == 0
    assert fibonacci(1) == 1


def test_fibonacci_sequence():
    assert fibonacci(2) == 1
    assert fibonacci(5) == 5
    assert fibonacci(10) == 55
