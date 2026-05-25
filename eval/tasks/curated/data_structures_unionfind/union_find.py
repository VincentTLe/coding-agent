"""Disjoint Set Union (Union-Find) — implement-from-spec stub.

Replace every ``raise NotImplementedError`` with a working implementation that
satisfies the contract on each method and in task.md. Use path compression and
union by rank/size so that operations are near-constant amortized time.
"""

from __future__ import annotations

from typing import Hashable, List


class UnionFind:
    """A disjoint-set (union-find) structure over hashable elements.

    Elements are added lazily on first reference. Each element belongs to
    exactly one set; ``union`` merges two sets, ``find`` returns a set's
    canonical representative, and ``connected`` tests co-membership.

    Implement path compression in ``find`` and union by rank or size in
    ``union`` so the amortized cost per operation is effectively O(α(n)).
    """

    def __init__(self) -> None:
        """Create an empty structure with no elements."""
        raise NotImplementedError

    def find(self, x: Hashable) -> Hashable:
        """Return the canonical representative of ``x``'s set.

        If ``x`` has never been seen, add it as its own singleton set first,
        then return it. Two elements share a representative iff they are in the
        same set. Apply path compression while resolving.
        """
        raise NotImplementedError

    def union(self, x: Hashable, y: Hashable) -> bool:
        """Merge the sets containing ``x`` and ``y``.

        Return True if a merge happened (they were in different sets), or False
        if they were already in the same set. Adds unseen elements first. Merge
        using union by rank/size to keep trees shallow. A successful merge
        decreases ``count`` by 1.
        """
        raise NotImplementedError

    def connected(self, x: Hashable, y: Hashable) -> bool:
        """Return True iff ``x`` and ``y`` are in the same set (adding unseen
        elements first).
        """
        raise NotImplementedError

    def add(self, x: Hashable) -> None:
        """Ensure ``x`` exists as (at least) a singleton set. Idempotent: adding
        an existing element does not merge or reset it.
        """
        raise NotImplementedError

    @property
    def count(self) -> int:
        """Number of disjoint sets currently present."""
        raise NotImplementedError

    def size(self, x: Hashable) -> int:
        """Return how many elements are in ``x``'s set (adding ``x`` first if
        unseen, in which case the answer is 1).
        """
        raise NotImplementedError

    def groups(self) -> List[List[Hashable]]:
        """Return the current partition as a list of groups. Each group is a
        list of its members sorted ascending; the outer list is sorted by each
        group's first (smallest) member. Elements must be mutually comparable
        for this method.
        """
        raise NotImplementedError
