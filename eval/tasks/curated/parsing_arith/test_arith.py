import pytest

from arith import evaluate


# ----------------------------- basic arithmetic ---------------------------

def test_single_number():
    assert evaluate("42") == 42
    assert evaluate("0") == 0


def test_addition_and_subtraction():
    assert evaluate("2+3") == 5
    assert evaluate("10-4") == 6
    assert evaluate("1+2+3+4") == 10


def test_left_associative_subtraction():
    # (10 - 3) - 2 == 5, NOT 10 - (3 - 2) == 9
    assert evaluate("10-3-2") == 5
    assert evaluate("20-5-5-5") == 5


def test_multiplication_and_division():
    assert evaluate("3*4") == 12
    assert evaluate("12/4") == 3
    assert evaluate("2*3*4") == 24


def test_left_associative_division():
    # (16 / 4) / 2 == 2, NOT 16 / (4 / 2) == 8
    assert evaluate("16/4/2") == 2


# ----------------------------- precedence ----------------------------------

def test_precedence_mul_over_add():
    assert evaluate("2+3*4") == 14
    assert evaluate("3*4+2") == 14
    assert evaluate("2+10/2") == 7


def test_precedence_with_subtraction():
    assert evaluate("10-2*3") == 4
    assert evaluate("100-50/5-3") == 87


# ----------------------------- parentheses ---------------------------------

def test_parentheses_change_precedence():
    assert evaluate("(2+3)*4") == 20
    assert evaluate("2*(3+4)") == 14


def test_nested_parentheses():
    assert evaluate("((1+2)*(3+4))") == 21
    assert evaluate("((((5))))") == 5
    assert evaluate("(2*(3+(4-1)))") == 12


def test_deeply_nested_with_precedence():
    assert evaluate("2*(3+4*(5-2))") == 30


# ----------------------------- unary operators -----------------------------

def test_unary_minus():
    assert evaluate("-5") == -5
    assert evaluate("-5+3") == -2
    assert evaluate("3+-5") == -2


def test_unary_plus():
    assert evaluate("+5") == 5
    assert evaluate("+5+3") == 8


def test_stacked_unary():
    assert evaluate("--3") == 3
    assert evaluate("---3") == -3
    assert evaluate("-+-2") == 2


def test_unary_with_parentheses():
    assert evaluate("-(2+3)") == -5
    assert evaluate("-(-(4))") == 4
    assert evaluate("2*-3") == -6


# ----------------------------- whitespace ----------------------------------

def test_whitespace_is_insignificant():
    assert evaluate("  2  +  3  ") == 5
    assert evaluate("\t10 *\n2 ") == 20
    assert evaluate(" ( 1 + 2 ) * 3 ") == 9


# ----------------------------- decimals & result typing --------------------

def test_decimal_numbers():
    assert evaluate("3.5+1.5") == 5
    assert evaluate("0.25*4") == 1
    assert abs(evaluate("1.1+2.2") - 3.3) < 1e-9


def test_division_result_typing():
    # Whole results come back as int; fractional results as float.
    assert evaluate("6/3") == 2
    assert isinstance(evaluate("6/3"), int)
    assert evaluate("6/4") == 1.5
    assert isinstance(evaluate("6/4"), float)


def test_integer_ops_stay_int():
    assert isinstance(evaluate("2+2"), int)
    assert isinstance(evaluate("10-3*2"), int)


def test_float_input_keeps_type_when_fractional():
    assert isinstance(evaluate("2.5"), float)
    assert evaluate("2.5") == 2.5


# ----------------------------- error: empty / blank ------------------------

def test_empty_raises():
    with pytest.raises(ValueError):
        evaluate("")


def test_blank_raises():
    with pytest.raises(ValueError):
        evaluate("   \t\n  ")


# ----------------------------- error: bad characters -----------------------

def test_unknown_character_raises():
    with pytest.raises(ValueError):
        evaluate("2 % 3")
    with pytest.raises(ValueError):
        evaluate("2 + x")
    with pytest.raises(ValueError):
        evaluate("2 ^ 3")


# ----------------------------- error: malformed numbers --------------------

def test_malformed_number_raises():
    with pytest.raises(ValueError):
        evaluate("1.2.3")
    with pytest.raises(ValueError):
        evaluate("1..2")


def test_leading_or_trailing_dot_raises():
    with pytest.raises(ValueError):
        evaluate(".5")
    with pytest.raises(ValueError):
        evaluate("5.")
    with pytest.raises(ValueError):
        evaluate("5.+2")


# ----------------------------- error: unbalanced parens --------------------

def test_missing_closing_paren_raises():
    with pytest.raises(ValueError):
        evaluate("(2+3")
    with pytest.raises(ValueError):
        evaluate("2*(3+4")


def test_extra_closing_paren_raises():
    with pytest.raises(ValueError):
        evaluate("2+3)")
    with pytest.raises(ValueError):
        evaluate("(2+3))")


def test_empty_parens_raise():
    with pytest.raises(ValueError):
        evaluate("()")
    with pytest.raises(ValueError):
        evaluate("2*()")


# ----------------------------- error: missing operands ---------------------

def test_trailing_operator_raises():
    with pytest.raises(ValueError):
        evaluate("1+")
    with pytest.raises(ValueError):
        evaluate("5*")


def test_leading_binary_operator_raises():
    with pytest.raises(ValueError):
        evaluate("*3")
    with pytest.raises(ValueError):
        evaluate("/2")


def test_two_numbers_no_operator_raises():
    with pytest.raises(ValueError):
        evaluate("1 2")
    with pytest.raises(ValueError):
        evaluate("3 (4)")


def test_operator_inside_parens_missing_operand():
    with pytest.raises(ValueError):
        evaluate("(1+)")
    with pytest.raises(ValueError):
        evaluate("(*2)")


def test_double_binary_operator_raises():
    with pytest.raises(ValueError):
        evaluate("2**3")  # '*' then unary nothing -> '*' is not unary
    with pytest.raises(ValueError):
        evaluate("2*/3")


# ----------------------------- error: division by zero ---------------------

def test_division_by_zero_raises():
    with pytest.raises(ValueError):
        evaluate("1/0")
    with pytest.raises(ValueError):
        evaluate("5/(3-3)")
    with pytest.raises(ValueError):
        evaluate("10/0.0")
