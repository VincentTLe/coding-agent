"""A small directed-graph container (COMPLETE — do not modify).

`paths.py` runs algorithms over this structure. Read this file: the exact
semantics of node creation, neighbour ordering, and edge de-duplication
matter for getting the algorithms (and their deterministic output) right.
"""

from __future__ import annotations


class Graph:
    """A directed graph with hashable node labels.

    Internally an adjacency map ``node -> set(successors)``. Key behaviours
    that ``paths.py`` relies on:

    * The graph is DIRECTED. ``add_edge(u, v)`` adds ``u -> v`` only.
    * Adding an edge auto-creates any node it mentions.
    * Parallel edges are de-duplicated (the successor store is a set), and
      self-loops (``add_edge(u, u)``) are allowed.
    * ``neighbors(node)`` returns successors SORTED, so traversals that visit
      neighbours in order are deterministic.
    """

    def __init__(self) -> None:
        self._adj: dict[object, set] = {}

    def add_node(self, node) -> None:
        """Register ``node`` with no edges (no-op if it already exists)."""
        self._adj.setdefault(node, set())

    def add_edge(self, u, v) -> None:
        """Add a directed edge ``u -> v``, creating both endpoints if needed."""
        self.add_node(u)
        self.add_node(v)
        self._adj[u].add(v)

    def nodes(self) -> list:
        """All node labels, sorted for determinism."""
        return sorted(self._adj)

    def neighbors(self, node) -> list:
        """Successors of ``node``, sorted. Raises ``KeyError`` if unknown."""
        if node not in self._adj:
            raise KeyError(node)
        return sorted(self._adj[node])

    def has_node(self, node) -> bool:
        return node in self._adj

    def has_edge(self, u, v) -> bool:
        return u in self._adj and v in self._adj[u]

    def in_degree(self, node) -> int:
        """Number of edges pointing INTO ``node``. Self-loops count once."""
        if node not in self._adj:
            raise KeyError(node)
        return sum(1 for succ in self._adj.values() if node in succ)
