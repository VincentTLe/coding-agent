"""Tests for rpn.py. Currently RED until the planted bugs are fixed."""

import pytest

from rpn import eval_rpn


def test_single_number():
    assert eval_rpn("42") == 42.0
    assert eval_rpn(["3.5"]) == 3.5


def test_commutative_ops():
    assert eval_rpn("3 4 +") == 7.0
    assert eval_rpn("6 7 *") == 42.0


def test_subtraction_order():
    # Earlier operand is the left side: 5 - 1, not 1 - 5.
    assert eval_rpn("5 1 -") == 4.0
    assert eval_rpn("1 5 -") == -4.0


def test_true_division():
    assert eval_rpn("8 2 /") == 4.0
    assert eval_rpn("7 2 /") == 3.5            # true division, not floor
    assert eval_rpn("1 4 /") == 0.25


def test_division_order_and_sign():
    assert eval_rpn("20 5 /") == 4.0
    # -7 / 2 == -3.5 under true division; floor division would give -4.0.
    assert eval_rpn("-7 2 /") == -3.5


def test_nested_expression():
    # (3 + 4) * 2 = 14
    assert eval_rpn("3 4 + 2 *") == 14.0
    # 5 1 2 + 4 * + 3 - = 5 + (1+2)*4 - 3 = 14
    assert eval_rpn("5 1 2 + 4 * + 3 -") == 14.0


def test_list_input():
    assert eval_rpn(["10", "2", "-", "3", "/"]) == pytest.approx(2.6666666, rel=1e-6)


def test_errors():
    with pytest.raises(ValueError):
        eval_rpn("")
    with pytest.raises(ValueError):
        eval_rpn("3 +")            # not enough operands
    with pytest.raises(ValueError):
        eval_rpn("3 4 5 +")        # leftover values
    with pytest.raises(ValueError):
        eval_rpn("3 4 %")          # unknown token
