"""Trailing moving average.

NOTE (for the agent): this implementation is correct only in the middle of the
series; it breaks at the window boundaries (the first ``k-1`` positions) and on
a couple of edge cases. Run the tests to see the failing invariants, then
refactor ``moving_average`` without changing its signature.
"""

from typing import List


def moving_average(data: List[float], k: int) -> List[float]:
    """Return the trailing moving average with window size ``k``.

    Contract:
      * The output has the SAME length as ``data`` (one value per input
        element) — there is no "warm-up" trimming.
      * ``output[i]`` is the mean of the window ending at ``i`` and spanning at
        most ``k`` elements: indices ``max(0, i - k + 1) .. i`` inclusive. So
        the first element is just ``data[0]``, the second is the mean of the
        first two, and so on until the window fills up.
      * ``k`` must be a positive integer; raise ``ValueError`` otherwise.
      * An empty ``data`` yields an empty list.

    Examples:
        >>> moving_average([1, 2, 3, 4], 2)
        [1.0, 1.5, 2.5, 3.5]
        >>> moving_average([10, 20, 30], 5)
        [10.0, 15.0, 20.0]
    """
    if k <= 0:
        raise ValueError("k must be a positive integer")
    out: List[float] = []
    for i in range(len(data)):
        # BUG: for i < k-1 the start index i-k+1 is negative, so this slice
        # wraps around from the end of the list, and it always divides by k
        # instead of the actual number of elements in the (clamped) window.
        window = data[i - k + 1:i + 1]
        out.append(sum(window) / k)
    return out
