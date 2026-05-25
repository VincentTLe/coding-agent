"""Tests for roman.py. Currently RED until the planted bugs are fixed."""

import pytest

from roman import from_roman, to_roman


def test_to_roman_basics():
    assert to_roman(1) == "I"
    assert to_roman(2) == "II"
    assert to_roman(3) == "III"
    assert to_roman(5) == "V"
    assert to_roman(10) == "X"


def test_to_roman_subtractive_small():
    assert to_roman(4) == "IV"
    assert to_roman(9) == "IX"
    assert to_roman(40) == "XL"
    assert to_roman(90) == "XC"


def test_to_roman_subtractive_hundreds():
    # These exercise the CD (400) and CM (900) forms.
    assert to_roman(400) == "CD"
    assert to_roman(900) == "CM"
    assert to_roman(444) == "CDXLIV"
    assert to_roman(949) == "CMXLIX"


def test_to_roman_larger():
    assert to_roman(1994) == "MCMXCIV"
    assert to_roman(2024) == "MMXXIV"
    assert to_roman(3888) == "MMMDCCCLXXXVIII"
    assert to_roman(3999) == "MMMCMXCIX"


def test_to_roman_rejects_out_of_range():
    with pytest.raises(ValueError):
        to_roman(0)
    with pytest.raises(ValueError):
        to_roman(4000)


def test_from_roman_basics():
    assert from_roman("I") == 1
    assert from_roman("II") == 2          # equal adjacent symbols must ADD, not subtract
    assert from_roman("III") == 3
    assert from_roman("XX") == 20
    assert from_roman("MMM") == 3000


def test_from_roman_subtractive():
    assert from_roman("IV") == 4
    assert from_roman("IX") == 9
    assert from_roman("XL") == 40
    assert from_roman("CM") == 900
    assert from_roman("MCMXCIV") == 1994


def test_round_trip_all():
    # The two functions must be exact inverses across the whole valid range.
    for n in range(1, 4000):
        assert from_roman(to_roman(n)) == n
