# debugging_dateutil — proleptic-Gregorian date utilities

## Goal
`dateutil.py` implements small calendar helpers without using the stdlib
`datetime` module:

- `is_leap_year(y)` — Gregorian leap-year rule.
- `days_in_month(y, m)` — days in month `m` (1..12) of year `y`.
- `day_of_year(y, m, d)` — 1-based day index in the year (Jan 1 -> 1).
- `days_between(d1, d2)` — signed difference `d2 - d1` in whole calendar days,
  where each date is a `(year, month, day)` tuple.

The suite in `test_dateutil.py` is failing. Run pytest, localize the bug(s),
and fix `dateutil.py` so every test passes. Do not edit the tests. Key cases the
implementation must get right:

- `is_leap_year(2000) is True` and `is_leap_year(1900) is False`.
- September has 30 days; February has 29 in a leap year.
- `days_between((2020, 2, 28), (2020, 3, 1)) == 2` (Feb 29 exists in 2020).
- `days_between((1999, 1, 1), (2001, 1, 1)) == 365 + 366`.

## Category
debugging

## Difficulty
hard

## Tests
visible

## Source/License
Authored for coding-agent eval. MIT.
