"""Hidden tests for UnionFind. Exercise merge logic, counts, sizes, partition."""

import random

import pytest

from union_find import UnionFind


def test_empty():
    uf = UnionFind()
    assert uf.count == 0
    assert uf.groups() == []


def test_add_singletons():
    uf = UnionFind()
    uf.add(1)
    uf.add(2)
    uf.add(3)
    assert uf.count == 3
    assert uf.connected(1, 2) is False
    assert uf.size(1) == 1


def test_add_idempotent():
    uf = UnionFind()
    uf.add(1)
    uf.add(1)
    uf.add(1)
    assert uf.count == 1
    assert uf.size(1) == 1


def test_find_creates_singleton():
    uf = UnionFind()
    assert uf.find(7) == 7  # unseen -> its own representative
    assert uf.count == 1
    assert uf.size(7) == 1


def test_find_self_representative():
    uf = UnionFind()
    uf.add("x")
    assert uf.find("x") == "x"


def test_union_returns_bool():
    uf = UnionFind()
    uf.add(1)
    uf.add(2)
    assert uf.union(1, 2) is True
    assert uf.union(1, 2) is False  # already merged
    assert uf.union(2, 1) is False  # order-independent


def test_union_connects():
    uf = UnionFind()
    uf.union(1, 2)
    assert uf.connected(1, 2) is True
    assert uf.connected(2, 1) is True
    assert uf.find(1) == uf.find(2)


def test_union_lazily_adds_elements():
    uf = UnionFind()
    assert uf.union(10, 20) is True  # neither seen before
    assert uf.count == 1
    assert uf.connected(10, 20) is True
    assert uf.size(10) == 2


def test_count_decreases_on_merge():
    uf = UnionFind()
    for i in range(5):
        uf.add(i)
    assert uf.count == 5
    uf.union(0, 1)
    assert uf.count == 4
    uf.union(2, 3)
    assert uf.count == 3
    uf.union(0, 2)
    assert uf.count == 2  # {0,1,2,3} and {4}


def test_count_unchanged_on_redundant_merge():
    uf = UnionFind()
    uf.union(1, 2)
    assert uf.count == 1
    uf.union(1, 2)
    uf.union(2, 1)
    assert uf.count == 1


def test_transitive_union():
    uf = UnionFind()
    uf.union("a", "b")
    uf.union("b", "c")
    assert uf.connected("a", "c") is True
    assert uf.find("a") == uf.find("c")
    assert uf.size("a") == 3
    assert uf.size("b") == 3
    assert uf.size("c") == 3
    assert uf.count == 1


def test_size_sums_after_merge():
    uf = UnionFind()
    uf.union(1, 2)
    uf.union(3, 4)
    uf.union(4, 5)
    assert uf.size(1) == 2
    assert uf.size(3) == 3
    uf.union(2, 5)  # merge a 2-set and a 3-set
    for x in (1, 2, 3, 4, 5):
        assert uf.size(x) == 5
    assert uf.count == 1


def test_size_unseen_is_one():
    uf = UnionFind()
    assert uf.size("ghost") == 1
    assert uf.count == 1


def test_separate_sets_stay_separate():
    uf = UnionFind()
    uf.union(1, 2)
    uf.union(3, 4)
    assert uf.connected(1, 3) is False
    assert uf.connected(2, 4) is False
    assert uf.find(1) != uf.find(3)
    assert uf.count == 2


def test_groups_partition():
    uf = UnionFind()
    for i in range(1, 7):
        uf.add(i)
    uf.union(1, 2)
    uf.union(2, 3)
    uf.union(4, 5)
    # sets: {1,2,3}, {4,5}, {6}
    assert uf.groups() == [[1, 2, 3], [4, 5], [6]]
    assert uf.count == 3


def test_groups_single_set():
    uf = UnionFind()
    uf.union(3, 1)
    uf.union(1, 2)
    assert uf.groups() == [[1, 2, 3]]


def test_groups_reflects_count():
    uf = UnionFind()
    for i in range(10):
        uf.add(i)
    uf.union(0, 9)
    uf.union(1, 8)
    uf.union(0, 1)
    groups = uf.groups()
    assert len(groups) == uf.count
    # union of all group members == all elements, no overlaps
    flat = sorted(x for g in groups for x in g)
    assert flat == list(range(10))


def test_representative_stable_within_set():
    uf = UnionFind()
    uf.union(1, 2)
    uf.union(2, 3)
    r = uf.find(1)
    assert uf.find(2) == r
    assert uf.find(3) == r
    # find must be repeatable / stable for the current partition
    assert uf.find(1) == r


def test_string_elements():
    uf = UnionFind()
    uf.union("apple", "banana")
    uf.union("cherry", "date")
    assert uf.connected("apple", "banana") is True
    assert uf.connected("apple", "cherry") is False
    uf.union("banana", "date")
    assert uf.connected("apple", "date") is True
    assert uf.size("apple") == 4
    assert uf.count == 1


def test_large_chain_then_query():
    # A long chain stresses path compression; correctness must hold regardless.
    uf = UnionFind()
    n = 1000
    for i in range(n - 1):
        uf.union(i, i + 1)
    assert uf.count == 1
    assert uf.connected(0, n - 1) is True
    assert uf.size(0) == n
    r = uf.find(0)
    assert all(uf.find(i) == r for i in range(n))


def test_randomized_against_reference():
    rng = random.Random(31337)
    n = 60
    uf = UnionFind()
    for i in range(n):
        uf.add(i)
    # Brute-force reference partition via labels.
    label = list(range(n))

    def ref_connected(a, b):
        return label[a] == label[b]

    def ref_union(a, b):
        if label[a] == label[b]:
            return False
        old, new = label[b], label[a]
        for k in range(n):
            if label[k] == old:
                label[k] = new
        return True

    for _ in range(2000):
        a, b = rng.randrange(n), rng.randrange(n)
        if rng.random() < 0.5:
            assert uf.union(a, b) == ref_union(a, b)
        else:
            assert uf.connected(a, b) == ref_connected(a, b)
        # count must always equal the number of distinct reference labels
        assert uf.count == len(set(label))

    # Final partition must match exactly.
    expected = {}
    for i in range(n):
        expected.setdefault(label[i], []).append(i)
    expected_groups = sorted(sorted(g) for g in expected.values())
    assert uf.groups() == expected_groups
