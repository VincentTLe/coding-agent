"""Hidden tests for dijkstra. The spec lives in task.md."""

import pytest

from dijkstra import dijkstra


def test_empty_graph_source_only():
    assert dijkstra({}, "a") == {"a": 0}


def test_source_not_a_key():
    # source has no out-edges and isn't a key, but appears at distance 0
    assert dijkstra({"x": {"y": 1}}, "z") == {"z": 0}


def test_simple_relaxation_shorter_multi_hop_wins():
    g = {"a": {"b": 1, "c": 4}, "b": {"c": 2, "d": 5}, "c": {"d": 1}, "d": {}}
    assert dijkstra(g, "a") == {"a": 0, "b": 1, "c": 3, "d": 4}


def test_more_edges_but_cheaper_path_chosen():
    # direct a->d costs 10; a->b->c->d costs 1+1+1=3
    g = {"a": {"b": 1, "d": 10}, "b": {"c": 1}, "c": {"d": 1}, "d": {}}
    assert dijkstra(g, "a") == {"a": 0, "b": 1, "c": 2, "d": 3}


def test_unreachable_nodes_omitted():
    g = {0: {1: 2}, 1: {2: 3}, 3: {0: 1}}  # 3 unreachable from 0
    result = dijkstra(g, 0)
    assert result == {0: 0, 1: 2, 2: 5}
    assert 3 not in result


def test_disconnected_components():
    g = {1: {2: 5}, 2: {}, 10: {11: 1}, 11: {}}
    assert dijkstra(g, 1) == {1: 0, 2: 5}
    assert dijkstra(g, 10) == {10: 0, 11: 1}


def test_self_loop_does_not_help_or_hang():
    g = {"x": {"x": 5, "y": 2}, "y": {}}
    assert dijkstra(g, "x") == {"x": 0, "y": 2}


def test_cycle_terminates_and_is_correct():
    # cycle a->b->c->a, plus c->d
    g = {"a": {"b": 1}, "b": {"c": 1}, "c": {"a": 1, "d": 1}, "d": {}}
    assert dijkstra(g, "a") == {"a": 0, "b": 1, "c": 2, "d": 3}


def test_zero_weight_edges():
    g = {"a": {"b": 0}, "b": {"c": 0}, "c": {}}
    assert dijkstra(g, "a") == {"a": 0, "b": 0, "c": 0}


def test_float_and_int_weights_mixed():
    g = {"a": {"b": 1.5, "c": 4}, "b": {"c": 1.0}, "c": {}}
    result = dijkstra(g, "a")
    assert result["a"] == 0
    assert result["b"] == pytest.approx(1.5)
    assert result["c"] == pytest.approx(2.5)  # a->b->c = 1.5+1.0 beats a->c = 4


def test_node_only_as_target_is_a_sink():
    # 'd' only appears as a target, never a key
    g = {"a": {"b": 1}, "b": {"d": 2}}
    assert dijkstra(g, "a") == {"a": 0, "b": 1, "d": 3}


def test_single_node_graph():
    assert dijkstra({"a": {}}, "a") == {"a": 0}


def test_stale_queue_entry_ignored():
    # Classic case where a node gets pushed with a large dist, then a smaller one;
    # the stale (larger) pop must not overwrite the finalized distance.
    g = {
        "s": {"a": 10, "b": 1},
        "b": {"a": 1},   # gives a much cheaper route to a (1+1=2)
        "a": {"t": 1},
        "t": {},
    }
    assert dijkstra(g, "s") == {"s": 0, "a": 2, "b": 1, "t": 3}


def test_classic_weighted_graph():
    # Well-known small example.
    g = {
        "A": {"B": 7, "C": 9, "F": 14},
        "B": {"C": 10, "D": 15},
        "C": {"D": 11, "F": 2},
        "D": {"E": 6},
        "E": {},
        "F": {"E": 9},
    }
    result = dijkstra(g, "A")
    assert result["A"] == 0
    assert result["B"] == 7
    assert result["C"] == 9
    assert result["D"] == 20    # A->C->D = 9+11
    assert result["F"] == 11    # A->C->F = 9+2
    assert result["E"] == 20    # A->C->F->E = 9+2+9


def test_returns_dict():
    assert isinstance(dijkstra({"a": {}}, "a"), dict)
