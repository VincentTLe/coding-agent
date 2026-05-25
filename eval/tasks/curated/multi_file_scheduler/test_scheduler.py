"""Tests for scheduler.py. Visible — use them as feedback while implementing."""

import pytest

from events import Conflict, Event, InvalidEvent
from scheduler import Calendar


def cal(*triples):
    c = Calendar()
    for name, s, e in triples:
        c.add(Event(name, s, e))
    return c


# ---- Event sanity (given model) -------------------------------------------

def test_event_validation():
    with pytest.raises(InvalidEvent):
        Event("bad", 10, 10)   # zero length
    with pytest.raises(InvalidEvent):
        Event("bad", 10, 5)    # negative length


def test_event_adjacent_not_overlap():
    a = Event("a", 0, 60)
    b = Event("b", 60, 120)
    assert a.overlaps(b) is False


# ---- conflicts_with --------------------------------------------------------

def test_conflicts_with_empty():
    c = Calendar()
    assert c.conflicts_with(Event("x", 0, 60)) == []


def test_conflicts_with_overlap():
    c = cal(("a", 0, 60), ("b", 120, 180))
    hits = c.conflicts_with(Event("x", 30, 130))
    assert [e.name for e in hits] == ["a", "b"]


def test_conflicts_with_touching_is_not_conflict():
    c = cal(("a", 0, 60))
    assert c.conflicts_with(Event("x", 60, 90)) == []
    assert c.conflicts_with(Event("y", -0 + 60, 120)) == []


def test_conflicts_sorted_by_start():
    c = Calendar()
    c.add(Event("late", 100, 200))
    c.add(Event("early", 0, 50))
    hits = c.conflicts_with(Event("span", 10, 150))
    assert [e.name for e in hits] == ["early", "late"]


# ---- add -------------------------------------------------------------------

def test_add_then_present():
    c = cal(("a", 0, 60))
    assert len(c.events) == 1


def test_add_conflict_raises_and_no_mutation():
    c = cal(("a", 0, 60))
    with pytest.raises(Conflict):
        c.add(Event("b", 30, 90))
    assert len(c.events) == 1  # unchanged


def test_add_adjacent_ok():
    c = cal(("a", 0, 60))
    c.add(Event("b", 60, 120))  # touches, no overlap
    assert len(c.events) == 2


# ---- busy_intervals --------------------------------------------------------

def test_busy_intervals_empty():
    assert Calendar().busy_intervals() == []


def test_busy_intervals_sorted():
    c = cal(("b", 100, 150), ("a", 0, 30))
    assert c.busy_intervals() == [(0, 30), (100, 150)]


def test_busy_intervals_merges_touching():
    c = cal(("a", 0, 30), ("b", 30, 60))
    assert c.busy_intervals() == [(0, 60)]


def test_busy_intervals_merges_overlapping_chain():
    # add non-overlapping pieces, but they form a contiguous block 0..90
    c = cal(("a", 0, 30), ("b", 30, 60), ("c", 60, 90), ("d", 200, 210))
    assert c.busy_intervals() == [(0, 90), (200, 210)]


# ---- is_free ---------------------------------------------------------------

def test_is_free_true_in_gap():
    c = cal(("a", 0, 60), ("b", 120, 180))
    assert c.is_free(60, 120) is True   # exactly the gap (half-open)


def test_is_free_false_on_overlap():
    c = cal(("a", 0, 60))
    assert c.is_free(30, 90) is False


def test_is_free_touching_is_free():
    c = cal(("a", 0, 60))
    assert c.is_free(60, 90) is True


# ---- find_free_slot --------------------------------------------------------

def test_find_free_slot_at_start():
    c = cal(("a", 120, 180))
    assert c.find_free_slot(60) == 0  # [0,60) is free, earliest


def test_find_free_slot_in_gap():
    c = cal(("a", 0, 60), ("b", 120, 180))
    # need 60 mins; [60,120) fits exactly
    assert c.find_free_slot(60, after=0) == 60


def test_find_free_slot_skips_too_small_gap():
    c = cal(("a", 0, 60), ("b", 90, 150))
    # gap [60,90) is only 30 mins; need 60 -> must go after b
    assert c.find_free_slot(60, after=0) == 150


def test_find_free_slot_respects_after():
    c = cal(("a", 0, 60), ("b", 120, 180))
    # earliest free is 60, but we require start >= 70 -> next fit is after b
    assert c.find_free_slot(60, after=70) == 180


def test_find_free_slot_bounded_none():
    c = cal(("a", 0, 60))
    # only window is [0,100); need 60 starting >=0 but [0,60) hits 'a'.
    # next candidate 60 -> [60,120) exceeds until=100 -> None
    assert c.find_free_slot(60, after=0, until=100) is None


def test_find_free_slot_bounded_fits():
    c = cal(("a", 0, 60))
    assert c.find_free_slot(30, after=0, until=100) == 60


def test_find_free_slot_unbounded_after_last():
    c = cal(("a", 0, 60), ("b", 60, 120))
    assert c.find_free_slot(45, after=0) == 120


def test_find_free_slot_invalid_duration():
    c = Calendar()
    with pytest.raises((ValueError, InvalidEvent)):
        c.find_free_slot(0)
