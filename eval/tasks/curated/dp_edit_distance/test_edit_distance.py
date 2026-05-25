import random

import pytest

from edit_distance import edit_distance


# --- base / classic cases -------------------------------------------------

def test_classic_kitten_sitting():
    assert edit_distance("kitten", "sitting") == 3


def test_classic_examples():
    assert edit_distance("flaw", "lawn") == 2
    assert edit_distance("sunday", "saturday") == 3
    assert edit_distance("intention", "execution") == 5


# --- edge cases: empty / single -------------------------------------------

def test_both_empty():
    assert edit_distance("", "") == 0


def test_one_empty_equals_length_of_other():
    assert edit_distance("abc", "") == 3
    assert edit_distance("", "abc") == 3
    assert edit_distance("hello", "") == 5
    assert edit_distance("", "x") == 1


def test_identical_strings_zero():
    assert edit_distance("abc", "abc") == 0
    assert edit_distance("a", "a") == 0
    assert edit_distance("a long phrase here", "a long phrase here") == 0


def test_single_char():
    assert edit_distance("a", "b") == 1
    assert edit_distance("a", "a") == 0


# --- structural properties of the metric ----------------------------------

def test_single_operations():
    # one insertion
    assert edit_distance("abc", "abxc") == 1
    # one deletion
    assert edit_distance("abxc", "abc") == 1
    # one substitution (NOT delete+insert)
    assert edit_distance("abc", "abd") == 1


def test_substitution_is_one_edit():
    # If substitution were mishandled as delete+insert, this would be 2.
    assert edit_distance("cat", "bat") == 1
    assert edit_distance("cat", "cut") == 1


def test_symmetry():
    pairs = [
        ("kitten", "sitting"),
        ("flaw", "lawn"),
        ("", "abc"),
        ("abcdef", "azced"),
        ("intention", "execution"),
    ]
    for a, b in pairs:
        assert edit_distance(a, b) == edit_distance(b, a)


def test_case_sensitive():
    assert edit_distance("ABC", "abc") == 3
    assert edit_distance("Hello", "hello") == 1


def test_distance_bounded_by_max_length():
    # distance can never exceed the longer length
    for a, b in [("abc", "xyz"), ("abcd", "x"), ("", "wxyz")]:
        assert edit_distance(a, b) <= max(len(a), len(b))


def test_no_common_chars_equals_max_length():
    # totally disjoint same-length strings -> all substitutions
    assert edit_distance("abc", "xyz") == 3
    assert edit_distance("aaaa", "bbbb") == 4


def test_prefix_relationship():
    # b is a's prefix: distance == number of trailing chars removed
    assert edit_distance("abcdef", "abc") == 3
    assert edit_distance("abc", "abcdef") == 3


# --- triangle inequality (a real metric) ----------------------------------

def test_triangle_inequality():
    strings = ["", "a", "abc", "abx", "xyz", "kitten", "sitting"]
    for x in strings:
        for y in strings:
            for z in strings:
                assert edit_distance(x, z) <= edit_distance(x, y) + edit_distance(y, z)


# --- inputs not mutated ---------------------------------------------------

def test_inputs_not_mutated():
    a, b = "kitten", "sitting"
    edit_distance(a, b)
    assert a == "kitten" and b == "sitting"


# --- larger-ish / performance sanity --------------------------------------

def test_repeated_char_strings():
    assert edit_distance("a" * 50, "a" * 50) == 0
    assert edit_distance("a" * 50, "a" * 40) == 10
    assert edit_distance("a" * 30, "b" * 30) == 30


def test_unicode():
    assert edit_distance("café", "cafe") == 1
    assert edit_distance("naïve", "naive") == 1


def test_largeish_runs_fast():
    # ~300x300 DP table; an exponential solution would not finish.
    rng = random.Random(1234)
    alphabet = "abcd"
    a = "".join(rng.choice(alphabet) for _ in range(300))
    b = "".join(rng.choice(alphabet) for _ in range(300))
    d = edit_distance(a, b)
    assert isinstance(d, int)
    assert 0 <= d <= 300
    # transforming a into itself with a couple known edits
    assert edit_distance(a, a + "zz") == 2


def test_return_type_is_int():
    assert isinstance(edit_distance("abc", "abd"), int)
