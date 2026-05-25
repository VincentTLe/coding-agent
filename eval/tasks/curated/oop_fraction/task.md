# oop_fraction — exact rational number type

## Goal
Implement the `Fraction` class in `fraction.py` (replace every `NotImplementedError`)
so all hidden tests pass. `Fraction` is an immutable rational number always kept
in lowest terms.

Normal form, enforced in `__init__` so every stored value obeys it:
  * Reduce by `gcd(|numerator|, |denominator|)`, so `Fraction(2, 4) == Fraction(1, 2)`.
  * Denominator is always a positive int; any sign lives on the numerator, so
    `Fraction(1, -2)` stores numerator `-1`, denominator `2`.
  * Zero normalizes to numerator `0`, denominator `1`.
  * A zero denominator raises `ZeroDivisionError`.
  * A non-int numerator or denominator raises `TypeError` (note: `bool` is not
    an accepted int here).

Construction: `Fraction(n)` -> `n/1`; `Fraction(n, d)` -> reduced `n/d`.

Read-only attributes via `@property` (no setters): `.numerator` (int),
`.denominator` (int, always > 0).

Implement these dunders:
  * Arithmetic returning a NEW `Fraction` (never mutate `self`): `__add__`,
    `__sub__`, `__mul__`, `__truediv__`, `__neg__`, and `__pow__` for INTEGER
    exponents (negative allowed; negative power of zero raises `ZeroDivisionError`).
    Each binary op also accepts a plain `int` on the right (`Fraction(1, 2) + 1`).
    Division by a fraction whose value is zero raises `ZeroDivisionError`.
  * Reflected operators `__radd__`, `__rsub__`, `__rmul__`, `__rtruediv__` so that
    `1 + Fraction(1, 2)`, `1 - Fraction(1, 4)`, `1 / Fraction(2, 3)` all work.
  * Comparisons on exact value: `__eq__`, `__lt__`, `__le__`, `__gt__`, `__ge__`
    (mixed `int` comparisons too, e.g. `Fraction(4, 2) == 2`). `__eq__` against an
    unrelated type must NOT raise — return `NotImplemented`/`False`.
  * `__hash__` consistent with `__eq__`: equal fractions hash equally, an
    integer-valued fraction hashes like that `int`, and a `Fraction` works as a
    `set`/`dict` key.
  * `__repr__` -> `"Fraction(n, d)"` exactly (e.g. `"Fraction(-1, 2)"`).
  * `__str__` -> `"n/d"`, or just `"n"` when the denominator is 1 (`"2"`, `"-1/2"`).
  * `__bool__` -> `False` iff the value is zero. `__float__` -> the float value.

Examples:
```
Fraction(1, 2) + Fraction(1, 3) == Fraction(5, 6)
Fraction(2, 4) == Fraction(1, 2)
1 - Fraction(1, 4) == Fraction(3, 4)
str(Fraction(6, 3)) == "2"
Fraction(1, 2) ** -1 == Fraction(2, 1)
sorted([Fraction(3, 4), Fraction(1, 4)]) == [Fraction(1, 4), Fraction(3, 4)]
```

## Category
oop

## Difficulty
hard

## Tests
hidden

## Source/License
Authored for coding-agent eval. MIT.
