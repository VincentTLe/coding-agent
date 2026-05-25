"""Reference solution: immutable single-variable polynomial."""

from __future__ import annotations


def _is_number(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _normalize(coeffs) -> tuple:
    seq = list(coeffs)
    for c in seq:
        if not _is_number(c):
            raise TypeError(f"coefficients must be numbers, got {c!r}")
    # strip trailing (highest-power) zeros
    while seq and seq[-1] == 0:
        seq.pop()
    return tuple(seq)


class Polynomial:
    """Immutable single-variable polynomial, coefficients in ascending powers."""

    __slots__ = ("_c",)

    def __init__(self, coefficients) -> None:
        self._c = _normalize(coefficients)

    @classmethod
    def _from_tuple(cls, t: tuple) -> "Polynomial":
        obj = cls.__new__(cls)
        obj._c = t
        return obj

    @classmethod
    def _coerce(cls, value):
        if isinstance(value, Polynomial):
            return value
        if _is_number(value):
            return cls([value])
        return None

    @property
    def coefficients(self) -> tuple:
        return self._c

    @property
    def degree(self) -> int:
        return len(self._c) - 1

    def coefficient(self, i: int):
        if i < 0 or i >= len(self._c):
            return 0
        return self._c[i]

    def __call__(self, x):
        # Horner's method, evaluating from the highest power down.
        result = 0
        for c in reversed(self._c):
            result = result * x + c
        return result

    def derivative(self) -> "Polynomial":
        if len(self._c) <= 1:
            return Polynomial([])
        return Polynomial([i * self._c[i] for i in range(1, len(self._c))])

    def _add_tuples(self, a: tuple, b: tuple, sign: int) -> "Polynomial":
        n = max(len(a), len(b))
        out = []
        for i in range(n):
            ai = a[i] if i < len(a) else 0
            bi = b[i] if i < len(b) else 0
            out.append(ai + sign * bi)
        return Polynomial(out)

    def __add__(self, other):
        o = self._coerce(other)
        if o is None:
            return NotImplemented
        return self._add_tuples(self._c, o._c, 1)

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        o = self._coerce(other)
        if o is None:
            return NotImplemented
        return self._add_tuples(self._c, o._c, -1)

    def __rsub__(self, other):
        o = self._coerce(other)
        if o is None:
            return NotImplemented
        return o._add_tuples(o._c, self._c, -1)

    def __mul__(self, other):
        o = self._coerce(other)
        if o is None:
            return NotImplemented
        a, b = self._c, o._c
        if not a or not b:
            return Polynomial([])
        out = [0] * (len(a) + len(b) - 1)
        for i, ai in enumerate(a):
            if ai == 0:
                continue
            for j, bj in enumerate(b):
                out[i + j] += ai * bj
        return Polynomial(out)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __neg__(self):
        return Polynomial._from_tuple(tuple(-c for c in self._c))

    def __eq__(self, other) -> bool:
        o = self._coerce(other)
        if o is None:
            return NotImplemented
        return self._c == o._c

    def __hash__(self) -> int:
        return hash(self._c)

    def __repr__(self) -> str:
        return f"Polynomial({list(self._c)!r})"

    def __str__(self) -> str:
        if not self._c:
            return "0"
        terms = []
        for i, c in enumerate(self._c):
            if c == 0:
                continue
            if i == 0:
                terms.append(f"{c}")
            elif i == 1:
                terms.append("x" if c == 1 else f"{c}x")
            else:
                terms.append(f"x^{i}" if c == 1 else f"{c}x^{i}")
        if not terms:
            return "0"
        return " + ".join(terms)
