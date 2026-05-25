# graphs_dijkstra — dijkstra

## Goal
Implement `dijkstra(graph, source) -> dict` in `dijkstra.py`.

Graph representation (specify precisely):
- `graph` is a **weighted adjacency dict**: `Dict[node, Dict[node, weight]]`.
  `graph[u]` maps each out-neighbour `v` to the weight of the directed edge `u -> v`.
- Edges are **directed**: `graph[u][v] = w` does not imply an edge `v -> u`.
- Weights are **non-negative** numbers (`int` or `float`); `0`-weight edges are allowed.
- Nodes are any hashable values.
- A node may appear only as a *target* (inside some `graph[u]`) and never as a key — a
  sink with no outgoing edges. Treat a missing key as a node with no out-edges.

Return a dict mapping every node **reachable** from `source` to the **minimum total
weight** of a path from `source` to that node:
- The distance from `source` to itself is `0`. `source` is always present in the result
  (even if `source` is not a key in `graph`).
- Nodes that are **not reachable** from `source` are **omitted** from the result dict
  (do NOT include them with infinity).
- Use **Dijkstra's algorithm** (with a priority queue). A node's distance is finalized
  the first time it is popped with the minimum tentative distance; later, larger entries
  for the same node must be ignored.

Behavioural requirements / edge cases:
- The **empty graph** (`{}`): `dijkstra({}, "a")` returns `{"a": 0}`.
- **Disconnected** graphs: only the reachable part appears.
- **Cycles** (including a path that loops back) must not cause infinite work.
- **Self-loops** (`graph[u][u] = w`) are allowed and never improve `u`'s own distance.
- When two routes reach a node, the **smaller** total weight must win, even if the
  smaller-weight route uses **more edges** (this is the whole point — a greedy
  fewest-hops answer is wrong).
- Integer and float weights may be mixed; compare distances numerically.

Examples:
```
dijkstra({}, "a")                                  -> {"a": 0}

g = {"a": {"b": 1, "c": 4}, "b": {"c": 2, "d": 5}, "c": {"d": 1}, "d": {}}
dijkstra(g, "a")  -> {"a": 0, "b": 1, "c": 3, "d": 4}
# c via a->b->c (1+2=3) beats a->c (4); d via a->b->c->d (3+1=4) beats a->b->d (1+5=6)

g2 = {0: {1: 2}, 1: {2: 3}, 3: {0: 1}}     # node 3 cannot be reached from 0
dijkstra(g2, 0)   -> {0: 0, 1: 2, 2: 5}    # 3 is omitted

g3 = {"x": {"x": 5, "y": 2}, "y": {}}      # self-loop on x
dijkstra(g3, "x") -> {"x": 0, "y": 2}
```

## Category
graphs

## Difficulty
hard

## Tests
hidden

## Source/License
Authored for coding-agent eval. MIT.
