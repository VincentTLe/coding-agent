import pytest

from flatten import flatten, flatten_depth


# ------------------------------------------------------------------- flatten

def test_basic_mixed_nesting():
    assert flatten([1, [2, [3, 4], 5], [[6]], 7]) == [1, 2, 3, 4, 5, 6, 7]


def test_empty_list():
    assert flatten([]) == []


def test_only_empty_nested():
    assert flatten([[], [[]], [[[]]]]) == []
    assert flatten([[[], []], []]) == []


def test_single_int_wrapped():
    assert flatten([42]) == [42]
    assert flatten([[[[[42]]]]]) == [42]


def test_left_to_right_order_preserved():
    assert flatten([[3, 2], 1, [[0, -1]]]) == [3, 2, 1, 0, -1]


def test_duplicates_kept():
    assert flatten([1, [1, [1]], 1]) == [1, 1, 1, 1]


def test_negative_and_zero():
    assert flatten([0, [-1, [-2]], 0]) == [0, -1, -2, 0]


def test_does_not_mutate_input():
    src = [1, [2, [3]], 4]
    snapshot = [1, [2, [3]], 4]
    flatten(src)
    assert src == snapshot


def test_returns_new_list():
    src = [1, 2, 3]
    out = flatten(src)
    assert out == [1, 2, 3]
    assert out is not src


def test_bool_leaf_rejected():
    # bool is a subclass of int but must NOT be accepted as an integer leaf.
    with pytest.raises(TypeError):
        flatten([True])
    with pytest.raises(TypeError):
        flatten([1, [2, False], 3])


def test_non_int_leaf_rejected():
    for bad in ([1.0], ["x"], [(1, 2)], [{1: 2}], [None], [{1, 2}]):
        with pytest.raises(TypeError):
            flatten(bad)


def test_non_list_top_level_rejected():
    with pytest.raises(TypeError):
        flatten(5)
    with pytest.raises(TypeError):
        flatten("abc")


def test_deeply_nested_does_not_overflow_for_reasonable_depth():
    # Build [[[...[1]...]]] nested 800 deep; a correct recursion handles it.
    depth = 800
    node = [1]
    for _ in range(depth):
        node = [node]
    assert flatten(node) == [1]


def test_wide_input():
    src = [[i, [i + 1]] for i in range(0, 2000, 2)]
    expected = list(range(2000))
    assert flatten(src) == expected


# -------------------------------------------------------------- flatten_depth

def test_depth_zero_is_shallow_copy():
    src = [1, [2, [3, [4]]]]
    out = flatten_depth(src, 0)
    assert out == [1, [2, [3, [4]]]]
    assert out is not src


def test_depth_one():
    assert flatten_depth([1, [2, [3, [4]]]], 1) == [1, 2, [3, [4]]]
    assert flatten_depth([[1, 2], [3, 4]], 1) == [1, 2, 3, 4]


def test_depth_two():
    assert flatten_depth([1, [2, [3, [4]]]], 2) == [1, 2, 3, [4]]


def test_depth_large_fully_flattens():
    assert flatten_depth([1, [2, [3, [4]]]], 99) == [1, 2, 3, 4]
    assert flatten_depth([1, [2, [3, [4]]]], 99) == flatten([1, [2, [3, [4]]]])


def test_depth_preserved_nesting_not_inspected():
    # A bool buried below the cut depth is preserved untouched, not validated.
    assert flatten_depth([1, [True]], 0) == [1, [True]]
    # But once the cut depth reaches it, the bool leaf is rejected.
    with pytest.raises(TypeError):
        flatten_depth([1, [True]], 1)


def test_depth_validation():
    with pytest.raises(ValueError):
        flatten_depth([1, 2], -1)
    with pytest.raises(ValueError):
        flatten_depth([1, 2], True)  # bool is not a valid depth
    with pytest.raises(ValueError):
        flatten_depth([1, 2], 1.5)


def test_depth_does_not_mutate_input():
    src = [1, [2, [3]]]
    snapshot = [1, [2, [3]]]
    flatten_depth(src, 1)
    assert src == snapshot
