"""Reference solution: immutable, always-reduced rational number type."""

from __future__ import annotations

from math import gcd


class Fraction:
    """Exact rational number kept in lowest terms with a positive denominator."""

    __slots__ = ("_n", "_d")

    def __init__(self, numerator: int, denominator: int = 1) -> None:
        if isinstance(numerator, bool) or isinstance(denominator, bool):
            raise TypeError("numerator and denominator must be ints")
        if not isinstance(numerator, int) or not isinstance(denominator, int):
            raise TypeError("numerator and denominator must be ints")
        if denominator == 0:
            raise ZeroDivisionError("denominator must be non-zero")
        if denominator < 0:
            numerator, denominator = -numerator, -denominator
        g = gcd(abs(numerator), denominator)
        if g == 0:
            g = 1
        self._n = numerator // g
        self._d = denominator // g

    @property
    def numerator(self) -> int:
        return self._n

    @property
    def denominator(self) -> int:
        return self._d

    @staticmethod
    def _coerce(value):
        if isinstance(value, Fraction):
            return value
        if isinstance(value, int) and not isinstance(value, bool):
            return Fraction(value, 1)
        return None

    def __add__(self, other):
        o = self._coerce(other)
        if o is None:
            return NotImplemented
        return Fraction(self._n * o._d + o._n * self._d, self._d * o._d)

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        o = self._coerce(other)
        if o is None:
            return NotImplemented
        return Fraction(self._n * o._d - o._n * self._d, self._d * o._d)

    def __rsub__(self, other):
        o = self._coerce(other)
        if o is None:
            return NotImplemented
        return o.__sub__(self)

    def __mul__(self, other):
        o = self._coerce(other)
        if o is None:
            return NotImplemented
        return Fraction(self._n * o._n, self._d * o._d)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        o = self._coerce(other)
        if o is None:
            return NotImplemented
        if o._n == 0:
            raise ZeroDivisionError("division by zero fraction")
        return Fraction(self._n * o._d, self._d * o._n)

    def __rtruediv__(self, other):
        o = self._coerce(other)
        if o is None:
            return NotImplemented
        return o.__truediv__(self)

    def __neg__(self):
        return Fraction(-self._n, self._d)

    def __pow__(self, power: int):
        if isinstance(power, bool) or not isinstance(power, int):
            return NotImplemented
        if power >= 0:
            return Fraction(self._n ** power, self._d ** power)
        if self._n == 0:
            raise ZeroDivisionError("negative power of zero")
        k = -power
        return Fraction(self._d ** k, self._n ** k)

    def __eq__(self, other) -> bool:
        o = self._coerce(other)
        if o is None:
            return NotImplemented
        return self._n == o._n and self._d == o._d

    def __lt__(self, other) -> bool:
        o = self._coerce(other)
        if o is None:
            return NotImplemented
        return self._n * o._d < o._n * self._d

    def __le__(self, other) -> bool:
        o = self._coerce(other)
        if o is None:
            return NotImplemented
        return self._n * o._d <= o._n * self._d

    def __gt__(self, other) -> bool:
        o = self._coerce(other)
        if o is None:
            return NotImplemented
        return self._n * o._d > o._n * self._d

    def __ge__(self, other) -> bool:
        o = self._coerce(other)
        if o is None:
            return NotImplemented
        return self._n * o._d >= o._n * self._d

    def __hash__(self) -> int:
        # Equal to the hash of the equivalent int when denominator == 1, so that
        # Fraction(4, 2) and 2 hash alike and behave consistently in sets/dicts.
        if self._d == 1:
            return hash(self._n)
        return hash((self._n, self._d))

    def __bool__(self) -> bool:
        return self._n != 0

    def __float__(self) -> float:
        return self._n / self._d

    def __repr__(self) -> str:
        return f"Fraction({self._n}, {self._d})"

    def __str__(self) -> str:
        if self._d == 1:
            return str(self._n)
        return f"{self._n}/{self._d}"
