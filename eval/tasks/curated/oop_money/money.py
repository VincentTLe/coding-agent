"""A currency-safe money type backed by integer minor units (cents).

Implement the `Money` class so all hidden tests pass. Money represents an exact
amount in a single currency and must never silently mix currencies or lose
precision to binary floating point.

Internal representation:
  * Store the amount as an integer number of MINOR UNITS (e.g. cents) in an
    attribute. 2 minor digits are assumed (1 dollar == 100 cents).
  * The currency is an uppercase 3-letter code (str), e.g. "USD", "EUR".

Construction:
  Money(amount, currency)
    `amount` may be an int or float number of MAJOR units (dollars). It is
    converted to minor units using round-half-to-even (banker's rounding) on the
    exact value, so Money(1.005, "USD") and Money(2.675, "USD") round correctly
    (to 100 and 268 cents -- not 267). Use Decimal internally to avoid float drift.
    `currency` is normalized to upper case. A non-3-letter / non-alpha currency
    raises ValueError.
  Money.from_minor(units, currency) -> classmethod building directly from an
    integer count of minor units (no rounding). Non-int units raise TypeError.

Read-only attributes (@property, no setters):
  .currency -> str (upper case)
  .minor_units -> int (signed count of cents)
  .amount -> Decimal major-unit value (e.g. Decimal('1.50') for 150 cents)

Currency safety: any binary op mixing two different currencies raises
`ValueError`. Comparisons across currencies (other than __eq__) also raise
`ValueError`; __eq__ across currencies returns False (never raises).

Arithmetic (return NEW Money, never mutate):
  __add__, __sub__   : Money +/- Money of the SAME currency.
  __mul__, __rmul__  : Money * int|float scalar (scales the amount; the product
                       is rounded back to whole minor units with banker's
                       rounding). Money * Money is unsupported (TypeError /
                       NotImplemented).
  __truediv__        : Money / int|float scalar -> Money (banker's rounding);
                       Money / Money of the SAME currency -> a float ratio.
                       Division by zero raises ZeroDivisionError.
  __neg__, __abs__   : sign operations.

Comparisons (same currency): __eq__, __lt__, __le__, __gt__, __ge__ plus a
__hash__ consistent with __eq__ (equal Money values in the same currency hash
equally; the currency is part of the hash). __eq__ with a non-Money returns
False.

Representation:
  __repr__ -> "Money('<amount>', '<CUR>')" using the 2-decimal major value,
              e.g. "Money('1.50', 'USD')", "Money('-2.05', 'EUR')".
  __str__  -> "<amount> <CUR>", e.g. "1.50 USD", "-2.05 EUR" (always 2 decimals).
  __bool__ -> False iff the amount is zero.

Examples:
  Money(1, "USD") + Money(2, "usd") == Money(3, "USD")
  Money(10, "USD") / 3 == Money.from_minor(333, "USD")   # 3.333.. -> 333 cents
  Money(10, "USD") / Money(4, "USD") == 2.5
  Money(2.675, "USD").minor_units == 268
  str(Money(1.5, "USD")) == "1.50 USD"
  Money(1, "USD") + Money(1, "EUR")  -> raises ValueError
"""

from __future__ import annotations


class Money:
    """Exact, currency-tagged monetary amount stored as integer minor units."""

    def __init__(self, amount, currency: str) -> None:
        """Store `amount` major units as integer minor units (banker's rounding); normalize currency."""
        raise NotImplementedError

    @classmethod
    def from_minor(cls, units: int, currency: str) -> "Money":
        """Build a Money directly from an integer count of minor units (no rounding)."""
        raise NotImplementedError

    @property
    def currency(self) -> str:
        """Upper-case 3-letter currency code."""
        raise NotImplementedError

    @property
    def minor_units(self) -> int:
        """Signed integer count of minor units (cents)."""
        raise NotImplementedError

    @property
    def amount(self):
        """Major-unit value as a Decimal with 2 fractional digits."""
        raise NotImplementedError

    def __add__(self, other):
        raise NotImplementedError

    def __sub__(self, other):
        raise NotImplementedError

    def __mul__(self, other):
        raise NotImplementedError

    def __rmul__(self, other):
        raise NotImplementedError

    def __truediv__(self, other):
        raise NotImplementedError

    def __neg__(self):
        raise NotImplementedError

    def __abs__(self):
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

    def __repr__(self) -> str:
        raise NotImplementedError

    def __str__(self) -> str:
        raise NotImplementedError
