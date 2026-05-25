"""Reference solution: breadth-first shortest path (minimum hops)."""

from collections import deque
from typing import Dict, Hashable, List


def bfs_shortest_path(graph: Dict[Hashable, List[Hashable]], start: Hashable, goal: Hashable) -> int:
    """Return the minimum number of edges from ``start`` to ``goal``, or -1.

    Standard BFS over an adjacency dict. ``dist`` doubles as the visited set, so
    self-loops, cycles and duplicate edges are handled (each node enqueued once).
    """
    if start == goal:
        return 0
    dist = {start: 0}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        d = dist[node]
        for nbr in graph.get(node, ()):  # missing key -> treated as a sink
            if nbr not in dist:
                if nbr == goal:
                    return d + 1
                dist[nbr] = d + 1
                queue.append(nbr)
    return -1
