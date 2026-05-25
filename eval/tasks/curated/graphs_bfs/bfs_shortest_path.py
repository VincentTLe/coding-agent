"""Breadth-first shortest path (minimum number of hops) in an unweighted graph.

The agent must implement `bfs_shortest_path` per the spec in task.md.
"""

from typing import Dict, Hashable, List


def bfs_shortest_path(graph: Dict[Hashable, List[Hashable]], start: Hashable, goal: Hashable) -> int:
    """Return the minimum number of edges on a path from ``start`` to ``goal``.

    ``graph`` is an adjacency dict mapping each node to a list of its
    out-neighbours (a directed graph; for an undirected graph both directions
    appear in the dict). Return ``-1`` if ``goal`` is not reachable from
    ``start``. The distance from a node to itself is ``0``.

    See task.md for the full specification and examples.
    """
    raise NotImplementedError
