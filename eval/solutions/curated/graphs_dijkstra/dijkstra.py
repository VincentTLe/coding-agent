"""Reference solution: Dijkstra's algorithm with a binary heap."""

import heapq
from typing import Dict, Hashable


def dijkstra(graph: Dict[Hashable, Dict[Hashable, float]], source: Hashable) -> Dict[Hashable, float]:
    """Return shortest distances from ``source`` to every reachable node.

    Lazy-deletion variant: a node may sit in the heap multiple times; the first
    pop (smallest distance) finalizes it and stale, larger entries are skipped.
    """
    dist: Dict[Hashable, float] = {source: 0}
    heap = [(0, _Order(source))]  # (tentative distance, tie-break wrapper)
    while heap:
        d, wrapped = heapq.heappop(heap)
        u = wrapped.node
        if d > dist.get(u, float("inf")):
            continue  # stale entry — a better distance was already finalized
        for v, w in graph.get(u, {}).items():
            nd = d + w
            if nd < dist.get(v, float("inf")):
                dist[v] = nd
                heapq.heappush(heap, (nd, _Order(v)))
    return dist


class _Order:
    """Wrap a node so heap tuples never compare the (possibly unorderable) node.

    Two heap entries can share the same distance; without this, Python would fall
    back to comparing the node values, which may be unorderable (e.g. mixed types)
    or simply undesirable. ``_Order`` instances compare as equal, so ties are kept
    in push order and the node is never compared.
    """

    __slots__ = ("node",)

    def __init__(self, node):
        self.node = node

    def __lt__(self, other):  # all instances tie -> never raises on node compare
        return False
