# oop_money — currency-safe money type

## Goal
Implement the `Money` class in `money.py` (replace every `NotImplementedError`)
so all hidden tests pass. `Money` is an exact amount in a single currency that
never silently mixes currencies and never loses precision to binary floating
point.

Internal representation:
  * Store the amount as an integer count of MINOR UNITS (cents); 2 minor digits
    per major unit (1 dollar == 100 cents).
  * Currency is an upper-case 3-letter alpha code (str), e.g. `"USD"`, `"EUR"`.

Construction:
  * `Money(amount, currency)` — `amount` is an int or float of MAJOR units,
    converted to minor units with round-half-to-EVEN (banker's rounding) on the
    exact decimal value. Use `Decimal` internally (`Decimal(str(x))` for floats)
    so `Money(1.005, "USD")` -> 100 cents and `Money(2.675, "USD")` -> 268 cents.
    `currency` is normalized to upper case; a non-3-letter or non-alpha code
    raises `ValueError`.
  * `Money.from_minor(units, currency)` (classmethod) — build directly from an
    integer count of minor units, no rounding. Non-int `units` raises `TypeError`.

Read-only `@property` attributes (no setters): `.currency` (upper-case str),
`.minor_units` (signed int), `.amount` (a `Decimal` major value with 2 fractional
digits, e.g. `Decimal('1.50')` for 150 cents).

Currency safety: any binary op mixing two different currencies raises
`ValueError`. Ordering comparisons across currencies also raise `ValueError`;
`__eq__` across currencies returns `False` (never raises).

Implement these dunders (arithmetic returns a NEW `Money`, never mutates):
  * `__add__`, `__sub__` — `Money` +/- `Money` of the SAME currency.
  * `__mul__`, `__rmul__` — `Money` * int|float scalar; the product is rounded
    back to whole minor units with banker's rounding. `Money * Money` is
    unsupported (`TypeError`).
  * `__truediv__` — `Money` / int|float scalar -> `Money` (banker's rounding);
    `Money` / `Money` of the SAME currency -> a `float` ratio. Division by zero
    raises `ZeroDivisionError`.
  * `__neg__`, `__abs__`.
  * `__eq__`, `__lt__`, `__le__`, `__gt__`, `__ge__` (same currency) and a
    `__hash__` consistent with `__eq__` (equal same-currency Money hash equally;
    currency is part of the hash). `__eq__` with a non-`Money` returns `False`.
  * `__repr__` -> `"Money('<amount>', '<CUR>')"` using the 2-decimal major value
    (e.g. `"Money('1.50', 'USD')"`, `"Money('-2.05', 'EUR')"`).
  * `__str__` -> `"<amount> <CUR>"` with always 2 decimals (`"1.50 USD"`).
  * `__bool__` -> `False` iff the amount is zero.

Examples:
```
Money(1, "USD") + Money(2, "usd") == Money(3, "USD")
Money(10, "USD") / 3 == Money.from_minor(333, "USD")
Money(10, "USD") / Money(4, "USD") == 2.5
Money(2.675, "USD").minor_units == 268
str(Money(1.5, "USD")) == "1.50 USD"
Money(1, "USD") + Money(1, "EUR")   # raises ValueError
```

## Category
oop

## Difficulty
hard

## Tests
hidden

## Source/License
Authored for coding-agent eval. MIT.
