"""Dijkstra's single-source shortest paths on a weighted directed graph.

The agent must implement `dijkstra` per the spec in task.md.
"""

from typing import Dict, Hashable


def dijkstra(graph: Dict[Hashable, Dict[Hashable, float]], source: Hashable) -> Dict[Hashable, float]:
    """Return shortest-path distances from ``source`` to every reachable node.

    ``graph`` is a weighted adjacency dict: ``graph[u]`` maps each out-neighbour
    ``v`` to the (non-negative) weight of the directed edge ``u -> v``. The result
    maps each node **reachable** from ``source`` (including ``source`` itself, at
    distance 0) to its minimum total path weight. Unreachable nodes are **omitted**
    from the result.

    See task.md for the full specification and examples.
    """
    raise NotImplementedError
