"""Tests for rle.py. Currently RED until the planted bugs are fixed."""

from rle import decode, encode


def test_encode_empty():
    assert encode("") == ""


def test_encode_single_char():
    assert encode("a") == "1a"          # the lone final run must still be emitted
    assert encode("z") == "1z"


def test_encode_basic():
    assert encode("aaabbc") == "3a2b1c"
    assert encode("aabb") == "2a2b"


def test_encode_no_repeats():
    assert encode("abc") == "1a1b1c"    # every run is length 1, including the last


def test_encode_multidigit_count():
    assert encode("a" * 12 + "b") == "12a1b"
    assert encode("x" * 100) == "100x"


def test_decode_basic():
    assert decode("") == ""
    assert decode("3a2b1c") == "aaabbc"
    assert decode("1a1b1c") == "abc"


def test_decode_multidigit_count():
    assert decode("12a1b") == "a" * 12 + "b"
    assert decode("100x") == "x" * 100


def test_round_trip():
    for s in ["", "a", "abc", "aaabbc", "x" * 12 + "y" * 3, "mississippi", "a" * 250]:
        assert decode(encode(s)) == s
