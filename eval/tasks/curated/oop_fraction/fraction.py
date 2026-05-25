"""An immutable, always-reduced rational number type.

Implement the `Fraction` class so all hidden tests pass. The class models an
exact rational number numerator/denominator and must obey the rules below.

Normal form (enforced in __init__, every value is stored this way):
  * The fraction is reduced by the greatest common divisor of |numerator| and
    |denominator|, so Fraction(2, 4) and Fraction(1, 2) are indistinguishable.
  * The denominator is always a positive integer. Any sign lives on the
    numerator, so Fraction(1, -2) stores numerator -1, denominator 2.
  * Zero is normalized to numerator 0, denominator 1.
  * A zero denominator raises ZeroDivisionError.
  * Non-integer numerator/denominator raise TypeError.

Construction:
  Fraction(n)        -> n/1
  Fraction(n, d)     -> n/d (then normalized)

Read-only attributes (use @property, no public setters):
  .numerator   -> int
  .denominator -> int  (always > 0)

Arithmetic (all return a NEW Fraction, never mutate self):
  __add__, __sub__, __mul__, __truediv__   between two Fractions, and also when
  the right operand is a plain int (e.g. Fraction(1, 2) + 1). Division by a
  fraction equal to zero raises ZeroDivisionError.
  __neg__  -> additive inverse.
  __pow__  -> Fraction ** k for INTEGER k (may be negative; negative power of
              zero raises ZeroDivisionError). Returns a Fraction.
  Reflected operators (__radd__, __rsub__, __rmul__, __rtruediv__) so that
  `1 + Fraction(1, 2)` works.

Comparisons (compare exact rational value; mixed int comparisons work too):
  __eq__, __lt__, __le__, __gt__, __ge__   and a consistent __hash__ so that
  equal Fractions hash equally and a Fraction can be a dict/set key. Fractions
  equal to an int (e.g. Fraction(4, 2)) compare equal to that int. __eq__ with
  an unrelated type returns NotImplemented / False rather than raising.

Other:
  __repr__  -> "Fraction(n, d)" exactly (e.g. "Fraction(-1, 2)").
  __str__   -> "n/d", or just "n" when the denominator is 1 (e.g. "3", "-1/2").
  __bool__  -> False iff the value is zero.
  __float__ -> float value of the fraction.

Examples:
  Fraction(1, 2) + Fraction(1, 3) == Fraction(5, 6)
  Fraction(2, 4) == Fraction(1, 2)
  -Fraction(1, 2) == Fraction(-1, 2)
  str(Fraction(6, 3)) == "2"
  Fraction(1, 2) ** -1 == Fraction(2, 1)
  1 - Fraction(1, 4) == Fraction(3, 4)
"""

from __future__ import annotations


class Fraction:
    """Exact rational number kept in lowest terms with a positive denominator."""

    def __init__(self, numerator: int, denominator: int = 1) -> None:
        """Build numerator/denominator, then reduce to normal form (see module docstring)."""
        raise NotImplementedError

    @property
    def numerator(self) -> int:
        """The reduced, signed numerator."""
        raise NotImplementedError

    @property
    def denominator(self) -> int:
        """The reduced denominator (always > 0)."""
        raise NotImplementedError

    def __add__(self, other):
        raise NotImplementedError

    def __radd__(self, other):
        raise NotImplementedError

    def __sub__(self, other):
        raise NotImplementedError

    def __rsub__(self, other):
        raise NotImplementedError

    def __mul__(self, other):
        raise NotImplementedError

    def __rmul__(self, other):
        raise NotImplementedError

    def __truediv__(self, other):
        raise NotImplementedError

    def __rtruediv__(self, other):
        raise NotImplementedError

    def __neg__(self):
        raise NotImplementedError

    def __pow__(self, power: int):
        raise NotImplementedError

    def __eq__(self, other) -> bool:
        raise NotImplementedError

    def __lt__(self, other) -> bool:
        raise NotImplementedError

    def __le__(self, other) -> bool:
        raise NotImplementedError

    def __gt__(self, other) -> bool:
        raise NotImplementedError

    def __ge__(self, other) -> bool:
        raise NotImplementedError

    def __hash__(self) -> int:
        raise NotImplementedError

    def __bool__(self) -> bool:
        raise NotImplementedError

    def __float__(self) -> float:
        raise NotImplementedError

    def __repr__(self) -> str:
        raise NotImplementedError

    def __str__(self) -> str:
        raise NotImplementedError
