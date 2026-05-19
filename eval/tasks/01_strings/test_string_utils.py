"""Tests for string_utils.py. Several fail until the agent fixes the bugs."""

from string_utils import count_vowels, is_palindrome, reverse_string


def test_reverse_empty():
    assert reverse_string("") == ""


def test_reverse_single():
    assert reverse_string("a") == "a"


def test_reverse_word():
    assert reverse_string("hello") == "olleh"


def test_reverse_sentence():
    assert reverse_string("abc def") == "fed cba"


def test_count_vowels_lowercase():
    assert count_vowels("hello") == 2


def test_count_vowels_uppercase():
    assert count_vowels("HELLO") == 2


def test_count_vowels_mixed_case():
    assert count_vowels("Hello World") == 3


def test_count_vowels_empty():
    assert count_vowels("") == 0


def test_palindrome_true():
    assert is_palindrome("racecar") is True
    assert is_palindrome("A man a plan a canal Panama") is True


def test_palindrome_false():
    assert is_palindrome("hello") is False
