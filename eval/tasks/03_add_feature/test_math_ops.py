"""Tests for math_ops.py. Initially only the existing functions are covered.

After the agent adds gcd() and lcm(), the agent should ALSO add tests for
them so the test file ends up covering all 5 functions.
"""

from math_ops import add, multiply, subtract


def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0


def test_subtract():
    assert subtract(10, 3) == 7
    assert subtract(0, 5) == -5


def test_multiply():
    assert multiply(4, 5) == 20
    assert multiply(0, 100) == 0
