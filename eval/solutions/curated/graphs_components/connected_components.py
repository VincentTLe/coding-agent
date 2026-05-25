"""Reference solution: connected components of an undirected graph.

Builds a symmetric undirected adjacency view first (the input may list an edge in
only one direction), then walks each unvisited node's component iteratively.
"""

from typing import Dict, Hashable, List


def connected_components(graph: Dict[Hashable, List[Hashable]]) -> List[List[Hashable]]:
    # 1) Collect all nodes (keys and any node mentioned only as a neighbour).
    nodes = set(graph.keys())
    for nbrs in graph.values():
        nodes.update(nbrs)

    # 2) Build an undirected adjacency view: add both directions, drop self-loops.
    adj: Dict[Hashable, set] = {n: set() for n in nodes}
    for u in graph:
        for v in graph[u]:
            if u != v:
                adj[u].add(v)
                adj[v].add(u)

    # 3) Iterative DFS/BFS per component over the symmetric view.
    visited: set = set()
    components: List[List[Hashable]] = []
    for start in nodes:
        if start in visited:
            continue
        stack = [start]
        visited.add(start)
        comp: List[Hashable] = []
        while stack:
            node = stack.pop()
            comp.append(node)
            for nbr in adj[node]:
                if nbr not in visited:
                    visited.add(nbr)
                    stack.append(nbr)
        components.append(sorted(comp))

    # 4) Sort components by their smallest element.
    components.sort(key=lambda c: c[0])
    return components
