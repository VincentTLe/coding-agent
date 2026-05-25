"""Hidden tests for the Polynomial class."""

import pytest

from polynomial import Polynomial


# ------------------------------------------------------------- normalization
def test_strip_trailing_zeros():
    assert Polynomial([1, 2, 0, 0]).coefficients == (1, 2)


def test_already_normalized():
    assert Polynomial([1, 2, 3]).coefficients == (1, 2, 3)


def test_zero_polynomial_is_empty():
    assert Polynomial([]).coefficients == ()
    assert Polynomial([0, 0, 0]).coefficients == ()


def test_degree():
    assert Polynomial([1, 2, 3]).degree == 2
    assert Polynomial([1, 2, 0, 0]).degree == 1
    assert Polynomial([7]).degree == 0


def test_zero_polynomial_degree_is_minus_one():
    assert Polynomial([]).degree == -1
    assert Polynomial([0, 0]).degree == -1


def test_non_numeric_coefficient_raises():
    with pytest.raises(TypeError):
        Polynomial([1, "x", 3])
    with pytest.raises(TypeError):
        Polynomial([1, True])


def test_coefficient_accessor():
    p = Polynomial([1, 2, 3])
    assert p.coefficient(0) == 1
    assert p.coefficient(2) == 3
    assert p.coefficient(5) == 0   # beyond stored range
    assert p.coefficient(-1) == 0  # negative index


# ------------------------------------------------------------- evaluation
def test_call_horner():
    assert Polynomial([1, 2, 3])(2) == 17  # 1 + 4 + 12


def test_call_constant():
    assert Polynomial([5])(123) == 5


def test_call_zero_polynomial():
    assert Polynomial([])(99) == 0


def test_call_negative_and_float_x():
    # 1 + 2x + 3x^2 at x=-1 -> 1 - 2 + 3 = 2
    assert Polynomial([1, 2, 3])(-1) == 2
    assert Polynomial([0, 1])(2.5) == 2.5


# ------------------------------------------------------------- derivative
def test_derivative():
    # d/dx (1 + 2x + 3x^2) = 2 + 6x
    assert Polynomial([1, 2, 3]).derivative() == Polynomial([2, 6])


def test_derivative_of_constant_is_zero():
    assert Polynomial([5]).derivative() == Polynomial([])


def test_derivative_of_zero_is_zero():
    assert Polynomial([]).derivative() == Polynomial([])


def test_derivative_higher_order():
    # d/dx (x^3) = 3x^2  -> coeffs [0,0,3]
    assert Polynomial([0, 0, 0, 1]).derivative() == Polynomial([0, 0, 3])


# ------------------------------------------------------------- add / sub
def test_add_same_length():
    assert Polynomial([1, 2, 3]) + Polynomial([4, 5, 6]) == Polynomial([5, 7, 9])


def test_add_different_length():
    assert Polynomial([1, 2]) + Polynomial([0, 0, 5]) == Polynomial([1, 2, 5])


def test_add_cancels_high_terms():
    # leading terms cancel -> renormalized to lower degree
    s = Polynomial([1, 2, 3]) + Polynomial([0, 0, -3])
    assert s == Polynomial([1, 2])
    assert s.degree == 1


def test_sub():
    assert Polynomial([5, 7, 9]) - Polynomial([4, 5, 6]) == Polynomial([1, 2, 3])


def test_add_scalar():
    assert Polynomial([1, 2]) + 3 == Polynomial([4, 2])


def test_immutable_operands():
    a = Polynomial([1, 2, 3])
    b = Polynomial([1, 1, 1])
    _ = a + b
    assert a.coefficients == (1, 2, 3)
    assert b.coefficients == (1, 1, 1)


# ------------------------------------------------- reflected scalar operators
def test_radd():
    assert 3 + Polynomial([0, 1]) == Polynomial([3, 1])


def test_rsub():
    # 1 - x -> 1 - x  -> coeffs (1, -1)
    assert 1 - Polynomial([0, 1]) == Polynomial([1, -1])


def test_rmul():
    assert 2 * Polynomial([1, 2, 3]) == Polynomial([2, 4, 6])


# ------------------------------------------------------------- multiply
def test_mul_binomials():
    # (1 + x)(1 + x) = 1 + 2x + x^2
    assert Polynomial([1, 1]) * Polynomial([1, 1]) == Polynomial([1, 2, 1])


def test_mul_degrees_add():
    p = Polynomial([1, 0, 1])  # 1 + x^2
    q = Polynomial([0, 1])     # x
    prod = p * q               # x + x^3
    assert prod == Polynomial([0, 1, 0, 1])
    assert prod.degree == 3


def test_mul_by_scalar():
    assert Polynomial([1, 2, 3]) * 2 == Polynomial([2, 4, 6])


def test_mul_by_zero_scalar():
    assert Polynomial([1, 2, 3]) * 0 == Polynomial([])


def test_mul_by_zero_polynomial():
    assert Polynomial([1, 2, 3]) * Polynomial([]) == Polynomial([])
    assert (Polynomial([1, 2, 3]) * Polynomial([])).degree == -1


def test_mul_distributes_over_eval():
    p = Polynomial([1, 2, 3])
    q = Polynomial([2, 1])
    x = 3
    assert (p * q)(x) == p(x) * q(x)


# ------------------------------------------------------------- neg
def test_neg():
    assert -Polynomial([1, -2, 3]) == Polynomial([-1, 2, -3])


def test_sub_via_neg():
    a = Polynomial([1, 2, 3])
    b = Polynomial([1, 1, 1])
    assert a - b == a + (-b)


# ------------------------------------------------------------- equality / hash
def test_eq_int_float():
    assert Polynomial([1, 2]) == Polynomial([1.0, 2.0])


def test_eq_normalization():
    assert Polynomial([1, 2, 0, 0]) == Polynomial([1, 2])


def test_eq_scalar_constant():
    assert Polynomial([5]) == 5
    assert 5 == Polynomial([5])
    assert Polynomial([]) == 0


def test_eq_scalar_nonconstant_false():
    assert (Polynomial([1, 2]) == 1) is False


def test_eq_unrelated_type_false():
    assert (Polynomial([1, 2]) == [1, 2]) is False
    assert (Polynomial([1, 2]) == "x") is False


def test_equal_polynomials_hash_equal():
    assert hash(Polynomial([1, 2, 0, 0])) == hash(Polynomial([1, 2]))
    assert hash(Polynomial([1, 2])) == hash(Polynomial([1.0, 2.0]))


def test_usable_as_set_and_dict():
    s = {Polynomial([1, 2]), Polynomial([1, 2, 0]), Polynomial([1, 3])}
    assert len(s) == 2
    d = {Polynomial([1, 2, 0, 0]): "p"}
    assert d[Polynomial([1, 2])] == "p"


# ------------------------------------------------------------- repr / str
def test_repr():
    assert repr(Polynomial([1, 2, 3])) == "Polynomial([1, 2, 3])"
    assert repr(Polynomial([])) == "Polynomial([])"


def test_str_basic():
    assert str(Polynomial([1, 2, 3])) == "1 + 2x + 3x^2"


def test_str_unit_coefficients():
    assert str(Polynomial([0, 1])) == "x"
    assert str(Polynomial([0, 0, 1])) == "x^2"
    assert str(Polynomial([2, 1])) == "2 + x"


def test_str_skips_zero_terms():
    assert str(Polynomial([1, 0, 3])) == "1 + 3x^2"


def test_str_constant_and_zero():
    assert str(Polynomial([3])) == "3"
    assert str(Polynomial([])) == "0"
