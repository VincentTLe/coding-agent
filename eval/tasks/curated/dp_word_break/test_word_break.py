import random

import pytest

from word_break import word_break


# --- base / classic cases -------------------------------------------------

def test_classic_true():
    assert word_break("leetcode", ["leet", "code"]) is True


def test_classic_reuse():
    assert word_break("applepenapple", ["apple", "pen"]) is True


def test_classic_false():
    assert word_break("catsandog", ["cats", "dog", "sand", "and", "cat"]) is False


# --- empty string / empty dict edges --------------------------------------

def test_empty_string_is_true():
    assert word_break("", ["a", "b"]) is True
    assert word_break("", []) is True


def test_nonempty_string_empty_dict_is_false():
    assert word_break("a", []) is False
    assert word_break("hello", []) is False


# --- single word ----------------------------------------------------------

def test_whole_string_is_a_word():
    assert word_break("apple", ["apple"]) is True
    assert word_break("apple", ["apple", "pen"]) is True


def test_single_char_word():
    assert word_break("a", ["a"]) is True
    assert word_break("a", ["b"]) is False


# --- greedy must NOT be used ----------------------------------------------

def test_greedy_longest_prefix_fails():
    # Greedy takes "cats" then "and" then stuck at "og".
    # Correct answer requires backtracking and is False.
    assert word_break("catsandog", ["cats", "dog", "sand", "and", "cat"]) is False


def test_requires_backtracking_true():
    # "cars": greedy "car" leaves "s" (not a word) -> must try "ca"+"rs".
    assert word_break("cars", ["car", "ca", "rs"]) is True


def test_overlap_choice():
    # "aaaaaaa" (7 a's) = aaa+aaaa or aaaa+aaa -> True.
    assert word_break("aaaaaaa", ["aaa", "aaaa"]) is True
    # 7 a's then a 'b' -> impossible.
    assert word_break("aaaaaaab", ["aaa", "aaaa"]) is False


# --- exact / case sensitivity ---------------------------------------------

def test_case_sensitive():
    assert word_break("Apple", ["apple", "pen"]) is False
    assert word_break("apple", ["Apple"]) is False
    assert word_break("ABc", ["AB", "c"]) is True


def test_no_partial_leftover():
    # "abcd" with only "abc" -> leftover "d", False.
    assert word_break("abcd", ["abc"]) is False
    # extra word at end not present
    assert word_break("abcde", ["abc", "de"]) is True


# --- duplicates in dictionary are harmless --------------------------------

def test_duplicate_words_in_dict():
    assert word_break("aa", ["a", "a", "a"]) is True
    assert word_break("ab", ["a", "a", "b", "b"]) is True


# --- words longer than s --------------------------------------------------

def test_dict_words_longer_than_s():
    assert word_break("ab", ["abc", "abcd"]) is False
    assert word_break("ab", ["ab", "abc"]) is True


# --- return type ----------------------------------------------------------

def test_returns_bool():
    assert isinstance(word_break("leetcode", ["leet", "code"]), bool)
    assert isinstance(word_break("xyz", ["a"]), bool)


# --- inputs not mutated ---------------------------------------------------

def test_inputs_not_mutated():
    s = "applepenapple"
    words = ["apple", "pen"]
    word_break(s, words)
    assert s == "applepenapple"
    assert words == ["apple", "pen"]


# --- cross-check against brute force --------------------------------------

def test_matches_bruteforce_small():
    def brute(s, words):
        wset = set(words)
        n = len(s)
        from functools import lru_cache

        @lru_cache(maxsize=None)
        def can(i):
            if i == n:
                return True
            for j in range(i + 1, n + 1):
                if s[i:j] in wset and can(j):
                    return True
            return False

        return can(0)

    rng = random.Random(321)
    alphabet = "ab"
    for _ in range(80):
        # build a small dictionary of short fragments
        dict_size = rng.randint(0, 5)
        words = list({"".join(rng.choice(alphabet) for _ in range(rng.randint(1, 3)))
                      for _ in range(dict_size)})
        s = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 8)))
        assert word_break(s, words) == brute(s, words)


# --- larger-ish adversarial performance -----------------------------------

def test_adversarial_no_solution_runs_fast():
    # Classic pathological case for un-memoized recursion:
    # many a's followed by a single 'b', with a-only words.
    s = "a" * 120 + "b"
    words = ["a", "aa", "aaa", "aaaa", "aaaaa"]
    assert word_break(s, words) is False


def test_adversarial_solution_runs_fast():
    s = "a" * 150
    words = ["a", "aa", "aaa", "aaaa", "aaaaa"]
    assert word_break(s, words) is True


def test_largeish_mixed():
    # Long string that IS segmentable, with distractor words.
    unit = "thequickbrownfox"
    s = unit * 8
    words = ["the", "quick", "brown", "fox", "lazy", "dog", "th", "equ"]
    assert word_break(s, words) is True
    # break it by appending one stray char
    assert word_break(s + "z", words) is False
