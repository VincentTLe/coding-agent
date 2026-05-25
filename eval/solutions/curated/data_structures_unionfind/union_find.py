"""Reference solution for the UnionFind task.

Dict-backed disjoint-set with iterative path compression in ``find`` and union
by size in ``union``. Elements are added lazily.
"""

from __future__ import annotations

from typing import Dict, Hashable, List


class UnionFind:
    def __init__(self) -> None:
        self._parent: Dict[Hashable, Hashable] = {}
        self._size: Dict[Hashable, int] = {}
        self._count = 0

    def add(self, x: Hashable) -> None:
        if x not in self._parent:
            self._parent[x] = x
            self._size[x] = 1
            self._count += 1

    def find(self, x: Hashable) -> Hashable:
        self.add(x)
        # Find root.
        root = x
        while self._parent[root] != root:
            root = self._parent[root]
        # Path compression: point every node on the path straight at the root.
        while self._parent[x] != root:
            self._parent[x], x = root, self._parent[x]
        return root

    def union(self, x: Hashable, y: Hashable) -> bool:
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return False
        # Union by size: attach the smaller tree under the larger root.
        if self._size[rx] < self._size[ry]:
            rx, ry = ry, rx
        self._parent[ry] = rx
        self._size[rx] += self._size[ry]
        self._count -= 1
        return True

    def connected(self, x: Hashable, y: Hashable) -> bool:
        return self.find(x) == self.find(y)

    @property
    def count(self) -> int:
        return self._count

    def size(self, x: Hashable) -> int:
        return self._size[self.find(x)]

    def groups(self) -> List[List[Hashable]]:
        buckets: Dict[Hashable, List[Hashable]] = {}
        for elem in self._parent:
            buckets.setdefault(self.find(elem), []).append(elem)
        return sorted((sorted(g) for g in buckets.values()), key=lambda g: g[0])
