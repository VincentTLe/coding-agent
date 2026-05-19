"""Pytest for calculator.py. The `add` tests will fail until the bug is fixed."""

from calculator import add, multiply


def test_add_positive():
    assert add(2, 3) == 5


def test_add_zero():
    assert add(0, 0) == 0


def test_multiply():
    assert multiply(4, 5) == 20
