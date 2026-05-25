# graphs_toposort — topological_sort

## Goal
Implement `topological_sort(graph) -> list` in `topological_sort.py`.

Graph representation (specify precisely):
- `graph` is an **adjacency dict**: `Dict[node, List[node]]` mapping each node to a
  list of its **out-neighbours**. A directed edge `u -> v` (i.e. `v in graph[u]`) is a
  **precedence constraint**: `u` must appear **before** `v` in the output ordering.
- Nodes are hashable and, within a single call, **mutually comparable** with `<`
  (e.g. all ints, or all strings) — this is needed for the deterministic tie-break below.
- A node may appear only as a neighbour and never as a key (a node with no out-edges).
  Such nodes are still part of the graph and **must appear** in the output. Treat a
  missing key as a node with an empty neighbour list.

Return a list containing **every node exactly once**, ordered so that for every edge
`u -> v`, `u` precedes `v`. If no such ordering exists (the graph has a **cycle**),
return `[]` (an empty list).

Deterministic tie-break (required so the answer is unique):
- Use **Kahn's algorithm**. Whenever more than one node currently has in-degree 0 and is
  ready to be emitted, always emit the **smallest** such node (by `<`) next.
- Duplicate / parallel edges (e.g. `{"a": ["b", "b"]}`) must not change in-degrees
  incorrectly — count each occurrence consistently so the algorithm still terminates with
  the right ordering. (Equivalently: collapse parallel edges, or decrement once per
  occurrence as long as in-degree was computed the same way.)

Behavioural requirements / edge cases:
- The **empty graph** (`{}`) returns `[]`.
- A graph of isolated nodes with no edges returns them in sorted order.
- A **self-loop** (`u in graph[u]`) is a cycle of length 1 → return `[]`.
- Disconnected DAGs are sorted across all components, respecting the tie-break globally.

Examples:
```
topological_sort({})                                  -> []
topological_sort({"a": ["b"], "b": ["c"]})            -> ["a", "b", "c"]
topological_sort({"a": ["c"], "b": ["c"], "c": []})   -> ["a", "b", "c"]   # a,b both ready; a<b
topological_sort({2: [], 1: [], 3: []})               -> [1, 2, 3]         # isolated, sorted
topological_sort({0: [1], 1: [2], 2: [0]})            -> []                # 3-cycle
topological_sort({"x": ["x"]})                        -> []                # self-loop
```

## Category
graphs

## Difficulty
hard

## Tests
hidden

## Source/License
Authored for coding-agent eval. MIT.
