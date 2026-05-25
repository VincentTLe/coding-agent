"""Reference solution for the LRUCache task.

Backed by ``collections.OrderedDict``, which preserves insertion order and
supports O(1) ``move_to_end`` and ``popitem``. Order convention: the *first*
item is the least-recently-used, the *last* is the most-recently-used.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Hashable, Optional


class LRUCache:
    def __init__(self, capacity: int) -> None:
        if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity < 1:
            raise ValueError(f"capacity must be a positive integer, got {capacity!r}")
        self._capacity = capacity
        self._store: "OrderedDict[Hashable, Any]" = OrderedDict()

    def get(self, key: Hashable) -> Optional[Any]:
        if key not in self._store:
            return None
        self._store.move_to_end(key)  # mark most-recently-used
        return self._store[key]

    def put(self, key: Hashable, value: Any) -> None:
        if key in self._store:
            self._store[key] = value
            self._store.move_to_end(key)
            return
        self._store[key] = value
        if len(self._store) > self._capacity:
            self._store.popitem(last=False)  # evict least-recently-used

    def __contains__(self, key: Hashable) -> bool:
        return key in self._store  # pure query: does not touch recency

    def __len__(self) -> int:
        return len(self._store)
