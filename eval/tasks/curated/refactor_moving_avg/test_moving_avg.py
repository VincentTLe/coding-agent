import random

import pytest

from moving_avg import moving_average


def _brute_force(data, k):
    """Independent clamped-window reference for the property test."""
    out = []
    for i in range(len(data)):
        lo = max(0, i - k + 1)
        window = data[lo:i + 1]
        out.append(sum(window) / len(window))
    return out


def test_length_matches_input():
    for n in range(0, 8):
        data = list(range(n))
        assert len(moving_average(data, 3)) == n


def test_basic_window_two():
    assert moving_average([1, 2, 3, 4], 2) == [1.0, 1.5, 2.5, 3.5]


def test_boundary_warmup_values():
    # The first k-1 outputs use a growing window, not a divide-by-k.
    assert moving_average([2, 4, 6, 8], 3) == [2.0, 3.0, 4.0, 6.0]


def test_window_larger_than_data():
    # Every position averages everything seen so far.
    assert moving_average([10, 20, 30], 5) == [10.0, 15.0, 20.0]


def test_window_one_is_identity():
    assert moving_average([3, 1, 4, 1, 5], 1) == [3.0, 1.0, 4.0, 1.0, 5.0]


def test_empty():
    assert moving_average([], 4) == []


def test_invalid_k_raises():
    with pytest.raises(ValueError):
        moving_average([1, 2, 3], 0)
    with pytest.raises(ValueError):
        moving_average([1, 2, 3], -2)


def test_first_value_is_first_element():
    # No wraparound: output[0] must equal data[0], never pull from the tail.
    assert moving_average([100, 1, 1, 1], 3)[0] == 100.0


def test_matches_brute_force_random():
    rng = random.Random(424242)
    for _ in range(300):
        n = rng.randint(0, 12)
        data = [rng.randint(-5, 20) for _ in range(n)]
        k = rng.randint(1, 6)
        expected = _brute_force(data, k)
        got = moving_average(data, k)
        assert len(got) == len(expected)
        for a, b in zip(got, expected):
            assert abs(a - b) < 1e-9
