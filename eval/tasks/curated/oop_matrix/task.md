# oop_matrix — dense 2-D numeric matrix

## Goal
Implement the `Matrix` class in `matrix.py` (replace every `NotImplementedError`)
so all hidden tests pass. A `Matrix` wraps a rectangular grid of numbers
(int/float) and supports linear-algebra operators.

Construction:
  * `Matrix(rows)` where `rows` is a non-empty sequence of equal-length non-empty
    numeric sequences (e.g. `Matrix([[1, 2], [3, 4]])`). The data is COPIED into
    an internal list-of-lists, so later mutating the caller's input must NOT
    affect the Matrix (and vice versa). Empty input or ragged rows raise
    `ValueError`. A non-int/float cell (`bool` excluded) raises `TypeError`.
  * `Matrix.zeros(r, c)` (classmethod) -> `r x c` matrix of `0`.
  * `Matrix.identity(n)` (classmethod) -> `n x n` identity; `n < 1` raises `ValueError`.

Read-only `@property`: `.rows` (int), `.cols` (int), `.shape` (`(rows, cols)`).

Indexing:
  * `m[i, j]` -> cell value (out-of-range raises `IndexError`).
  * `m[i, j] = v` -> set that cell; `v` must be int/float else `TypeError`. This
    is the ONLY mutation allowed.
  * `m[i]` -> a COPY (list) of row `i`, so mutating it must not change the Matrix.

Operators (arithmetic returns a NEW `Matrix`, never mutates `self`):
  * `__add__`, `__sub__` — element-wise between two matrices of the SAME shape
    (mismatch raises `ValueError`).
  * `__mul__` — if `other` is a `Matrix`, the MATRIX product (`self.cols` must
    equal `other.rows`, else `ValueError`); if `other` is int/float, scalar
    multiply. `__rmul__` handles `scalar * Matrix`.
  * `__pow__` — `Matrix ** k` for non-negative integer `k` on a SQUARE matrix
    (`k == 0` -> identity). Non-square or negative `k` raises `ValueError`;
    non-int `k` raises `TypeError`.
  * `__neg__` — negate every element. `transpose()` — return a new Matrix with
    rows and columns swapped.

Equality & hashing:
  * `__eq__` — `True` iff same shape and all corresponding elements equal
    (`1 == 1.0`); comparing to a non-`Matrix` returns `False` (never raises).
  * `Matrix` is mutable, hence unhashable: keep `__hash__ = None`.

`__repr__` -> `"Matrix([[1, 2], [3, 4]])"` (uses the internal rows; should
`eval()`-round-trip).

Examples:
```
Matrix([[1, 2], [3, 4]]) + Matrix([[5, 6], [7, 8]]) == Matrix([[6, 8], [10, 12]])
Matrix([[1, 2], [3, 4]]) * Matrix([[5, 6], [7, 8]]) == Matrix([[19, 22], [43, 50]])
2 * Matrix([[1, 2]]) == Matrix([[2, 4]])
Matrix([[1, 2], [3, 4]]).transpose() == Matrix([[1, 3], [2, 4]])
Matrix.identity(2) == Matrix([[1, 0], [0, 1]])
Matrix([[1, 2], [3, 4]])[1, 0] == 3
```

## Category
oop

## Difficulty
hard

## Tests
hidden

## Source/License
Authored for coding-agent eval. MIT.
