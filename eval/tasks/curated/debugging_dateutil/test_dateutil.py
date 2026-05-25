"""Tests for dateutil.py. Currently RED until the planted bugs are fixed."""

from dateutil import days_between, days_in_month, day_of_year, is_leap_year


def test_leap_year_basic_rule():
    assert is_leap_year(2020) is True
    assert is_leap_year(2019) is False
    assert is_leap_year(1900) is False   # century not divisible by 400


def test_leap_year_400_exception():
    # The tricky part of the Gregorian rule: 400-divisible centuries ARE leap.
    assert is_leap_year(2000) is True
    assert is_leap_year(1600) is True
    assert is_leap_year(2400) is True


def test_days_in_month_fixed():
    assert days_in_month(2021, 1) == 31
    assert days_in_month(2021, 4) == 30
    assert days_in_month(2021, 9) == 30    # September has 30 days
    assert days_in_month(2021, 12) == 31


def test_days_in_month_february():
    assert days_in_month(2021, 2) == 28
    assert days_in_month(2020, 2) == 29
    assert days_in_month(2000, 2) == 29    # 2000 is a leap year


def test_day_of_year():
    assert day_of_year(2021, 1, 1) == 1
    assert day_of_year(2021, 12, 31) == 365
    assert day_of_year(2020, 12, 31) == 366    # leap year
    assert day_of_year(2021, 10, 1) == 274     # Jan..Sep = 273, +1


def test_days_between_simple():
    assert days_between((2021, 1, 1), (2021, 1, 1)) == 0
    assert days_between((2021, 1, 1), (2021, 1, 2)) == 1
    assert days_between((2021, 1, 2), (2021, 1, 1)) == -1


def test_days_between_across_leap_day():
    assert days_between((2020, 2, 28), (2020, 3, 1)) == 2     # Feb 29 exists
    assert days_between((2021, 2, 28), (2021, 3, 1)) == 1     # no Feb 29


def test_days_between_full_years():
    assert days_between((2020, 1, 1), (2021, 1, 1)) == 366    # 2020 leap
    assert days_between((2021, 1, 1), (2022, 1, 1)) == 365


def test_days_between_spanning_400_century():
    # 1999-01-01 to 2001-01-01 spans the year 2000, which must contribute 366.
    assert days_between((1999, 1, 1), (2001, 1, 1)) == 365 + 366
