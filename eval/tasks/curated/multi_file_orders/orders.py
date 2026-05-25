"""Order-fulfilment service over ``inventory`` (IMPLEMENT THIS FILE).

Each function raises ``NotImplementedError``. Implement them per the docstrings
and ``test_orders.py``. You must READ ``inventory.py`` to use ``Warehouse``
(its ``available`` / ``reserve`` / ``release`` methods), ``normalize_sku``, and
the ``UnknownSKU`` / ``NotEnoughStock`` exceptions.

An "order" is a mapping ``{sku: quantity}``. SKUs supplied by callers are NOT
necessarily normalised — different casings/whitespace of the same SKU refer to
the same item and must be combined.
"""

from __future__ import annotations

from inventory import (
    NotEnoughStock,
    UnknownSKU,
    Warehouse,
    normalize_sku,
)


def normalize_order(order: dict) -> dict:
    """Return a new order with SKUs normalised and duplicate SKUs merged.

    Quantities for SKUs that normalise to the same key are summed. Every
    quantity must be a positive ``int`` (reject ``bool`` and non-ints) — raise
    ``ValueError`` otherwise. An empty order normalises to ``{}``.

    Example: ``{" a-1 ": 2, "A-1": 3, "b": 1}`` -> ``{"A-1": 5, "B": 1}``.
    """
    raise NotImplementedError


def shortfalls(warehouse: Warehouse, order: dict) -> dict:
    """Return ``{sku: missing}`` for lines the warehouse cannot currently meet.

    The order is normalised first. For each line, ``missing`` is how many units
    beyond the available quantity are requested (``requested - available``,
    only when positive). A line whose SKU is unknown counts as fully short
    (its entire requested quantity is missing). Lines that can be met are
    omitted. SKUs in the returned dict are normalised.
    """
    raise NotImplementedError


def can_fulfil(warehouse: Warehouse, order: dict) -> bool:
    """Return True iff every line of the (normalised) order can be reserved now.

    Must NOT mutate the warehouse. Equivalent to ``shortfalls`` being empty.
    """
    raise NotImplementedError


def reserve_order(warehouse: Warehouse, order: dict) -> None:
    """Reserve stock for the whole order, atomically.

    Normalise the order, then reserve every line. If ANY line cannot be fully
    reserved (unknown SKU or not enough stock), reserve NOTHING: the warehouse
    must be left exactly as it was, and a ``NotEnoughStock`` (or ``UnknownSKU``)
    error is raised. On success every line's reservation is applied.
    """
    raise NotImplementedError


def cancel_order(warehouse: Warehouse, order: dict) -> None:
    """Release the reservations previously made for ``order``.

    Normalise the order and release each line's quantity. Unknown SKUs in the
    order are ignored (releasing something never stocked is a no-op).
    """
    raise NotImplementedError
