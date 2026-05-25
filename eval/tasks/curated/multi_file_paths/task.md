# multi_file_paths — Reachability & shortest-hops over a directed graph

## Goal
Implement the graph algorithms in `paths.py` so all tests in `test_paths.py`
pass.

The graph container is already written for you in `graph.py` (a directed
`Graph` with an adjacency map). You MUST read `graph.py` to implement
`paths.py` correctly — note that the graph is **directed**, that `neighbors`
returns successors **sorted** (which you rely on for deterministic output),
and that helpers like `nodes`, `in_degree`, and `has_node` already exist.

Implement these functions (full specs are in the `paths.py` docstrings):

- `reachable(graph, start)` — set of all nodes reachable from `start` via
  directed edges, including `start`. `KeyError` if `start` is unknown.
- `has_path(graph, src, dst)` — True iff `dst` is reachable from `src`
  (a node always reaches itself). `KeyError` on an unknown endpoint.
- `shortest_hops(graph, src, dst)` — fewest edges on a directed path (0 to
  self, -1 if unreachable). This is a breadth-first shortest path since every
  edge has weight 1. `KeyError` on an unknown endpoint.
- `topological_order(graph)` — a topological ordering via Kahn's algorithm;
  break ties by smallest node label so the result is deterministic; raise
  `ValueError` if the graph has a directed cycle.
- `has_cycle(graph)` — True iff the directed graph contains a cycle (a
  self-loop counts).

Example:

```python
g = Graph()
g.add_edge("a", "b"); g.add_edge("a", "c")
g.add_edge("b", "d"); g.add_edge("c", "d")
reachable(g, "a")        # {"a", "b", "c", "d"}
shortest_hops(g, "a", "d")  # 2
topological_order(g)     # ["a", "b", "c", "d"]
```

## Category
multi_file

## Difficulty
hard

## Tests
visible

## Source/License
Authored for coding-agent eval. MIT.
