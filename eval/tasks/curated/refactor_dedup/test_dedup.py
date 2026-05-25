from dedup import dedup, first_unique


def test_dedup_hashable_preserves_first_order():
    assert dedup([3, 1, 3, 2, 1]) == [3, 1, 2]
    assert dedup(["a", "b", "a", "c", "b"]) == ["a", "b", "c"]


def test_dedup_empty():
    assert dedup([]) == []


def test_dedup_all_duplicates():
    assert dedup([7, 7, 7]) == [7]


def test_dedup_unhashable_lists():
    # Lists are unhashable; the naive set-based version raises TypeError here.
    assert dedup([[1], [1], [2], [1]]) == [[1], [2]]


def test_dedup_unhashable_dicts():
    assert dedup([{"a": 1}, {"a": 1}, {"b": 2}]) == [{"a": 1}, {"b": 2}]


def test_dedup_mixed_hashable_and_unhashable():
    data = [1, [2], 1, "x", [2], "x", (3, 4)]
    assert dedup(data) == [1, [2], "x", (3, 4)]


def test_dedup_does_not_mutate_input():
    src = [1, 2, 2, 3]
    _ = dedup(src)
    assert src == [1, 2, 2, 3]


def test_dedup_is_idempotent():
    once = dedup([5, 1, 5, 9, 1])
    assert dedup(once) == once


def test_first_unique_basic():
    assert first_unique([2, 3, 2, 4, 3]) == 4


def test_first_unique_picks_first_not_just_any():
    # Both 'b' and 'c' are unique; the FIRST in order is 'b'.
    assert first_unique(["a", "b", "a", "c"]) == "b"


def test_first_unique_none_when_all_repeat():
    assert first_unique([1, 1, 2, 2]) is None
    assert first_unique([]) is None


def test_first_unique_single():
    assert first_unique([42]) == 42
