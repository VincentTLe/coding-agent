"""Hidden tests for topological_sort. The spec lives in task.md."""

import pytest

from topological_sort import topological_sort


def _all_nodes(graph):
    nodes = set(graph.keys())
    for nbrs in graph.values():
        nodes.update(nbrs)
    return nodes


def _is_valid_topo(graph, order):
    """order is a valid topo sort: contains every node once, respects every edge."""
    nodes = _all_nodes(graph)
    if sorted(map(str, order)) != sorted(map(str, nodes)):
        return False
    if len(order) != len(set(order)):
        return False
    pos = {n: i for i, n in enumerate(order)}
    for u, nbrs in graph.items():
        for v in nbrs:
            if pos[u] >= pos[v]:
                return False
    return True


def test_empty_graph():
    assert topological_sort({}) == []


def test_simple_chain_exact_order():
    assert topological_sort({"a": ["b"], "b": ["c"]}) == ["a", "b", "c"]


def test_tie_break_smallest_first():
    # a and b both have in-degree 0; a < b so a comes first.
    assert topological_sort({"a": ["c"], "b": ["c"], "c": []}) == ["a", "b", "c"]


def test_isolated_nodes_sorted():
    assert topological_sort({2: [], 1: [], 3: []}) == [1, 2, 3]


def test_node_only_as_neighbour_is_included():
    # 'c' is never a key but must appear in the output.
    order = topological_sort({"a": ["c"], "b": ["c"]})
    assert set(order) == {"a", "b", "c"}
    assert _is_valid_topo({"a": ["c"], "b": ["c"]}, order)
    # tie-break: a<b, and c last
    assert order == ["a", "b", "c"]


def test_cycle_returns_empty():
    assert topological_sort({0: [1], 1: [2], 2: [0]}) == []


def test_two_cycle_returns_empty():
    assert topological_sort({"a": ["b"], "b": ["a"]}) == []


def test_self_loop_returns_empty():
    assert topological_sort({"x": ["x"]}) == []
    assert topological_sort({"a": ["b"], "b": ["b"]}) == []


def test_partial_cycle_in_otherwise_dag():
    # one component is a DAG, another has a cycle -> whole thing has no valid order
    g = {"a": ["b"], "c": ["d"], "d": ["c"]}
    assert topological_sort(g) == []


def test_diamond_exact_order():
    g = {"a": ["b", "c"], "b": ["d"], "c": ["d"], "d": []}
    assert topological_sort(g) == ["a", "b", "c", "d"]


def test_duplicate_parallel_edges():
    g = {"a": ["b", "b"], "b": ["c", "c", "c"], "c": []}
    assert topological_sort(g) == ["a", "b", "c"]


def test_disconnected_dags_global_tie_break():
    # Two independent chains 1->3 and 2->4. Ready set order must be global.
    g = {1: [3], 2: [4], 3: [], 4: []}
    # in-degree-0 ready: 1,2 -> pick 1; then ready {2,3} -> pick 2; then {3,4} -> 3; then 4
    assert topological_sort(g) == [1, 2, 3, 4]


def test_validity_on_larger_dag():
    # Layered DAG: layer i connects to layer i+1; plenty of valid orders exist.
    g = {}
    layers = [[0, 1, 2], [3, 4], [5, 6, 7], [8]]
    for i in range(len(layers) - 1):
        for u in layers[i]:
            g.setdefault(u, [])
            for v in layers[i + 1]:
                g[u].append(v)
    for u in layers[-1]:
        g.setdefault(u, [])
    order = topological_sort(g)
    assert _is_valid_topo(g, order)
    # With the smallest-first rule the layered DAG comes out fully sorted.
    assert order == [0, 1, 2, 3, 4, 5, 6, 7, 8]


def test_single_node_no_edges():
    assert topological_sort({"only": []}) == ["only"]


def test_returns_list_type():
    assert isinstance(topological_sort({"a": []}), list)
    assert isinstance(topological_sort({"a": ["a"]}), list)
