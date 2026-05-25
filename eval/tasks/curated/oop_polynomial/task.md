# oop_polynomial — single-variable polynomial

## Goal
Implement the `Polynomial` class in `polynomial.py` (replace every
`NotImplementedError`) so all hidden tests pass.

Coefficient convention — ASCENDING powers: `coefficients[i]` is the coefficient
of `x**i`. So `Polynomial([1, 2, 3])` is `1 + 2x + 3x^2`.

Normal form, enforced in `__init__`:
  * Strip trailing (highest-power) zero coefficients, so `Polynomial([1, 2, 0, 0])`
    equals `Polynomial([1, 2])`.
  * The ZERO polynomial is stored as an EMPTY coefficient tuple and has
    `degree == -1`.
  * Store coefficients as an immutable tuple (ints stay ints, floats stay
    floats). A non-numeric coefficient (`bool` excluded) raises `TypeError`.

Read-only / accessors: `.coefficients` (tuple, ascending; empty for zero),
`.degree` (int, `-1` for zero), `coefficient(i)` -> coefficient of `x**i` (`0`
for `i` out of range or negative).

Evaluation & calculus:
  * `__call__(x)` -> `p(x)` via Horner's method (`Polynomial([1, 2, 3])(2) == 17`);
    the zero polynomial evaluates to `0`.
  * `derivative()` -> a new `Polynomial`, the formal derivative; the derivative of
    a constant/zero polynomial is the zero polynomial.

Arithmetic (returns a NEW `Polynomial`, never mutates; results re-normalized):
  * `__add__`, `__sub__` — coefficient-wise; also accept a plain int/float
    (treated as a constant polynomial).
  * `__mul__` — polynomial * polynomial (convolution) or polynomial * scalar;
    multiplying by `0` / the zero polynomial yields the zero polynomial.
  * `__radd__`, `__rsub__`, `__rmul__` — reflected forms so `3 + p`, `1 - p`,
    `2 * p` work. `__neg__` — negate every coefficient.

Equality & hashing:
  * `__eq__` — equal iff normalized coefficient tuples are identical (`1 == 1.0`
    elementwise). A scalar compares equal to the matching constant polynomial
    (`Polynomial([5]) == 5`, `Polynomial([]) == 0`). Comparing to an unrelated
    type returns `False` (never raises).
  * `__hash__` — consistent with `__eq__`; a `Polynomial` may be a `set`/`dict` key.

Representation:
  * `__repr__` -> `"Polynomial([1, 2, 3])"` using normalized coefficients
    (`"Polynomial([])"` for zero).
  * `__str__` -> math form in ASCENDING powers joined by `" + "`. A unit
    coefficient on a power shows as `x` / `x^2` (not `1x`); the constant term
    shows its number; zero terms are skipped; the zero polynomial is `"0"`:
    ```
    str(Polynomial([0, 1]))    == "x"
    str(Polynomial([3]))       == "3"
    str(Polynomial([1, 2, 3])) == "1 + 2x + 3x^2"
    str(Polynomial([0, 0, 1])) == "x^2"
    str(Polynomial([1, 0, 3])) == "1 + 3x^2"
    str(Polynomial([]))        == "0"
    ```

Examples:
```
Polynomial([1, 2, 3])(2) == 17
Polynomial([1, 2]) + Polynomial([0, 0, 5]) == Polynomial([1, 2, 5])
Polynomial([1, 1]) * Polynomial([1, 1]) == Polynomial([1, 2, 1])
Polynomial([1, 2, 3]).derivative() == Polynomial([2, 6])
Polynomial([1, 2, 0, 0]) == Polynomial([1, 2])
```

## Category
oop

## Difficulty
hard

## Tests
hidden

## Source/License
Authored for coding-agent eval. MIT.
