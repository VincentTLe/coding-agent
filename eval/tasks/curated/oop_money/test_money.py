"""Hidden tests for the Money class."""

from decimal import Decimal

import pytest

from money import Money


# ------------------------------------------------------------- construction
def test_int_amount_to_minor():
    assert Money(1, "USD").minor_units == 100
    assert Money(0, "USD").minor_units == 0


def test_currency_uppercased():
    assert Money(1, "usd").currency == "USD"
    assert Money(1, "Eur").currency == "EUR"


def test_from_minor_no_rounding():
    m = Money.from_minor(333, "USD")
    assert m.minor_units == 333
    assert m.currency == "USD"


def test_amount_is_decimal_two_places():
    assert Money.from_minor(150, "USD").amount == Decimal("1.50")
    assert Money.from_minor(5, "USD").amount == Decimal("0.05")
    assert Money.from_minor(-205, "EUR").amount == Decimal("-2.05")


def test_invalid_currency_raises():
    with pytest.raises(ValueError):
        Money(1, "US")
    with pytest.raises(ValueError):
        Money(1, "DOLLAR")
    with pytest.raises(ValueError):
        Money(1, "U5D")


def test_from_minor_non_int_raises():
    with pytest.raises(TypeError):
        Money.from_minor(1.5, "USD")


# ------------------------------------------------ banker's rounding (no float drift)
def test_round_half_even_down():
    # 1.005 -> 100.5 cents -> nearest even is 100
    assert Money(1.005, "USD").minor_units == 100
    # 0.125 -> 12.5 cents -> nearest even is 12
    assert Money(0.125, "USD").minor_units == 12


def test_round_half_even_up():
    # 2.675 -> 267.5 cents -> nearest even is 268
    assert Money(2.675, "USD").minor_units == 268
    # 0.135 -> 13.5 cents -> nearest even is 14
    assert Money(0.135, "USD").minor_units == 14


def test_no_binary_float_drift_sum():
    total = Money(0, "USD")
    for _ in range(10):
        total = total + Money(0.1, "USD")
    assert total.minor_units == 100  # exactly 1.00, not 0.9999...


# ------------------------------------------------------------- add / sub
def test_add_same_currency():
    assert Money(1, "USD") + Money(2, "usd") == Money(3, "USD")


def test_sub_same_currency():
    assert Money(5, "USD") - Money(2, "USD") == Money(3, "USD")


def test_sub_to_negative():
    assert (Money(2, "USD") - Money(5, "USD")).minor_units == -300


def test_add_immutable():
    a = Money(1, "USD")
    b = Money(2, "USD")
    _ = a + b
    assert a.minor_units == 100
    assert b.minor_units == 200


def test_add_currency_mismatch_raises():
    with pytest.raises(ValueError):
        Money(1, "USD") + Money(1, "EUR")


def test_sub_currency_mismatch_raises():
    with pytest.raises(ValueError):
        Money(1, "USD") - Money(1, "EUR")


# ------------------------------------------------------------- multiply
def test_mul_scalar_int():
    assert Money(2, "USD") * 3 == Money(6, "USD")


def test_rmul_scalar():
    assert 3 * Money(2, "USD") == Money(6, "USD")


def test_mul_scalar_float_rounds():
    # 1.00 * 2.5 = 2.50
    assert (Money(1, "USD") * 2.5).minor_units == 250
    # 333 cents * 0.5 = 166.5 -> even 166
    assert (Money.from_minor(333, "USD") * 0.5).minor_units == 166


def test_money_times_money_unsupported():
    with pytest.raises(TypeError):
        Money(1, "USD") * Money(1, "USD")


# ------------------------------------------------------------- divide
def test_div_by_scalar_rounds():
    # 10.00 / 3 = 3.333... -> 333 cents
    assert Money(10, "USD") / 3 == Money.from_minor(333, "USD")


def test_div_money_by_money_ratio():
    assert Money(10, "USD") / Money(4, "USD") == 2.5


def test_div_by_zero_scalar_raises():
    with pytest.raises(ZeroDivisionError):
        Money(10, "USD") / 0


def test_div_by_zero_money_raises():
    with pytest.raises(ZeroDivisionError):
        Money(10, "USD") / Money(0, "USD")


def test_div_money_mismatch_raises():
    with pytest.raises(ValueError):
        Money(10, "USD") / Money(2, "EUR")


# ------------------------------------------------------------- sign ops
def test_neg():
    assert -Money(2, "USD") == Money(-2, "USD")


def test_abs():
    assert abs(Money(-2.05, "EUR")) == Money(2.05, "EUR")
    assert abs(Money(3, "USD")) == Money(3, "USD")


# ------------------------------------------------------------- comparisons
def test_lt_le_gt_ge_same_currency():
    assert Money(1, "USD") < Money(2, "USD")
    assert Money(2, "USD") > Money(1, "USD")
    assert Money(2, "USD") <= Money(2, "USD")
    assert Money(2, "USD") >= Money(2, "USD")


def test_compare_currency_mismatch_raises():
    with pytest.raises(ValueError):
        Money(1, "USD") < Money(1, "EUR")
    with pytest.raises(ValueError):
        Money(1, "USD") >= Money(1, "EUR")


def test_eq_currency_mismatch_is_false():
    assert (Money(1, "USD") == Money(1, "EUR")) is False


def test_eq_non_money_is_false():
    assert (Money(1, "USD") == 100) is False
    assert (Money(1, "USD") == "1 USD") is False


def test_sorting_same_currency():
    items = [Money(3, "USD"), Money(1, "USD"), Money(2, "USD")]
    assert sorted(items) == [Money(1, "USD"), Money(2, "USD"), Money(3, "USD")]


# ------------------------------------------------------------- hashing
def test_equal_money_hash_equal():
    assert hash(Money(1, "USD")) == hash(Money.from_minor(100, "USD"))


def test_currency_part_of_hash():
    # different currencies are not equal; their hashes should differ to keep
    # both usable as distinct dict keys
    d = {Money(1, "USD"): "a", Money(1, "EUR"): "b"}
    assert len(d) == 2
    assert d[Money.from_minor(100, "USD")] == "a"


def test_usable_as_set_members():
    s = {Money(1, "USD"), Money.from_minor(100, "USD"), Money(2, "USD")}
    assert len(s) == 2


# ------------------------------------------------------------- repr / str / bool
def test_repr():
    assert repr(Money(1.5, "USD")) == "Money('1.50', 'USD')"
    assert repr(Money(-2.05, "EUR")) == "Money('-2.05', 'EUR')"


def test_str():
    assert str(Money(1.5, "USD")) == "1.50 USD"
    assert str(Money(-2.05, "EUR")) == "-2.05 EUR"
    assert str(Money(0, "USD")) == "0.00 USD"


def test_bool():
    assert bool(Money(1, "USD")) is True
    assert bool(Money(0, "USD")) is False
