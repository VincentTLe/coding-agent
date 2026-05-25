"""Inventory primitives for the order service (COMPLETE — do not modify).

`orders.py` is implemented against the behaviour here. Read this file: the
distinction between ON-HAND and RESERVED stock, SKU normalisation, and the
exception types are all defined below and must be reused by `orders.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class InventoryError(Exception):
    """Base class for inventory/order errors."""


class UnknownSKU(InventoryError):
    """Raised when a SKU is not stocked by the warehouse."""


class NotEnoughStock(InventoryError):
    """Raised when a reservation exceeds the available quantity."""


def normalize_sku(sku: str) -> str:
    """Canonical SKU form: trimmed and upper-cased.

    '  a-1 ' and 'A-1' refer to the same item. Order code should normalise
    user-supplied SKUs through this function before touching the warehouse.
    """
    return sku.strip().upper()


@dataclass
class Item:
    """A stocked product line.

    ``on_hand`` is the physical quantity present. ``reserved`` is the portion
    of ``on_hand`` already promised to orders but not yet shipped. The amount
    that may be reserved by a NEW order is ``on_hand - reserved``.
    """

    sku: str
    on_hand: int = 0
    reserved: int = 0

    def available(self) -> int:
        return self.on_hand - self.reserved


@dataclass
class Warehouse:
    """A collection of :class:`Item` keyed by normalised SKU."""

    items: dict[str, Item] = field(default_factory=dict)

    def stock(self, sku: str, quantity: int) -> None:
        """Add ``quantity`` units of on-hand stock for ``sku`` (creating it)."""
        key = normalize_sku(sku)
        item = self.items.get(key)
        if item is None:
            item = Item(sku=key)
            self.items[key] = item
        item.on_hand += quantity

    def get(self, sku: str) -> Item:
        """Return the item for ``sku`` or raise ``UnknownSKU``."""
        key = normalize_sku(sku)
        if key not in self.items:
            raise UnknownSKU(key)
        return self.items[key]

    def available(self, sku: str) -> int:
        """Units of ``sku`` that may still be reserved. ``UnknownSKU`` if absent."""
        return self.get(sku).available()

    def reserve(self, sku: str, quantity: int) -> None:
        """Reserve ``quantity`` units (increasing ``reserved``).

        Raises ``UnknownSKU`` if absent, ``NotEnoughStock`` if ``quantity``
        exceeds what is available. ``quantity`` is assumed positive.
        """
        item = self.get(sku)
        if quantity > item.available():
            raise NotEnoughStock(f"{item.sku}: need {quantity}, have {item.available()}")
        item.reserved += quantity

    def release(self, sku: str, quantity: int) -> None:
        """Release ``quantity`` previously-reserved units (decreasing reserved).

        Never lets ``reserved`` drop below 0. Raises ``UnknownSKU`` if absent.
        """
        item = self.get(sku)
        item.reserved = max(0, item.reserved - quantity)
