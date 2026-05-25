"""Reference solution: dense 2-D numeric matrix type."""

from __future__ import annotations


def _is_number(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


class Matrix:
    """A dense, rectangular matrix of numbers supporting linear-algebra operators."""

    def __init__(self, rows) -> None:
        data = list(rows)
        if not data:
            raise ValueError("matrix must have at least one row")
        width = None
        grid = []
        for row in data:
            row = list(row)
            if width is None:
                width = len(row)
                if width == 0:
                    raise ValueError("matrix rows must be non-empty")
            elif len(row) != width:
                raise ValueError("all rows must have the same length")
            for v in row:
                if not _is_number(v):
                    raise TypeError(f"matrix cells must be numbers, got {v!r}")
            grid.append(row)
        self._data = grid
        self._rows = len(grid)
        self._cols = width

    @classmethod
    def zeros(cls, r: int, c: int) -> "Matrix":
        if r < 1 or c < 1:
            raise ValueError("zeros requires positive dimensions")
        return cls([[0 for _ in range(c)] for _ in range(r)])

    @classmethod
    def identity(cls, n: int) -> "Matrix":
        if n < 1:
            raise ValueError("identity requires n >= 1")
        return cls([[1 if i == j else 0 for j in range(n)] for i in range(n)])

    @property
    def rows(self) -> int:
        return self._rows

    @property
    def cols(self) -> int:
        return self._cols

    @property
    def shape(self) -> tuple:
        return (self._rows, self._cols)

    def _check_index(self, i: int, j: int) -> None:
        if not (0 <= i < self._rows and 0 <= j < self._cols):
            raise IndexError(f"index ({i}, {j}) out of range for {self.shape}")

    def __getitem__(self, key):
        if isinstance(key, tuple):
            if len(key) != 2:
                raise IndexError("matrix index must be (row, col)")
            i, j = key
            self._check_index(i, j)
            return self._data[i][j]
        # single integer -> a *copy* of that row
        if not (0 <= key < self._rows):
            raise IndexError(f"row {key} out of range for {self.shape}")
        return list(self._data[key])

    def __setitem__(self, key, value) -> None:
        if not (isinstance(key, tuple) and len(key) == 2):
            raise TypeError("assignment index must be (row, col)")
        i, j = key
        self._check_index(i, j)
        if not _is_number(value):
            raise TypeError(f"cell value must be a number, got {value!r}")
        self._data[i][j] = value

    def transpose(self) -> "Matrix":
        return Matrix([[self._data[i][j] for i in range(self._rows)]
                       for j in range(self._cols)])

    def __add__(self, other):
        if not isinstance(other, Matrix):
            return NotImplemented
        if self.shape != other.shape:
            raise ValueError(f"shape mismatch for add: {self.shape} vs {other.shape}")
        return Matrix([[self._data[i][j] + other._data[i][j]
                        for j in range(self._cols)] for i in range(self._rows)])

    def __sub__(self, other):
        if not isinstance(other, Matrix):
            return NotImplemented
        if self.shape != other.shape:
            raise ValueError(f"shape mismatch for sub: {self.shape} vs {other.shape}")
        return Matrix([[self._data[i][j] - other._data[i][j]
                        for j in range(self._cols)] for i in range(self._rows)])

    def __mul__(self, other):
        if isinstance(other, Matrix):
            if self._cols != other._rows:
                raise ValueError(
                    f"cannot multiply {self.shape} by {other.shape}"
                )
            out = [[0] * other._cols for _ in range(self._rows)]
            for i in range(self._rows):
                row_i = self._data[i]
                for k in range(self._cols):
                    a = row_i[k]
                    if a == 0:
                        continue
                    other_k = other._data[k]
                    for j in range(other._cols):
                        out[i][j] += a * other_k[j]
            return Matrix(out)
        if _is_number(other):
            return Matrix([[v * other for v in row] for row in self._data])
        return NotImplemented

    def __rmul__(self, other):
        if _is_number(other):
            return Matrix([[other * v for v in row] for row in self._data])
        return NotImplemented

    def __pow__(self, power: int):
        if isinstance(power, bool) or not isinstance(power, int):
            raise TypeError("matrix power must be an integer")
        if self._rows != self._cols:
            raise ValueError("matrix power requires a square matrix")
        if power < 0:
            raise ValueError("negative matrix powers are not supported")
        result = Matrix.identity(self._rows)
        base = self
        # exponentiation by squaring
        while power:
            if power & 1:
                result = result * base
            power >>= 1
            if power:
                base = base * base
        return result

    def __neg__(self):
        return Matrix([[-v for v in row] for row in self._data])

    def __eq__(self, other) -> bool:
        if not isinstance(other, Matrix):
            return NotImplemented
        if self.shape != other.shape:
            return False
        for i in range(self._rows):
            for j in range(self._cols):
                if self._data[i][j] != other._data[i][j]:
                    return False
        return True

    __hash__ = None

    def __repr__(self) -> str:
        return f"Matrix({self._data!r})"
