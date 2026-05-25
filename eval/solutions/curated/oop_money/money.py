"""Reference solution: currency-safe money type backed by integer minor units."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN

_CENTS = Decimal(100)
_QUANT = Decimal("0.01")


def _to_minor(amount) -> int:
    """Convert a major-unit amount (int/float/Decimal) to integer minor units."""
    if isinstance(amount, bool):
        raise TypeError("amount must be a number")
    if isinstance(amount, int):
        dec = Decimal(amount)
    elif isinstance(amount, float):
        # Decimal(str(x)) reflects the human-written decimal, not the binary float.
        dec = Decimal(str(amount))
    elif isinstance(amount, Decimal):
        dec = amount
    else:
        raise TypeError("amount must be a number")
    scaled = dec * _CENTS
    return int(scaled.to_integral_value(rounding=ROUND_HALF_EVEN))


def _norm_currency(currency: str) -> str:
    if not isinstance(currency, str):
        raise ValueError("currency must be a 3-letter string")
    cur = currency.strip().upper()
    if len(cur) != 3 or not cur.isalpha():
        raise ValueError(f"invalid currency code: {currency!r}")
    return cur


class Money:
    """Exact, currency-tagged monetary amount stored as integer minor units."""

    __slots__ = ("_units", "_cur")

    def __init__(self, amount, currency: str) -> None:
        self._cur = _norm_currency(currency)
        self._units = _to_minor(amount)

    @classmethod
    def from_minor(cls, units: int, currency: str) -> "Money":
        if isinstance(units, bool) or not isinstance(units, int):
            raise TypeError("units must be an int")
        obj = cls.__new__(cls)
        obj._cur = _norm_currency(currency)
        obj._units = units
        return obj

    @property
    def currency(self) -> str:
        return self._cur

    @property
    def minor_units(self) -> int:
        return self._units

    @property
    def amount(self) -> Decimal:
        return (Decimal(self._units) / _CENTS).quantize(_QUANT)

    def _same_currency(self, other: "Money") -> None:
        if self._cur != other._cur:
            raise ValueError(
                f"currency mismatch: {self._cur} vs {other._cur}"
            )

    @staticmethod
    def _is_scalar(value) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    def __add__(self, other):
        if not isinstance(other, Money):
            return NotImplemented
        self._same_currency(other)
        return Money.from_minor(self._units + other._units, self._cur)

    def __sub__(self, other):
        if not isinstance(other, Money):
            return NotImplemented
        self._same_currency(other)
        return Money.from_minor(self._units - other._units, self._cur)

    def __mul__(self, other):
        if not self._is_scalar(other):
            return NotImplemented
        scaled = Decimal(self._units) * Decimal(str(other))
        units = int(scaled.to_integral_value(rounding=ROUND_HALF_EVEN))
        return Money.from_minor(units, self._cur)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        if isinstance(other, Money):
            self._same_currency(other)
            if other._units == 0:
                raise ZeroDivisionError("division by zero money")
            return self._units / other._units
        if self._is_scalar(other):
            if other == 0:
                raise ZeroDivisionError("division by zero")
            scaled = Decimal(self._units) / Decimal(str(other))
            units = int(scaled.to_integral_value(rounding=ROUND_HALF_EVEN))
            return Money.from_minor(units, self._cur)
        return NotImplemented

    def __neg__(self):
        return Money.from_minor(-self._units, self._cur)

    def __abs__(self):
        return Money.from_minor(abs(self._units), self._cur)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self._cur == other._cur and self._units == other._units

    def __lt__(self, other) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._same_currency(other)
        return self._units < other._units

    def __le__(self, other) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._same_currency(other)
        return self._units <= other._units

    def __gt__(self, other) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._same_currency(other)
        return self._units > other._units

    def __ge__(self, other) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._same_currency(other)
        return self._units >= other._units

    def __hash__(self) -> int:
        return hash((self._cur, self._units))

    def __bool__(self) -> bool:
        return self._units != 0

    def __repr__(self) -> str:
        return f"Money('{self.amount}', '{self._cur}')"

    def __str__(self) -> str:
        return f"{self.amount} {self._cur}"
