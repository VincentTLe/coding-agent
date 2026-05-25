"""Hidden tests for the Fraction class."""

import pytest

from fraction import Fraction


# ---------------------------------------------------------------- normalization
def test_auto_reduce():
    f = Fraction(2, 4)
    assert (f.numerator, f.denominator) == (1, 2)


def test_reduce_large():
    f = Fraction(100, 250)
    assert (f.numerator, f.denominator) == (2, 5)


def test_sign_moves_to_numerator():
    f = Fraction(1, -2)
    assert (f.numerator, f.denominator) == (-1, 2)


def test_double_negative_is_positive():
    f = Fraction(-3, -6)
    assert (f.numerator, f.denominator) == (1, 2)


def test_negative_numerator_kept():
    f = Fraction(-3, 6)
    assert (f.numerator, f.denominator) == (-1, 2)


def test_zero_normalized():
    f = Fraction(0, 5)
    assert (f.numerator, f.denominator) == (0, 1)


def test_integer_construction_defaults_denominator():
    f = Fraction(7)
    assert (f.numerator, f.denominator) == (7, 1)


def test_already_reduced_unchanged():
    f = Fraction(3, 7)
    assert (f.numerator, f.denominator) == (3, 7)


# ----------------------------------------------------------------- error cases
def test_zero_denominator_raises():
    with pytest.raises(ZeroDivisionError):
        Fraction(1, 0)


def test_non_integer_raises_typeerror():
    with pytest.raises(TypeError):
        Fraction(1.5, 2)
    with pytest.raises(TypeError):
        Fraction(1, 2.0)


def test_division_by_zero_fraction_raises():
    with pytest.raises(ZeroDivisionError):
        Fraction(1, 2) / Fraction(0, 5)


def test_division_by_zero_int_raises():
    with pytest.raises(ZeroDivisionError):
        Fraction(1, 2) / 0


def test_negative_power_of_zero_raises():
    with pytest.raises(ZeroDivisionError):
        Fraction(0, 1) ** -2


# ----------------------------------------------------------------- arithmetic
def test_add():
    assert Fraction(1, 2) + Fraction(1, 3) == Fraction(5, 6)


def test_add_reduces():
    assert Fraction(1, 6) + Fraction(1, 3) == Fraction(1, 2)


def test_sub():
    assert Fraction(3, 4) - Fraction(1, 4) == Fraction(1, 2)


def test_sub_to_negative():
    assert Fraction(1, 4) - Fraction(3, 4) == Fraction(-1, 2)


def test_mul():
    assert Fraction(2, 3) * Fraction(3, 4) == Fraction(1, 2)


def test_truediv():
    assert Fraction(1, 2) / Fraction(3, 4) == Fraction(2, 3)


def test_neg():
    assert -Fraction(1, 2) == Fraction(-1, 2)
    assert -Fraction(-1, 2) == Fraction(1, 2)


def test_results_are_new_objects():
    a = Fraction(1, 2)
    b = Fraction(1, 3)
    c = a + b
    # operands unchanged (immutability)
    assert (a.numerator, a.denominator) == (1, 2)
    assert (b.numerator, b.denominator) == (1, 3)
    assert isinstance(c, Fraction)


def test_pow_positive():
    assert Fraction(2, 3) ** 2 == Fraction(4, 9)


def test_pow_zero():
    assert Fraction(5, 7) ** 0 == Fraction(1, 1)


def test_pow_negative():
    assert Fraction(1, 2) ** -1 == Fraction(2, 1)
    assert Fraction(2, 3) ** -2 == Fraction(9, 4)


# ----------------------------------------------------- mixed int (coercion + reflected)
def test_add_int_right():
    assert Fraction(1, 2) + 1 == Fraction(3, 2)


def test_radd_int_left():
    assert 1 + Fraction(1, 2) == Fraction(3, 2)


def test_rsub_int_left():
    assert 1 - Fraction(1, 4) == Fraction(3, 4)


def test_rmul_int_left():
    assert 3 * Fraction(1, 6) == Fraction(1, 2)


def test_rtruediv_int_left():
    assert 1 / Fraction(2, 3) == Fraction(3, 2)


def test_equal_to_int():
    assert Fraction(4, 2) == 2
    assert 2 == Fraction(4, 2)
    assert Fraction(0, 5) == 0


# ----------------------------------------------------------------- comparisons
def test_lt_gt():
    assert Fraction(1, 3) < Fraction(1, 2)
    assert Fraction(1, 2) > Fraction(1, 3)


def test_le_ge_equal():
    assert Fraction(1, 2) <= Fraction(2, 4)
    assert Fraction(1, 2) >= Fraction(2, 4)


def test_compare_negative():
    assert Fraction(-1, 2) < Fraction(1, 2)
    assert Fraction(-3, 4) < Fraction(-1, 4)


def test_compare_with_int():
    assert Fraction(3, 2) > 1
    assert Fraction(3, 2) < 2
    assert Fraction(5, 1) >= 5


def test_sorting():
    items = [Fraction(3, 4), Fraction(1, 4), Fraction(1, 2), Fraction(-1, 2)]
    ordered = sorted(items)
    assert ordered == [Fraction(-1, 2), Fraction(1, 4), Fraction(1, 2), Fraction(3, 4)]


# ----------------------------------------------------------------- equality/hash
def test_eq_unrelated_type_is_false_not_error():
    assert (Fraction(1, 2) == "1/2") is False
    assert (Fraction(1, 2) != "1/2") is True


def test_equal_fractions_hash_equal():
    assert hash(Fraction(2, 4)) == hash(Fraction(1, 2))


def test_integer_fraction_hashes_like_int():
    assert hash(Fraction(4, 2)) == hash(2)


def test_usable_as_set_members():
    s = {Fraction(1, 2), Fraction(2, 4), Fraction(1, 3)}
    assert len(s) == 2


def test_usable_as_dict_key():
    d = {Fraction(1, 2): "half"}
    assert d[Fraction(2, 4)] == "half"


# ----------------------------------------------------------------- conversions
def test_repr():
    assert repr(Fraction(-1, 2)) == "Fraction(-1, 2)"
    assert repr(Fraction(2, 4)) == "Fraction(1, 2)"
    assert repr(Fraction(3)) == "Fraction(3, 1)"


def test_str_proper():
    assert str(Fraction(-1, 2)) == "-1/2"
    assert str(Fraction(1, 3)) == "1/3"


def test_str_integer_value():
    assert str(Fraction(6, 3)) == "2"
    assert str(Fraction(0, 9)) == "0"


def test_bool():
    assert bool(Fraction(1, 2)) is True
    assert bool(Fraction(0, 5)) is False


def test_float():
    assert float(Fraction(1, 4)) == 0.25
    assert float(Fraction(-3, 2)) == -1.5
