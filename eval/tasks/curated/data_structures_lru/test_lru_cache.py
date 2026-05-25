"""Hidden tests for LRUCache. Exercise recency invariants and edge cases."""

import pytest

from lru_cache import LRUCache


def test_basic_put_get():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    assert c.get("a") == 1
    assert c.get("b") == 2


def test_missing_key_returns_none():
    c = LRUCache(2)
    assert c.get("nope") is None
    c.put("a", 1)
    assert c.get("a") == 1
    assert c.get("b") is None


def test_capacity_must_be_positive():
    with pytest.raises(ValueError):
        LRUCache(0)
    with pytest.raises(ValueError):
        LRUCache(-3)


def test_eviction_of_least_recently_used():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)  # capacity exceeded -> evict "a" (LRU)
    assert c.get("a") is None
    assert c.get("b") == 2
    assert c.get("c") == 3
    assert len(c) == 2


def test_get_refreshes_recency():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    assert c.get("a") == 1  # "a" now MRU, "b" is LRU
    c.put("c", 3)           # evicts "b", not "a"
    assert c.get("b") is None
    assert c.get("a") == 1
    assert c.get("c") == 3


def test_put_existing_key_updates_value_and_recency():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("a", 10)  # overwrite value AND refresh recency -> "b" is LRU
    assert c.get("a") == 10
    c.put("c", 3)   # evicts "b"
    assert c.get("b") is None
    assert c.get("a") == 10
    assert c.get("c") == 3
    assert len(c) == 2


def test_update_does_not_grow_length():
    c = LRUCache(3)
    c.put("a", 1)
    c.put("a", 2)
    c.put("a", 3)
    assert len(c) == 1
    assert c.get("a") == 3


def test_contains_does_not_change_recency():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    # Pure membership query: must NOT count as a use.
    assert ("a" in c) is True
    assert ("b" in c) is True
    assert ("z" in c) is False
    # If `in` (wrongly) refreshed "a", then "b" would be evicted below.
    c.put("c", 3)  # should evict "a" (still the LRU)
    assert ("a" in c) is False
    assert ("b" in c) is True
    assert ("c" in c) is True


def test_len_tracks_size():
    c = LRUCache(3)
    assert len(c) == 0
    c.put("a", 1)
    assert len(c) == 1
    c.put("b", 2)
    c.put("c", 3)
    assert len(c) == 3
    c.put("d", 4)  # eviction keeps length capped at capacity
    assert len(c) == 3


def test_capacity_one():
    c = LRUCache(1)
    c.put("a", 1)
    assert c.get("a") == 1
    c.put("b", 2)  # evicts "a"
    assert c.get("a") is None
    assert c.get("b") == 2
    assert len(c) == 1


def test_falsy_and_none_values_are_stored():
    # 0, "", and None are legitimate values; get must distinguish "stored None"
    # from "absent" only by membership, and falsy values must round-trip.
    c = LRUCache(3)
    c.put("zero", 0)
    c.put("empty", "")
    assert c.get("zero") == 0
    assert c.get("empty") == ""
    assert "zero" in c
    assert "absent" not in c


def test_integer_keys_and_sequence():
    c = LRUCache(3)
    for i in range(5):
        c.put(i, i * i)
    # Keys 0 and 1 should have been evicted (LRU), 2,3,4 remain.
    assert c.get(0) is None
    assert c.get(1) is None
    assert c.get(2) == 4
    assert c.get(3) == 9
    assert c.get(4) == 16


def test_complex_access_pattern():
    c = LRUCache(3)
    c.put(1, 1)
    c.put(2, 2)
    c.put(3, 3)
    assert c.get(1) == 1     # order (LRU->MRU): 2,3,1
    c.put(4, 4)              # evict 2 -> 3,1,4
    assert c.get(2) is None
    assert c.get(3) == 3     # order: 1,4,3
    c.put(5, 5)              # evict 1 -> 4,3,5
    assert c.get(1) is None
    assert c.get(4) == 4     # order: 3,5,4
    c.put(6, 6)              # evict 3 -> 5,4,6
    assert c.get(3) is None
    assert c.get(5) == 5
    assert c.get(6) == 6
    assert len(c) == 3


def test_reinsert_after_eviction():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)        # evict "a"
    assert "a" not in c
    c.put("a", 99)       # reinsert evicts "b" (now LRU)
    assert c.get("a") == 99
    assert c.get("b") is None
    assert c.get("c") == 3
