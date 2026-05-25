"""Reference solution: Kahn's algorithm with smallest-node-first tie-break."""

import heapq
from typing import Dict, Hashable, List


def topological_sort(graph: Dict[Hashable, List[Hashable]]) -> List[Hashable]:
    """Return a topological ordering (smallest ready node first), or [] on cycle."""
    # Collect every node, including ones that only appear as neighbours.
    nodes = set(graph.keys())
    for nbrs in graph.values():
        nodes.update(nbrs)

    # Build adjacency (collapse parallel edges) and in-degrees consistently.
    adj: Dict[Hashable, set] = {n: set() for n in nodes}
    indeg: Dict[Hashable, int] = {n: 0 for n in nodes}
    for u in graph:
        for v in graph[u]:
            if v not in adj[u]:
                adj[u].add(v)
                indeg[v] += 1

    # Min-heap of ready (in-degree 0) nodes -> deterministic smallest-first order.
    ready = [n for n in nodes if indeg[n] == 0]
    heapq.heapify(ready)

    order: List[Hashable] = []
    while ready:
        u = heapq.heappop(ready)
        order.append(u)
        for v in adj[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                heapq.heappush(ready, v)

    # If not every node was emitted, a cycle remained.
    return order if len(order) == len(nodes) else []
