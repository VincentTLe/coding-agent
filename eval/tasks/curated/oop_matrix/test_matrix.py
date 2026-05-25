"""Hidden tests for the Matrix class."""

import pytest

from matrix import Matrix


# ------------------------------------------------------------- construction
def test_shape_rows_cols():
    m = Matrix([[1, 2, 3], [4, 5, 6]])
    assert m.rows == 2
    assert m.cols == 3
    assert m.shape == (2, 3)


def test_ragged_rows_raise():
    with pytest.raises(ValueError):
        Matrix([[1, 2], [3]])


def test_empty_raises():
    with pytest.raises(ValueError):
        Matrix([])
    with pytest.raises(ValueError):
        Matrix([[]])


def test_non_numeric_cell_raises():
    with pytest.raises(TypeError):
        Matrix([[1, "x"]])
    with pytest.raises(TypeError):
        Matrix([[1, True]])


def test_constructor_copies_input():
    src = [[1, 2], [3, 4]]
    m = Matrix(src)
    src[0][0] = 99
    assert m[0, 0] == 1  # mutating source must not affect the matrix


def test_zeros():
    z = Matrix.zeros(2, 3)
    assert z.shape == (2, 3)
    assert z == Matrix([[0, 0, 0], [0, 0, 0]])


def test_identity():
    assert Matrix.identity(3) == Matrix([[1, 0, 0], [0, 1, 0], [0, 0, 1]])


def test_identity_invalid():
    with pytest.raises(ValueError):
        Matrix.identity(0)


# ------------------------------------------------------------- indexing
def test_getitem_cell():
    m = Matrix([[1, 2], [3, 4]])
    assert m[0, 0] == 1
    assert m[1, 0] == 3
    assert m[1, 1] == 4


def test_getitem_out_of_range():
    m = Matrix([[1, 2], [3, 4]])
    with pytest.raises(IndexError):
        _ = m[2, 0]
    with pytest.raises(IndexError):
        _ = m[0, 5]


def test_getitem_row_is_copy():
    m = Matrix([[1, 2], [3, 4]])
    row = m[0]
    assert row == [1, 2]
    row[0] = 99
    assert m[0, 0] == 1  # returned row is a copy


def test_setitem_cell():
    m = Matrix([[1, 2], [3, 4]])
    m[0, 1] = 20
    assert m[0, 1] == 20


def test_setitem_bad_value_raises():
    m = Matrix([[1, 2], [3, 4]])
    with pytest.raises(TypeError):
        m[0, 0] = "x"


def test_setitem_out_of_range_raises():
    m = Matrix([[1, 2], [3, 4]])
    with pytest.raises(IndexError):
        m[5, 0] = 1


# ------------------------------------------------------------- add / sub
def test_add():
    a = Matrix([[1, 2], [3, 4]])
    b = Matrix([[5, 6], [7, 8]])
    assert a + b == Matrix([[6, 8], [10, 12]])


def test_sub():
    a = Matrix([[5, 6], [7, 8]])
    b = Matrix([[1, 2], [3, 4]])
    assert a - b == Matrix([[4, 4], [4, 4]])


def test_add_shape_mismatch_raises():
    with pytest.raises(ValueError):
        Matrix([[1, 2]]) + Matrix([[1], [2]])


def test_add_is_immutable():
    a = Matrix([[1, 2], [3, 4]])
    b = Matrix([[1, 1], [1, 1]])
    _ = a + b
    assert a == Matrix([[1, 2], [3, 4]])


# ------------------------------------------------------------- multiply
def test_matrix_product_square():
    a = Matrix([[1, 2], [3, 4]])
    b = Matrix([[5, 6], [7, 8]])
    assert a * b == Matrix([[19, 22], [43, 50]])


def test_matrix_product_nonsquare():
    a = Matrix([[1, 2, 3], [4, 5, 6]])     # 2x3
    b = Matrix([[7, 8], [9, 10], [11, 12]])  # 3x2
    assert a * b == Matrix([[58, 64], [139, 154]])


def test_matrix_product_dimension_mismatch():
    with pytest.raises(ValueError):
        Matrix([[1, 2]]) * Matrix([[1, 2]])  # 1x2 * 1x2 invalid


def test_identity_is_multiplicative_unit():
    a = Matrix([[1, 2], [3, 4]])
    assert a * Matrix.identity(2) == a
    assert Matrix.identity(2) * a == a


def test_scalar_mul_right():
    assert Matrix([[1, 2], [3, 4]]) * 2 == Matrix([[2, 4], [6, 8]])


def test_scalar_mul_left():
    assert 3 * Matrix([[1, 2]]) == Matrix([[3, 6]])


# ------------------------------------------------------------- power
def test_pow_zero_is_identity():
    a = Matrix([[2, 0], [0, 3]])
    assert a ** 0 == Matrix.identity(2)


def test_pow_one():
    a = Matrix([[1, 2], [3, 4]])
    assert a ** 1 == a


def test_pow_three():
    a = Matrix([[1, 1], [0, 1]])
    # [[1,1],[0,1]]^3 == [[1,3],[0,1]]
    assert a ** 3 == Matrix([[1, 3], [0, 1]])


def test_pow_nonsquare_raises():
    with pytest.raises(ValueError):
        Matrix([[1, 2, 3]]) ** 2


def test_pow_negative_raises():
    with pytest.raises(ValueError):
        Matrix([[1, 2], [3, 4]]) ** -1


# ------------------------------------------------------------- transpose / neg
def test_transpose():
    assert Matrix([[1, 2, 3], [4, 5, 6]]).transpose() == Matrix([[1, 4], [2, 5], [3, 6]])


def test_transpose_twice_is_identity_op():
    a = Matrix([[1, 2], [3, 4], [5, 6]])
    assert a.transpose().transpose() == a


def test_neg():
    assert -Matrix([[1, -2], [3, 4]]) == Matrix([[-1, 2], [-3, -4]])


# ------------------------------------------------------------- equality / hash
def test_eq_int_float_equal():
    assert Matrix([[1, 2]]) == Matrix([[1.0, 2.0]])


def test_eq_different_shape_false():
    assert (Matrix([[1, 2]]) == Matrix([[1], [2]])) is False


def test_eq_non_matrix_false():
    assert (Matrix([[1, 2]]) == [[1, 2]]) is False
    assert (Matrix([[1, 2]]) == "x") is False


def test_matrix_is_unhashable():
    assert Matrix.__hash__ is None
    with pytest.raises(TypeError):
        {Matrix([[1, 2]])}


# ------------------------------------------------------------- repr
def test_repr_roundtrips():
    m = Matrix([[1, 2], [3, 4]])
    assert repr(m) == "Matrix([[1, 2], [3, 4]])"
    assert eval(repr(m)) == m
