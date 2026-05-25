"""Connected components of an undirected graph.

The agent must implement `connected_components` per the spec in task.md.
"""

from typing import Dict, Hashable, List


def connected_components(graph: Dict[Hashable, List[Hashable]]) -> List[List[Hashable]]:
    """Return the connected components of an undirected ``graph``.

    ``graph`` is an adjacency dict mapping each node to a list of its neighbours.
    The graph is **undirected**, but the input is **not guaranteed symmetric**:
    if ``v`` is listed in ``graph[u]`` you must treat ``u`` and ``v`` as connected
    even if ``u`` is not listed in ``graph[v]``.

    Return a list of components; each component is a **sorted list** of the nodes in
    it, and the list of components is sorted by each component's **first (smallest)
    element**. See task.md for the full specification and examples.
    """
    raise NotImplementedError
