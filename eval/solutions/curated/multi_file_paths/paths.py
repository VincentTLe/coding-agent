"""Reference solution for paths.py."""

from __future__ import annotations

from collections import deque

from graph import Graph


def reachable(graph: Graph, start) -> set:
    if not graph.has_node(start):
        raise KeyError(start)
    seen = {start}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for nxt in graph.neighbors(node):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return seen


def has_path(graph: Graph, src, dst) -> bool:
    if not graph.has_node(src) or not graph.has_node(dst):
        raise KeyError(src if not graph.has_node(src) else dst)
    return dst in reachable(graph, src)


def shortest_hops(graph: Graph, src, dst) -> int:
    if not graph.has_node(src) or not graph.has_node(dst):
        raise KeyError(src if not graph.has_node(src) else dst)
    dist = {src: 0}
    queue = deque([src])
    while queue:
        node = queue.popleft()
        if node == dst:
            return dist[node]
        for nxt in graph.neighbors(node):
            if nxt not in dist:
                dist[nxt] = dist[node] + 1
                queue.append(nxt)
    return dist.get(dst, -1)


def topological_order(graph: Graph) -> list:
    nodes = graph.nodes()
    indeg = {n: graph.in_degree(n) for n in nodes}
    # ready = nodes with in-degree 0; keep sorted so smallest comes out first.
    ready = sorted(n for n in nodes if indeg[n] == 0)
    order: list = []
    while ready:
        node = ready.pop(0)
        order.append(node)
        for nxt in graph.neighbors(node):
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                # insert keeping `ready` sorted for deterministic tie-breaking
                lo, hi = 0, len(ready)
                while lo < hi:
                    mid = (lo + hi) // 2
                    if ready[mid] < nxt:
                        lo = mid + 1
                    else:
                        hi = mid
                ready.insert(lo, nxt)
    if len(order) != len(nodes):
        raise ValueError("graph has a cycle; no topological order exists")
    return order


def has_cycle(graph: Graph) -> bool:
    try:
        topological_order(graph)
    except ValueError:
        return True
    return False
