"""Tests for paths.py. Visible — use them as feedback while implementing."""

import pytest

from graph import Graph
from paths import (
    has_cycle,
    has_path,
    reachable,
    shortest_hops,
    topological_order,
)


def line_graph():
    # a -> b -> c -> d
    g = Graph()
    g.add_edge("a", "b")
    g.add_edge("b", "c")
    g.add_edge("c", "d")
    return g


def diamond():
    # a -> b -> d, a -> c -> d  (plus isolated node "x")
    g = Graph()
    g.add_edge("a", "b")
    g.add_edge("a", "c")
    g.add_edge("b", "d")
    g.add_edge("c", "d")
    g.add_node("x")
    return g


def test_reachable_line():
    g = line_graph()
    assert reachable(g, "a") == {"a", "b", "c", "d"}
    assert reachable(g, "c") == {"c", "d"}
    assert reachable(g, "d") == {"d"}


def test_reachable_respects_direction():
    g = line_graph()
    # edges are directed; going backward reaches nothing new
    assert reachable(g, "d") == {"d"}


def test_reachable_isolated_node():
    g = diamond()
    assert reachable(g, "x") == {"x"}


def test_reachable_unknown_node():
    g = line_graph()
    with pytest.raises(KeyError):
        reachable(g, "zzz")


def test_has_path_self():
    g = line_graph()
    assert has_path(g, "a", "a") is True


def test_has_path_forward_and_backward():
    g = line_graph()
    assert has_path(g, "a", "d") is True
    assert has_path(g, "d", "a") is False


def test_has_path_unknown_endpoint():
    g = line_graph()
    with pytest.raises(KeyError):
        has_path(g, "a", "nope")


def test_shortest_hops_basic():
    g = line_graph()
    assert shortest_hops(g, "a", "a") == 0
    assert shortest_hops(g, "a", "b") == 1
    assert shortest_hops(g, "a", "d") == 3


def test_shortest_hops_picks_shorter_branch():
    # a->b->c->d (3 hops) but also a->d direct (1 hop)
    g = line_graph()
    g.add_edge("a", "d")
    assert shortest_hops(g, "a", "d") == 1


def test_shortest_hops_unreachable():
    g = line_graph()
    assert shortest_hops(g, "d", "a") == -1


def test_shortest_hops_diamond():
    g = diamond()
    assert shortest_hops(g, "a", "d") == 2
    assert shortest_hops(g, "a", "x") == -1


def test_shortest_hops_unknown_endpoint():
    g = line_graph()
    with pytest.raises(KeyError):
        shortest_hops(g, "ghost", "a")


def test_topological_order_line():
    g = line_graph()
    assert topological_order(g) == ["a", "b", "c", "d"]


def test_topological_order_is_valid_and_deterministic():
    g = diamond()
    order = topological_order(g)
    # all nodes present exactly once
    assert sorted(order) == ["a", "b", "c", "d", "x"]
    pos = {n: i for i, n in enumerate(order)}
    # every edge goes forward in the order
    for u in g.nodes():
        for v in g.neighbors(u):
            assert pos[u] < pos[v]
    # tie-break by smallest label among in-degree-0 nodes: "a" (0) is picked
    # before "x" (also 0) because "a" < "x"; and once "a" is removed, "b" is
    # chosen before "c". With Kahn + smallest-first the whole order is fixed.
    assert order == ["a", "b", "c", "d", "x"]
    assert pos["b"] < pos["c"]


def test_topological_order_cycle_raises():
    g = Graph()
    g.add_edge("a", "b")
    g.add_edge("b", "c")
    g.add_edge("c", "a")
    with pytest.raises(ValueError):
        topological_order(g)


def test_has_cycle_false_on_dag():
    assert has_cycle(line_graph()) is False
    assert has_cycle(diamond()) is False


def test_has_cycle_true():
    g = Graph()
    g.add_edge(1, 2)
    g.add_edge(2, 3)
    g.add_edge(3, 1)
    assert has_cycle(g) is True


def test_has_cycle_self_loop():
    g = Graph()
    g.add_edge("a", "a")
    assert has_cycle(g) is True


def test_has_cycle_empty_graph():
    assert has_cycle(Graph()) is False
