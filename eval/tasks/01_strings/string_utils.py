"""String utility functions with two intentional bugs."""


def reverse_string(s: str) -> str:
    """Return s reversed. reverse_string('hello') -> 'olleh'."""
    # BUG #1: drops the last character of the reversed string.
    return s[::-1][:-1]


def count_vowels(s: str) -> int:
    """Count vowels (a, e, i, o, u — case-insensitive)."""
    # BUG #2: forgets to handle uppercase vowels.
    return sum(1 for c in s if c in "aeiou")


def is_palindrome(s: str) -> bool:
    """Return True if s is a palindrome (case-insensitive, alpha-only)."""
    cleaned = "".join(c.lower() for c in s if c.isalpha())
    return cleaned == cleaned[::-1]
