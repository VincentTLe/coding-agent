"""An immutable single-variable polynomial with real coefficients.

Implement the `Polynomial` class so all hidden tests pass.

Coefficient convention (ASCENDING powers): the constructor takes coefficients
where index i is the coefficient of x**i. So Polynomial([1, 2, 3]) is the
polynomial 1 + 2*x + 3*x**2.

Normal form (enforced in __init__):
  * Trailing zero coefficients (highest powers) are stripped, so
    Polynomial([1, 2, 0, 0]) and Polynomial([1, 2]) are equal.
  * The ZERO polynomial is stored as an EMPTY coefficient tuple and has
    degree == -1 (by convention).
  * Coefficients are stored as an immutable tuple; ints stay ints, floats stay
    floats. A non-numeric coefficient (bool excluded) raises TypeError.

Read-only:
  .coefficients -> tuple of the normalized coefficients (ascending powers; the
                   empty tuple for the zero polynomial).
  .degree       -> int highest power with a non-zero coefficient (-1 for zero).
  coefficient(i)-> the coefficient of x**i (0 for i beyond the stored length or
                   negative i).

Evaluation:
  __call__(x)   -> the value p(x) computed with Horner's method (so
                   Polynomial([1, 2, 3])(2) == 1 + 2*2 + 3*4 == 17). The zero
                   polynomial evaluates to 0 everywhere.

Calculus:
  derivative()  -> a new Polynomial, the formal derivative (d/dx). The derivative
                   of a constant (or zero) polynomial is the zero polynomial.

Arithmetic (return a NEW Polynomial, never mutate; results re-normalized):
  __add__, __sub__   : add/subtract two polynomials coefficient-wise; also accept
                       a plain int/float (treated as a constant polynomial).
  __mul__            : polynomial * polynomial (convolution) OR polynomial *
                       scalar. Multiplying by 0 / the zero polynomial yields the
                       zero polynomial.
  __rmul__, __radd__, __rsub__ : reflected forms so 2 * p, 3 + p, 1 - p work.
  __neg__            : negate every coefficient.

Equality & hashing:
  __eq__   : equal iff their normalized coefficient tuples are identical
             (1 == 1.0 elementwise, so Polynomial([1, 2]) == Polynomial([1.0, 2.0])).
             A scalar compares equal to the matching constant polynomial
             (Polynomial([5]) == 5; the zero polynomial == 0). Comparing to an
             unrelated type returns False (never raises).
  __hash__ : consistent with __eq__ (equal polynomials hash equally; a Polynomial
             may be a set/dict key).

Representation:
  __repr__ -> "Polynomial([1, 2, 3])" using the normalized coefficients
              ("Polynomial([])" for the zero polynomial).
  __str__  -> human math form in ASCENDING powers joined by " + ", e.g.
              "1 + 2x + 3x^2"; a coefficient of 1 on a power still shows the term
              as "x" / "x^2" (not "1x"); the constant term shows its number.
              The zero polynomial is "0". Examples:
                str(Polynomial([0, 1]))      == "x"
                str(Polynomial([3]))         == "3"
                str(Polynomial([1, 2, 3]))   == "1 + 2x + 3x^2"
                str(Polynomial([0, 0, 1]))   == "x^2"
                str(Polynomial([]))          == "0"

Examples:
  Polynomial([1, 2, 3])(2) == 17
  Polynomial([1, 2]) + Polynomial([0, 0, 5]) == Polynomial([1, 2, 5])
  Polynomial([1, 1]) * Polynomial([1, 1]) == Polynomial([1, 2, 1])
  Polynomial([1, 2, 3]).derivative() == Polynomial([2, 6])
  Polynomial([1, 2, 0, 0]) == Polynomial([1, 2])
"""

from __future__ import annotations


class Polynomial:
    """Immutable single-variable polynomial, coefficients in ascending powers."""

    def __init__(self, coefficients) -> None:
        """Validate coefficients, strip trailing zeros, store an immutable tuple."""
        raise NotImplementedError

    @property
    def coefficients(self) -> tuple:
        """Normalized coefficients (ascending powers); empty tuple for zero."""
        raise NotImplementedError

    @property
    def degree(self) -> int:
        """Highest power with a non-zero coefficient; -1 for the zero polynomial."""
        raise NotImplementedError

    def coefficient(self, i: int):
        """Coefficient of x**i (0 outside the stored range)."""
        raise NotImplementedError

    def __call__(self, x):
        """Evaluate p(x) via Horner's method."""
        raise NotImplementedError

    def derivative(self) -> "Polynomial":
        """Return the formal derivative as a new Polynomial."""
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

    def __neg__(self):
        raise NotImplementedError

    def __eq__(self, other) -> bool:
        raise NotImplementedError

    def __hash__(self) -> int:
        raise NotImplementedError

    def __repr__(self) -> str:
        raise NotImplementedError

    def __str__(self) -> str:
        raise NotImplementedError
