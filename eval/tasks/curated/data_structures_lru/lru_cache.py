"""LRU (Least Recently Used) cache — implement-from-spec stub.

Replace every ``raise NotImplementedError`` with a working implementation that
satisfies the behavioural contract documented on each method and in task.md.
"""

from __future__ import annotations

from typing import Any, Hashable, Optional


class LRUCache:
    """A fixed-capacity cache that evicts the least-recently-used entry.

    Recency is defined by access: both ``get`` (on a hit) and ``put`` count as
    "using" a key, moving it to the most-recently-used position. When inserting
    a new key would exceed ``capacity``, the least-recently-used key is evicted
    first.

    All operations (``get``, ``put``, ``__contains__``, ``__len__``) must run in
    O(1) average time.
    """

    def __init__(self, capacity: int) -> None:
        """Create a cache holding at most ``capacity`` keys.

        Args:
            capacity: maximum number of entries. Must be a positive integer;
                a capacity < 1 must raise ``ValueError``.
        """
        raise NotImplementedError

    def get(self, key: Hashable) -> Optional[Any]:
        """Return the value for ``key`` and mark it most-recently-used.

        Returns ``None`` if the key is absent. A successful lookup counts as a
        use and updates recency.
        """
        raise NotImplementedError

    def put(self, key: Hashable, value: Any) -> None:
        """Insert or update ``key`` -> ``value`` and mark it most-recently-used.

        If the key already exists its value is overwritten and it becomes
        most-recently-used. If inserting a new key would exceed ``capacity``,
        evict the least-recently-used key first.
        """
        raise NotImplementedError

    def __contains__(self, key: Hashable) -> bool:
        """Return whether ``key`` is cached. Must NOT change recency order."""
        raise NotImplementedError

    def __len__(self) -> int:
        """Return the current number of cached entries."""
        raise NotImplementedError
