"""Tests for orders.py. Visible — use them as feedback while implementing."""

import pytest

from inventory import NotEnoughStock, UnknownSKU, Warehouse
from orders import (
    can_fulfil,
    cancel_order,
    normalize_order,
    reserve_order,
    shortfalls,
)


def make_warehouse():
    w = Warehouse()
    w.stock("A-1", 10)
    w.stock("B-2", 5)
    w.stock("C-3", 0)  # stocked but zero on hand
    return w


# ---- normalize_order -------------------------------------------------------

def test_normalize_merges_and_uppercases():
    assert normalize_order({" a-1 ": 2, "A-1": 3, "b": 1}) == {"A-1": 5, "B": 1}


def test_normalize_empty():
    assert normalize_order({}) == {}


def test_normalize_returns_new_dict():
    src = {"a": 1}
    out = normalize_order(src)
    assert out == {"A": 1}
    assert out is not src


@pytest.mark.parametrize("bad", [0, -2, 1.5, "3", None, True])
def test_normalize_rejects_bad_quantity(bad):
    with pytest.raises(ValueError):
        normalize_order({"a": bad})


# ---- shortfalls ------------------------------------------------------------

def test_shortfalls_none_when_in_stock():
    w = make_warehouse()
    assert shortfalls(w, {"a-1": 10, "B-2": 5}) == {}


def test_shortfalls_partial():
    w = make_warehouse()
    # want 12 of A-1 (have 10) and 5 of B-2 (have 5)
    assert shortfalls(w, {"A-1": 12, "B-2": 5}) == {"A-1": 2}


def test_shortfalls_zero_stock_line():
    w = make_warehouse()
    assert shortfalls(w, {"C-3": 4}) == {"C-3": 4}


def test_shortfalls_unknown_sku_fully_short():
    w = make_warehouse()
    assert shortfalls(w, {"ZZZ": 3}) == {"ZZZ": 3}


def test_shortfalls_merges_duplicate_lines():
    w = make_warehouse()
    # 6 + 6 = 12 of A-1 requested, have 10 -> short 2
    assert shortfalls(w, {"a-1": 6, "A-1": 6}) == {"A-1": 2}


# ---- can_fulfil ------------------------------------------------------------

def test_can_fulfil_true():
    w = make_warehouse()
    assert can_fulfil(w, {"A-1": 10, "B-2": 5}) is True


def test_can_fulfil_false():
    w = make_warehouse()
    assert can_fulfil(w, {"A-1": 11}) is False


def test_can_fulfil_does_not_mutate():
    w = make_warehouse()
    can_fulfil(w, {"A-1": 5})
    assert w.get("A-1").reserved == 0
    assert w.available("A-1") == 10


# ---- reserve_order ---------------------------------------------------------

def test_reserve_applies_all_lines():
    w = make_warehouse()
    reserve_order(w, {"a-1": 4, "B-2": 2})
    assert w.get("A-1").reserved == 4
    assert w.get("B-2").reserved == 2
    assert w.available("A-1") == 6
    assert w.available("B-2") == 3


def test_reserve_reduces_subsequent_availability():
    w = make_warehouse()
    reserve_order(w, {"A-1": 7})
    assert w.available("A-1") == 3
    # a second order for 4 now overshoots
    assert can_fulfil(w, {"A-1": 4}) is False


def test_reserve_atomic_on_shortfall():
    w = make_warehouse()
    with pytest.raises(NotEnoughStock):
        reserve_order(w, {"A-1": 3, "B-2": 99})  # B-2 line fails
    # the A-1 line must NOT have been reserved
    assert w.get("A-1").reserved == 0
    assert w.get("B-2").reserved == 0


def test_reserve_atomic_on_unknown_sku():
    w = make_warehouse()
    with pytest.raises((UnknownSKU, NotEnoughStock)):
        reserve_order(w, {"A-1": 2, "NOPE": 1})
    assert w.get("A-1").reserved == 0


def test_reserve_merged_line_overshoots():
    w = make_warehouse()
    with pytest.raises(NotEnoughStock):
        reserve_order(w, {"a-1": 6, "A-1": 6})  # 12 > 10
    assert w.get("A-1").reserved == 0


# ---- cancel_order ----------------------------------------------------------

def test_cancel_releases_reservation():
    w = make_warehouse()
    reserve_order(w, {"A-1": 4})
    cancel_order(w, {"a-1": 4})
    assert w.get("A-1").reserved == 0
    assert w.available("A-1") == 10


def test_cancel_partial():
    w = make_warehouse()
    reserve_order(w, {"A-1": 6})
    cancel_order(w, {"A-1": 2})
    assert w.get("A-1").reserved == 4
    assert w.available("A-1") == 6


def test_cancel_unknown_sku_is_noop():
    w = make_warehouse()
    # should not raise
    cancel_order(w, {"GHOST": 5})
    assert "GHOST" not in {k for k in w.items}


def test_reserve_then_cancel_roundtrip():
    w = make_warehouse()
    order = {"A-1": 3, "B-2": 2}
    reserve_order(w, order)
    cancel_order(w, order)
    assert w.available("A-1") == 10
    assert w.available("B-2") == 5
