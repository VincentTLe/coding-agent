"""Hidden tests for bfs_shortest_path. The spec lives in task.md."""

import pytest

from bfs_shortest_path import bfs_shortest_path


def test_start_equals_goal_present():
    assert bfs_shortest_path({"a": ["b"]}, "a", "a") == 0


def test_start_equals_goal_missing_key():
    # start not a key in the graph, but distance to itself is still 0
    assert bfs_shortest_path({}, 1, 1) == 0
    assert bfs_shortest_path({"x": ["y"]}, "z", "z") == 0


def test_empty_graph_unreachable():
    assert bfs_shortest_path({}, 1, 2) == -1


def test_simple_chain():
    g = {"a": ["b", "c"], "b": ["d"], "c": ["d"], "d": ["e"]}
    assert bfs_shortest_path(g, "a", "b") == 1
    assert bfs_shortest_path(g, "a", "d") == 2
    assert bfs_shortest_path(g, "a", "e") == 3


def test_direct_edge_beats_longer_route():
    # If BFS is implemented wrong (e.g. DFS or counting the wrong path), this fails.
    g = {0: [1, 3], 1: [2], 2: [3]}
    assert bfs_shortest_path(g, 0, 3) == 1


def test_min_over_two_equal_paths():
    g = {"a": ["b", "c"], "b": ["d"], "c": ["d"]}
    assert bfs_shortest_path(g, "a", "d") == 2


def test_unreachable_from_sink():
    g = {"a": ["b", "c"], "b": ["d"], "c": ["d"], "d": ["e"]}
    # e has no outgoing edges (and is not a key)
    assert bfs_shortest_path(g, "e", "a") == -1


def test_disconnected_components():
    g = {0: [1], 1: [0], 2: [3], 3: [2]}
    assert bfs_shortest_path(g, 0, 1) == 1
    assert bfs_shortest_path(g, 0, 3) == -1
    assert bfs_shortest_path(g, 2, 3) == 1


def test_self_loop_does_not_hang():
    g = {"a": ["a", "b"], "b": ["b"]}
    assert bfs_shortest_path(g, "a", "b") == 1
    assert bfs_shortest_path(g, "a", "a") == 0


def test_cycle_does_not_hang():
    g = {0: [1], 1: [2], 2: [0]}  # 3-cycle
    assert bfs_shortest_path(g, 0, 2) == 2
    assert bfs_shortest_path(g, 0, 0) == 0
    assert bfs_shortest_path(g, 2, 1) == 2  # 2->0->1


def test_parallel_duplicate_edges():
    g = {"a": ["b", "b", "b"], "b": ["c", "c"]}
    assert bfs_shortest_path(g, "a", "c") == 2
    assert bfs_shortest_path(g, "a", "b") == 1


def test_larger_grid_like_graph_minimum_hops():
    # Build a 5x5 grid (undirected) and check Manhattan-ish hop counts.
    def node(r, c):
        return (r, c)

    g = {}
    n = 5
    for r in range(n):
        for c in range(n):
            nbrs = []
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                rr, cc = r + dr, c + dc
                if 0 <= rr < n and 0 <= cc < n:
                    nbrs.append(node(rr, cc))
            g[node(r, c)] = nbrs
    # shortest path on an open grid = Manhattan distance
    assert bfs_shortest_path(g, (0, 0), (4, 4)) == 8
    assert bfs_shortest_path(g, (0, 0), (0, 0)) == 0
    assert bfs_shortest_path(g, (2, 2), (2, 4)) == 2


def test_goal_only_as_neighbour_never_a_key():
    # 'd' only appears as a neighbour, never as a key (sink node)
    g = {"a": ["b"], "b": ["d"]}
    assert bfs_shortest_path(g, "a", "d") == 2
    assert bfs_shortest_path(g, "d", "a") == -1


def test_integer_nodes_and_zero_node():
    g = {0: [1, 2], 1: [3], 2: [3], 3: []}
    assert bfs_shortest_path(g, 0, 3) == 2
    assert bfs_shortest_path(g, 3, 0) == -1
