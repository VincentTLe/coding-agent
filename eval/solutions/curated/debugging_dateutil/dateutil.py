"""Small proleptic-Gregorian date utilities (no stdlib datetime).

Functions:
  is_leap_year(y)              -> bool
  days_in_month(y, m)          -> int   (1..12)
  day_of_year(y, m, d)         -> int   (1-based; Jan 1 -> 1)
  days_between(d1, d2)         -> int   (signed: (d2 - d1) in whole days)

Dates are (year, month, day) tuples. days_between counts calendar days, so it
must respect leap years, e.g. days_between((2020,2,28),(2020,3,1)) == 2 because
2020 is a leap year (Feb 29 exists).
"""

_DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def is_leap_year(y: int) -> bool:
    """Gregorian leap-year rule."""
    # Divisible by 4 but not by 100 ... except centuries divisible by 400.
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


def days_in_month(y: int, m: int) -> int:
    """Number of days in month m of year y."""
    if not 1 <= m <= 12:
        raise ValueError("month out of range")
    if m == 2 and is_leap_year(y):
        return 29
    return _DAYS[m - 1]


def day_of_year(y: int, m: int, d: int) -> int:
    """1-based day index within the year (Jan 1 -> 1, Dec 31 -> 365 or 366)."""
    total = d
    for month in range(1, m):
        total += days_in_month(y, month)
    return total


def _to_ordinal(d: tuple[int, int, int]) -> int:
    """Days since an arbitrary fixed epoch (year 0001-01-01 -> 1)."""
    y, m, day = d
    days = 0
    # Whole years before y: count their lengths.
    for year in range(1, y):
        days += 366 if is_leap_year(year) else 365
    days += day_of_year(y, m, day)
    return days


def days_between(d1: tuple[int, int, int], d2: tuple[int, int, int]) -> int:
    """Signed difference d2 - d1 in whole calendar days."""
    return _to_ordinal(d2) - _to_ordinal(d1)
