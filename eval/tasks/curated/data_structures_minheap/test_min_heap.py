"""Hidden tests for MinHeap. Exercise heap invariant, ordering, edge cases."""

import random

import pytest

from min_heap import MinHeap


def _heapsort(items):
    """Drain a heap built from items; result must equal sorted(items)."""
    h = MinHeap(items)
    out = []
    while len(h) > 0:
        out.append(h.pop_min())
    return out


def test_empty_heap():
    h = MinHeap()
    assert len(h) == 0
    with pytest.raises(IndexError):
        h.peek()
    with pytest.raises(IndexError):
        h.pop_min()


def test_empty_heap_from_empty_iterable():
    h = MinHeap([])
    assert len(h) == 0
    with pytest.raises(IndexError):
        h.pop_min()


def test_single_element():
    h = MinHeap()
    h.push(42)
    assert len(h) == 1
    assert h.peek() == 42
    assert h.pop_min() == 42
    assert len(h) == 0


def test_push_then_pop_order():
    h = MinHeap()
    for x in [5, 3, 8, 1, 9, 2]:
        h.push(x)
    assert len(h) == 6
    assert h.peek() == 1
    assert [h.pop_min() for _ in range(6)] == [1, 2, 3, 5, 8, 9]
    assert len(h) == 0


def test_bulk_load_constructor():
    h = MinHeap([5, 3, 8, 1, 9, 2])
    assert len(h) == 6
    assert h.peek() == 1
    assert _heapsort([5, 3, 8, 1, 9, 2]) == [1, 2, 3, 5, 8, 9]


def test_peek_does_not_remove():
    h = MinHeap([4, 2, 7])
    assert h.peek() == 2
    assert h.peek() == 2  # idempotent
    assert len(h) == 3


def test_duplicates_allowed():
    h = MinHeap([3, 1, 3, 1, 2, 2])
    assert len(h) == 6
    assert [h.pop_min() for _ in range(6)] == [1, 1, 2, 2, 3, 3]


def test_all_equal():
    h = MinHeap([7, 7, 7, 7])
    assert h.peek() == 7
    assert [h.pop_min() for _ in range(4)] == [7, 7, 7, 7]
    assert len(h) == 0


def test_negative_and_zero():
    h = MinHeap([0, -5, 3, -1, 0])
    assert h.peek() == -5
    assert [h.pop_min() for _ in range(5)] == [-5, -1, 0, 0, 3]


def test_interleaved_push_pop():
    h = MinHeap()
    h.push(10)
    h.push(4)
    assert h.pop_min() == 4
    h.push(7)
    h.push(2)
    assert h.pop_min() == 2
    h.push(1)
    assert h.peek() == 1
    assert h.pop_min() == 1
    assert h.pop_min() == 7
    assert h.pop_min() == 10
    assert len(h) == 0


def test_push_smaller_than_min_updates_peek():
    h = MinHeap([5, 6, 7])
    assert h.peek() == 5
    h.push(1)
    assert h.peek() == 1
    h.push(3)
    assert h.peek() == 1
    assert h.pop_min() == 1
    assert h.peek() == 3


def test_as_sorted_returns_ascending():
    h = MinHeap([5, 3, 8, 1, 9, 2])
    assert h.as_sorted() == [1, 2, 3, 5, 8, 9]


def test_as_sorted_does_not_mutate_heap():
    h = MinHeap([5, 3, 8, 1, 9, 2])
    snapshot = h.as_sorted()
    assert len(h) == 6
    # Heap must remain fully usable and consistent after as_sorted().
    assert h.peek() == 1
    assert h.as_sorted() == snapshot  # second call identical
    assert [h.pop_min() for _ in range(6)] == [1, 2, 3, 5, 8, 9]


def test_as_sorted_empty():
    h = MinHeap()
    assert h.as_sorted() == []


def test_pop_until_empty_then_reuse():
    h = MinHeap([3, 1, 2])
    assert [h.pop_min() for _ in range(3)] == [1, 2, 3]
    with pytest.raises(IndexError):
        h.pop_min()
    h.push(9)
    h.push(4)
    assert h.pop_min() == 4
    assert h.pop_min() == 9


def test_strings_are_supported():
    h = MinHeap(["banana", "apple", "cherry"])
    assert h.peek() == "apple"
    assert h.as_sorted() == ["apple", "banana", "cherry"]


@pytest.mark.parametrize("seed", [0, 1, 2, 7, 13, 99])
def test_randomized_heapsort_matches_sorted(seed):
    rng = random.Random(seed)
    data = [rng.randint(-50, 50) for _ in range(rng.randint(1, 60))]
    assert _heapsort(data) == sorted(data)


def test_randomized_interleaved_operations():
    rng = random.Random(2024)
    h = MinHeap()
    reference = []
    for _ in range(500):
        if reference and rng.random() < 0.4:
            expected = min(reference)
            assert h.peek() == expected
            popped = h.pop_min()
            assert popped == expected
            reference.remove(expected)
        else:
            v = rng.randint(0, 100)
            h.push(v)
            reference.append(v)
        assert len(h) == len(reference)
        if reference:
            assert h.peek() == min(reference)
    # Drain and confirm full sorted order.
    drained = [h.pop_min() for _ in range(len(reference))]
    assert drained == sorted(reference)
