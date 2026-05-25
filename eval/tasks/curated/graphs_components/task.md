# graphs_components — connected_components

## Goal
Implement `connected_components(graph) -> list[list]` in `connected_components.py`.

Graph representation (specify precisely):
- `graph` is an **adjacency dict**: `Dict[node, List[node]]` mapping each node to a
  list of its neighbours. The graph is **UNDIRECTED**.
- The input is **NOT guaranteed to be symmetric**. If `v` appears in `graph[u]`, then
  `u` and `v` are in the same component, **whether or not** `u` appears in `graph[v]`.
  In other words, an entry `graph[u] = [v]` defines an undirected edge `u — v`.
- A node may appear only as a neighbour and never as a key; it is still a node of the
  graph and belongs to a component. Treat a missing key as a node with no listed
  neighbours.
- Nodes are hashable and, within a single call, **mutually comparable** with `<`
  (e.g. all ints, or all strings) so the output can be sorted deterministically.

Return the connected components as a **list of components**, where:
- each component is the **sorted list** (ascending) of the distinct nodes it contains, and
- the outer list is **sorted by each component's first element** (i.e. by its smallest node).

Behavioural requirements / edge cases:
- The **empty graph** (`{}`) returns `[]`.
- An **isolated node** (a key mapping to `[]`, with no other references) is its own
  component: `{"a": []}` -> `[["a"]]`.
- **Self-loops** (`u in graph[u]`) are allowed and do not create a duplicate node nor
  change the component structure.
- **Duplicate / parallel edges** in a neighbour list must not produce duplicate nodes in
  the output component.
- Components must be discovered without infinite looping on **cycles**.

Examples:
```
connected_components({})                                   -> []
connected_components({"a": []})                            -> [["a"]]
connected_components({1: [2], 2: [1], 3: []})              -> [[1, 2], [3]]
connected_components({1: [2], 3: [4], 5: []})              -> [[1, 2], [3, 4], [5]]  # asymmetric input
connected_components({0: [1], 1: [2], 2: [0]})             -> [[0, 1, 2]]            # cycle = one comp
connected_components({"a": ["a", "b", "b"], "b": []})      -> [["a", "b"]]          # self-loop + dup edges
```

## Category
graphs

## Difficulty
hard

## Tests
hidden

## Source/License
Authored for coding-agent eval. MIT.
