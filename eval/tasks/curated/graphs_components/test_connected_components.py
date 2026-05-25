"""Hidden tests for connected_components. The spec lives in task.md."""

import pytest

from connected_components import connected_components


def test_empty_graph():
    assert connected_components({}) == []


def test_single_isolated_node():
    assert connected_components({"a": []}) == [["a"]]


def test_two_nodes_one_edge_symmetric():
    assert connected_components({1: [2], 2: [1]}) == [[1, 2]]


def test_two_components_with_isolated():
    assert connected_components({1: [2], 2: [1], 3: []}) == [[1, 2], [3]]


def test_asymmetric_input_one_direction_only():
    # edge listed only as 1->2 and 3->4; still undirected components.
    assert connected_components({1: [2], 3: [4], 5: []}) == [[1, 2], [3, 4], [5]]


def test_asymmetric_chain():
    # a->b, b->c listed one direction; whole chain is one component.
    assert connected_components({"a": ["b"], "b": ["c"]}) == [["a", "b", "c"]]


def test_cycle_is_single_component():
    assert connected_components({0: [1], 1: [2], 2: [0]}) == [[0, 1, 2]]


def test_self_loop_and_duplicate_edges():
    assert connected_components({"a": ["a", "b", "b"], "b": []}) == [["a", "b"]]


def test_node_only_as_neighbour_included():
    # 'c' never a key but must appear, joined to b.
    assert connected_components({"a": [], "b": ["c"]}) == [["a"], ["b", "c"]]


def test_components_sorted_by_smallest_element():
    g = {5: [6], 6: [5], 1: [2], 2: [1], 3: []}
    assert connected_components(g) == [[1, 2], [3], [5, 6]]


def test_within_component_sorted_ascending():
    g = {3: [1], 1: [2], 2: [3]}
    assert connected_components(g) == [[1, 2, 3]]


def test_star_graph():
    # center 0 connected to 1,2,3,4 (asymmetric: only center lists them)
    g = {0: [1, 2, 3, 4]}
    assert connected_components(g) == [[0, 1, 2, 3, 4]]


def test_two_stars_merge_via_shared_node():
    # 0-1-2 and 2-3-4 share node 2 -> one component
    g = {0: [1], 1: [2], 3: [2], 4: [3]}
    assert connected_components(g) == [[0, 1, 2, 3, 4]]


def test_many_isolated_nodes():
    g = {n: [] for n in [4, 2, 7, 1]}
    assert connected_components(g) == [[1], [2], [4], [7]]


def test_no_duplicate_nodes_in_output():
    g = {1: [2, 2, 3], 2: [1, 3], 3: [1, 2]}
    comps = connected_components(g)
    assert comps == [[1, 2, 3]]
    # also assert no component has duplicates
    for comp in comps:
        assert len(comp) == len(set(comp))


def test_returns_list_of_lists():
    out = connected_components({1: [2], 2: [1]})
    assert isinstance(out, list)
    assert all(isinstance(c, list) for c in out)


def test_larger_mixed_graph():
    # Components: {0,1,2,3}, {4,5}, {6}, {7,8,9}
    g = {
        0: [1],
        1: [2, 3],
        2: [],
        3: [0],
        4: [5],
        5: [],
        6: [],
        7: [8],
        8: [9],
        9: [7],
    }
    assert connected_components(g) == [[0, 1, 2, 3], [4, 5], [6], [7, 8, 9]]
