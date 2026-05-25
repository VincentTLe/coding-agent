"""Binary min-heap — implement-from-spec stub.

Replace every ``raise NotImplementedError`` with a working implementation. You
must implement the heap yourself with an array and sift-up / sift-down logic;
do NOT delegate to the ``heapq`` module (the tests assert structural invariants
that your own implementation must maintain).
"""

from __future__ import annotations

from typing import Iterable, List, Optional


class MinHeap:
    """An array-backed binary min-heap of comparable items.

    The heap invariant: for every node at index ``i`` (0-based array), each
    child (at ``2*i+1`` and ``2*i+2``) is greater than or equal to the parent.
    Thus ``peek`` and ``pop_min`` always return a current minimum.

    Duplicates are allowed. Items must be mutually comparable with ``<``.
    """

    def __init__(self, items: Optional[Iterable] = None) -> None:
        """Create a heap, optionally bulk-loading ``items``.

        Bulk-loading must run in O(n) (Floyd's build-heap / heapify), not by
        pushing items one at a time. After construction the heap invariant must
        hold.
        """
        raise NotImplementedError

    def push(self, item) -> None:
        """Insert ``item``, maintaining the heap invariant. O(log n)."""
        raise NotImplementedError

    def pop_min(self):
        """Remove and return the smallest item. O(log n).

        Raises ``IndexError`` if the heap is empty.
        """
        raise NotImplementedError

    def peek(self):
        """Return (without removing) the smallest item. O(1).

        Raises ``IndexError`` if the heap is empty.
        """
        raise NotImplementedError

    def __len__(self) -> int:
        """Number of items currently in the heap."""
        raise NotImplementedError

    def as_sorted(self) -> List:
        """Return all items in ascending order WITHOUT mutating the heap.

        After calling this, the heap must still contain the same items and
        satisfy the heap invariant.
        """
        raise NotImplementedError
