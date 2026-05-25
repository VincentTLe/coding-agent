"""Topological sort of a directed graph.

The agent must implement `topological_sort` per the spec in task.md.
"""

from typing import Dict, Hashable, List


def topological_sort(graph: Dict[Hashable, List[Hashable]]) -> List[Hashable]:
    """Return a topological ordering of the nodes of ``graph``.

    ``graph`` is an adjacency dict mapping each node to a list of its
    out-neighbours; an edge ``u -> v`` (``v in graph[u]``) means ``u`` must come
    **before** ``v`` in the ordering. Return ``[]`` if the graph contains a cycle
    (no valid ordering exists).

    See task.md for the full specification, the required tie-break rule, and
    examples.
    """
    raise NotImplementedError
