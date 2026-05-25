"""Trailing moving average (reference solution)."""

from typing import List


def moving_average(data: List[float], k: int) -> List[float]:
    """Return the trailing moving average with window size ``k``.

    Contract:
      * The output has the SAME length as ``data``.
      * ``output[i]`` is the mean of indices ``max(0, i - k + 1) .. i``.
      * ``k`` must be a positive integer; raise ``ValueError`` otherwise.
      * An empty ``data`` yields an empty list.

    Examples:
        >>> moving_average([1, 2, 3, 4], 2)
        [1.0, 1.5, 2.5, 3.5]
        >>> moving_average([10, 20, 30], 5)
        [10.0, 15.0, 20.0]
    """
    if not isinstance(k, int) or isinstance(k, bool) or k <= 0:
        raise ValueError("k must be a positive integer")
    out: List[float] = []
    running = 0.0
    for i, x in enumerate(data):
        running += x
        if i >= k:
            running -= data[i - k]
        count = min(i + 1, k)
        out.append(running / count)
    return out
