"""Hidden tests for Trie. Exercise prefix vs word, delete, pruning, edges."""

import pytest

from trie import Trie


def test_empty_trie():
    t = Trie()
    assert len(t) == 0
    assert t.search("anything") is False
    assert t.starts_with("a") is False
    assert t.starts_with("") is False  # empty trie: no word starts with ""
    assert t.words_with_prefix("") == []


def test_insert_and_search():
    t = Trie()
    t.insert("apple")
    assert t.search("apple") is True
    assert len(t) == 1


def test_prefix_is_not_a_word():
    t = Trie()
    t.insert("apple")
    assert t.search("app") is False     # never inserted as a word
    assert t.search("appl") is False
    assert t.starts_with("app") is True  # but it IS a prefix
    assert t.starts_with("appl") is True
    assert t.starts_with("apple") is True


def test_word_is_prefix_of_itself():
    t = Trie()
    t.insert("cat")
    assert t.starts_with("cat") is True


def test_starts_with_nonexistent():
    t = Trie()
    t.insert("apple")
    assert t.starts_with("b") is False
    assert t.starts_with("apz") is False
    assert t.starts_with("applesauce") is False  # longer than any word


def test_insert_prefix_then_promote_to_word():
    t = Trie()
    t.insert("apple")
    assert t.search("app") is False
    t.insert("app")
    assert t.search("app") is True
    assert t.search("apple") is True
    assert len(t) == 2


def test_idempotent_insert():
    t = Trie()
    t.insert("dog")
    t.insert("dog")
    t.insert("dog")
    assert len(t) == 1
    assert t.search("dog") is True


def test_empty_string_word():
    t = Trie()
    t.insert("")
    assert t.search("") is True
    assert len(t) == 1
    assert t.starts_with("") is True
    # empty string present but no other words
    assert t.search("a") is False
    t.insert("a")
    assert len(t) == 2
    assert t.search("") is True
    assert t.search("a") is True


def test_starts_with_empty_when_nonempty():
    t = Trie()
    t.insert("xyz")
    assert t.starts_with("") is True


def test_multiple_words_shared_prefix():
    t = Trie()
    for w in ["car", "card", "care", "cart", "dog"]:
        t.insert(w)
    assert len(t) == 5
    assert t.search("car") is True
    assert t.search("care") is True
    assert t.search("ca") is False
    assert t.starts_with("car") is True
    assert t.starts_with("ca") is True
    assert t.starts_with("d") is True
    assert t.starts_with("e") is False


def test_delete_returns_bool():
    t = Trie()
    t.insert("hello")
    assert t.delete("hello") is True
    assert t.delete("hello") is False  # already gone
    assert t.delete("never") is False


def test_delete_updates_length_and_search():
    t = Trie()
    t.insert("a")
    t.insert("b")
    assert len(t) == 2
    assert t.delete("a") is True
    assert len(t) == 1
    assert t.search("a") is False
    assert t.search("b") is True


def test_delete_prunes_dangling_prefix():
    t = Trie()
    t.insert("apple")
    assert t.starts_with("app") is True
    assert t.delete("apple") is True
    # No word remains under "app" -> prefix must no longer match.
    assert t.starts_with("app") is False
    assert t.starts_with("a") is False
    assert t.search("apple") is False
    assert len(t) == 0


def test_delete_does_not_break_shared_branch():
    t = Trie()
    t.insert("app")
    t.insert("apple")
    assert t.delete("app") is True
    # "apple" must survive, and its prefixes must still match.
    assert t.search("apple") is True
    assert t.search("app") is False
    assert t.starts_with("app") is True
    assert t.starts_with("appl") is True
    assert len(t) == 1


def test_delete_word_that_is_prefix_keeps_longer_word():
    t = Trie()
    t.insert("test")
    t.insert("testing")
    t.insert("tester")
    assert t.delete("test") is True
    assert t.search("test") is False
    assert t.search("testing") is True
    assert t.search("tester") is True
    assert t.starts_with("test") is True
    assert len(t) == 2


def test_reinsert_after_delete():
    t = Trie()
    t.insert("word")
    assert t.delete("word") is True
    assert t.search("word") is False
    t.insert("word")
    assert t.search("word") is True
    assert len(t) == 1


def test_words_with_prefix_sorted():
    t = Trie()
    for w in ["apple", "app", "application", "apt", "banana"]:
        t.insert(w)
    assert t.words_with_prefix("app") == ["app", "apple", "application"]
    assert t.words_with_prefix("ap") == ["app", "apple", "application", "apt"]
    assert t.words_with_prefix("b") == ["banana"]
    assert t.words_with_prefix("c") == []


def test_words_with_prefix_empty_returns_all_sorted():
    t = Trie()
    for w in ["delta", "alpha", "charlie", "bravo"]:
        t.insert(w)
    assert t.words_with_prefix("") == ["alpha", "bravo", "charlie", "delta"]


def test_words_with_prefix_includes_exact_match():
    t = Trie()
    t.insert("go")
    t.insert("gopher")
    assert t.words_with_prefix("go") == ["go", "gopher"]


def test_case_sensitive():
    t = Trie()
    t.insert("Apple")
    assert t.search("apple") is False
    assert t.search("Apple") is True
    assert t.starts_with("app") is False
    assert t.starts_with("App") is True


def test_unicode_and_digits():
    t = Trie()
    t.insert("café")
    t.insert("caffè")
    t.insert("123")
    assert t.search("café") is True
    assert t.starts_with("caf") is True
    assert t.search("123") is True
    # Lexicographic (codepoint) order: 'caffè' < 'café' since 'f' < 'é'.
    assert t.words_with_prefix("caf") == ["caffè", "café"]
    assert t.words_with_prefix("12") == ["123"]


def test_single_char_words():
    t = Trie()
    for c in "xyz":
        t.insert(c)
    assert len(t) == 3
    assert t.search("x") is True
    assert t.words_with_prefix("") == ["x", "y", "z"]
    assert t.delete("y") is True
    assert t.search("y") is False
    assert t.words_with_prefix("") == ["x", "z"]


def test_large_shared_prefix_set():
    t = Trie()
    words = [f"prefix{i:03d}" for i in range(100)]
    for w in words:
        t.insert(w)
    assert len(t) == 100
    assert t.starts_with("prefix0") is True
    got = t.words_with_prefix("prefix00")
    assert got == [f"prefix00{i}" for i in range(10)]
    assert t.delete("prefix050") is True
    assert t.search("prefix050") is False
    assert len(t) == 99
    assert t.starts_with("prefix05") is True  # prefix051..059 still there
