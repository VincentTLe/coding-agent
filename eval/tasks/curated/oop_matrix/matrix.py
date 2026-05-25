"""A dense 2-D numeric matrix type.

Implement the `Matrix` class so all hidden tests pass. A Matrix wraps a
rectangular grid of numbers (int/float) and supports linear-algebra operators.

Construction:
  Matrix(rows) where `rows` is a non-empty sequence of equal-length non-empty
  sequences of numbers, e.g. Matrix([[1, 2], [3, 4]]). The data is COPIED into an
  internal list-of-lists (mutating the caller's input later must not affect the
  Matrix, and vice versa). Empty input or ragged rows raise ValueError. A cell
  that is not an int/float (bool excluded) raises TypeError.

Class constructors (classmethods):
  Matrix.zeros(r, c)   -> r x c matrix of 0.
  Matrix.identity(n)   -> n x n identity (1 on the diagonal, else 0). n < 1 -> ValueError.

Read-only attributes (@property):
  .rows -> int (number of rows)
  .cols -> int (number of columns)
  .shape -> (rows, cols) tuple

Indexing:
  m[i, j]      -> the value at row i, column j (raises IndexError out of range).
  m[i, j] = v  -> set that cell (value must be int/float; else TypeError). This is
                  the ONLY mutation allowed.
  m[i]         -> a COPY (list) of row i (mutating it must not change the Matrix).

Operators (all arithmetic returns a NEW Matrix, never mutates self):
  __add__, __sub__   : element-wise between two matrices of the SAME shape
                       (shape mismatch raises ValueError).
  __mul__            : if other is a Matrix -> MATRIX product (self.cols must
                       equal other.rows, else ValueError). If other is an
                       int/float -> scalar multiply every element.
  __rmul__           : scalar * Matrix (scalar on the left).
  __pow__            : Matrix ** k for non-negative integer k on a SQUARE matrix
                       (k == 0 -> identity). Non-square or negative/ non-int k
                       raises ValueError / TypeError.
  __neg__            : negate every element.
  transpose()        : return a new Matrix with rows and columns swapped.

Equality & hashing:
  __eq__   : True iff same shape and all corresponding elements equal (1 == 1.0).
             Comparing to a non-Matrix returns False (never raises).
  Matrix is MUTABLE (item assignment), so it is unhashable: __hash__ = None.

Representation:
  __repr__ -> "Matrix([[1, 2], [3, 4]])" (uses the internal rows).

Examples:
  Matrix([[1, 2], [3, 4]]) + Matrix([[5, 6], [7, 8]]) == Matrix([[6, 8], [10, 12]])
  Matrix([[1, 2], [3, 4]]) * Matrix([[5, 6], [7, 8]]) == Matrix([[19, 22], [43, 50]])
  2 * Matrix([[1, 2]]) == Matrix([[2, 4]])
  Matrix([[1, 2], [3, 4]]).transpose() == Matrix([[1, 3], [2, 4]])
  Matrix.identity(2) == Matrix([[1, 0], [0, 1]])
  Matrix([[1, 2], [3, 4]])[1, 0] == 3
"""

from __future__ import annotations


class Matrix:
    """A dense, rectangular matrix of numbers supporting linear-algebra operators."""

    def __init__(self, rows) -> None:
        """Validate and deep-copy `rows` (a sequence of equal-length numeric rows)."""
        raise NotImplementedError

    @classmethod
    def zeros(cls, r: int, c: int) -> "Matrix":
        """Return an r x c matrix filled with 0."""
        raise NotImplementedError

    @classmethod
    def identity(cls, n: int) -> "Matrix":
        """Return the n x n identity matrix."""
        raise NotImplementedError

    @property
    def rows(self) -> int:
        """Number of rows."""
        raise NotImplementedError

    @property
    def cols(self) -> int:
        """Number of columns."""
        raise NotImplementedError

    @property
    def shape(self) -> tuple:
        """(rows, cols)."""
        raise NotImplementedError

    def __getitem__(self, key):
        """m[i, j] -> cell value; m[i] -> a copy of row i."""
        raise NotImplementedError

    def __setitem__(self, key, value) -> None:
        """m[i, j] = value -> set a single cell (the only allowed mutation)."""
        raise NotImplementedError

    def transpose(self) -> "Matrix":
        """Return a new Matrix with rows and columns swapped."""
        raise NotImplementedError

    def __add__(self, other):
        raise NotImplementedError

    def __sub__(self, other):
        raise NotImplementedError

    def __mul__(self, other):
        raise NotImplementedError

    def __rmul__(self, other):
        raise NotImplementedError

    def __pow__(self, power: int):
        raise NotImplementedError

    def __neg__(self):
        raise NotImplementedError

    def __eq__(self, other) -> bool:
        raise NotImplementedError

    __hash__ = None

    def __repr__(self) -> str:
        raise NotImplementedError
