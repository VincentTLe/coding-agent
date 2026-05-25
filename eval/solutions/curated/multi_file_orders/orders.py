"""Reference solution for orders.py."""

from __future__ import annotations

from inventory import (
    NotEnoughStock,
    UnknownSKU,
    Warehouse,
    normalize_sku,
)


def normalize_order(order: dict) -> dict:
    out: dict[str, int] = {}
    for sku, qty in order.items():
        if isinstance(qty, bool) or not isinstance(qty, int) or qty <= 0:
            raise ValueError(f"quantity for {sku!r} must be a positive int, got {qty!r}")
        key = normalize_sku(sku)
        out[key] = out.get(key, 0) + qty
    return out


def shortfalls(warehouse: Warehouse, order: dict) -> dict:
    norm = normalize_order(order)
    out: dict[str, int] = {}
    for sku, qty in norm.items():
        try:
            avail = warehouse.available(sku)
        except UnknownSKU:
            out[sku] = qty  # unknown SKU is fully short
            continue
        if qty > avail:
            out[sku] = qty - avail
    return out


def can_fulfil(warehouse: Warehouse, order: dict) -> bool:
    return not shortfalls(warehouse, order)


def reserve_order(warehouse: Warehouse, order: dict) -> None:
    norm = normalize_order(order)
    # Pre-check so the operation is all-or-nothing: only reserve if every line
    # can be satisfied. This avoids partially mutating the warehouse.
    missing = shortfalls(warehouse, norm)
    if missing:
        raise NotEnoughStock(f"cannot fulfil order, short on: {missing}")
    for sku, qty in norm.items():
        warehouse.reserve(sku, qty)


def cancel_order(warehouse: Warehouse, order: dict) -> None:
    norm = normalize_order(order)
    for sku, qty in norm.items():
        try:
            warehouse.release(sku, qty)
        except UnknownSKU:
            continue  # releasing something never stocked is a no-op
