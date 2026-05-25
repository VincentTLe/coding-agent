# graphs_bfs — bfs_shortest_path

## Goal
Implement `bfs_shortest_path(graph, start, goal) -> int` in `bfs_shortest_path.py`.

Graph representation (specify precisely):
- `graph` is an **adjacency dict**: `Dict[node, List[node]]` mapping each node to a
  list of its **out-neighbours**. Edges are **directed**: an edge `u -> v` means
  `v in graph[u]`. An undirected graph is encoded by listing both directions.
- Nodes are any hashable values (ints, strings, ...).
- A node may be a *target* of an edge without appearing as a key (i.e. a sink node
  with no out-edges may be missing from `graph`). Treat a missing key as a node with
  an empty neighbour list.

Return the **minimum number of edges (hops)** on any path from `start` to `goal`:
- If `start == goal`, return `0` (even if `start` is not a key in `graph`).
- If `goal` is **unreachable** from `start`, return `-1`.
- Otherwise return the length of the shortest path in edges.

Behavioural requirements / edge cases:
- The graph may be **empty** (`{}`), **disconnected**, contain **cycles**, and contain
  **self-loops** (`u in graph[u]`). Self-loops and cycles must never cause an infinite
  loop — each node is visited at most once.
- Parallel/duplicate edges in a neighbour list (e.g. `{"a": ["b", "b"]}`) must be handled
  and not affect the result.
- The traversal must be genuine breadth-first so the returned value is the *minimum* hop
  count, not merely *some* path length. (A correct BFS that stops at the first time it
  dequeues / discovers the goal yields the minimum.)

Examples:
```
g = {"a": ["b", "c"], "b": ["d"], "c": ["d"], "d": ["e"]}
bfs_shortest_path(g, "a", "a")  ->  0
bfs_shortest_path(g, "a", "d")  ->  2      # a->b->d or a->c->d
bfs_shortest_path(g, "a", "e")  ->  3      # a->b->d->e
bfs_shortest_path(g, "e", "a")  -> -1      # no outgoing edges from e
bfs_shortest_path({}, 1, 1)     ->  0
bfs_shortest_path({}, 1, 2)     -> -1

# shortest path must win over a longer one that BFS could find first:
g2 = {0: [1, 3], 1: [2], 2: [3]}
bfs_shortest_path(g2, 0, 3)     ->  1      # direct edge 0->3, not 0->1->2->3
```

## Category
graphs

## Difficulty
hard

## Tests
hidden

## Source/License
Authored for coding-agent eval. MIT.
