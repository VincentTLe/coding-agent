"""Graph algorithms over ``graph.Graph`` (IMPLEMENT THIS FILE).

Each function raises ``NotImplementedError``. Implement them to satisfy the
docstrings and ``test_paths.py``. You will need to READ ``graph.py`` to use
``Graph.neighbors`` / ``Graph.nodes`` / ``Graph.in_degree`` / ``Graph.has_node``
correctly — in particular that the graph is directed and that ``neighbors``
returns its results SORTED (relied on for deterministic ordering below).
"""

from __future__ import annotations

from graph import Graph


def reachable(graph: Graph, start) -> set:
    """Return the set of nodes reachable from ``start`` (including ``start``).

    Raises ``KeyError`` if ``start`` is not in the graph. Following directed
    edges only.
    """
    raise NotImplementedError


def has_path(graph: Graph, src, dst) -> bool:
    """Return True iff ``dst`` is reachable from ``src`` via directed edges.

    A node always has a path to itself. Raises ``KeyError`` if either endpoint
    is not in the graph.
    """
    raise NotImplementedError


def shortest_hops(graph: Graph, src, dst) -> int:
    """Return the fewest edges on any directed path from ``src`` to ``dst``.

    ``src`` to itself is 0. If ``dst`` is unreachable from ``src`` return -1.
    Raises ``KeyError`` if either endpoint is not in the graph. (Every edge has
    weight 1, so this is a breadth-first shortest path.)
    """
    raise NotImplementedError


def topological_order(graph: Graph) -> list:
    """Return a topological ordering of all nodes (a list).

    Uses Kahn's algorithm. To make the result DETERMINISTIC, whenever several
    nodes have in-degree 0 at the same time, pick the smallest (per Python's
    ``sorted``) first. If the graph contains a directed cycle (so no
    topological order exists) raise ``ValueError``.
    """
    raise NotImplementedError


def has_cycle(graph: Graph) -> bool:
    """Return True iff the directed graph contains a cycle.

    A self-loop counts as a cycle.
    """
    raise NotImplementedError
