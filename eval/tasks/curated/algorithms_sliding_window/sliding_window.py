def max_subarray_sum_k(nums, k):
    """Return the maximum sum of any contiguous subarray of length exactly ``k``.

    Given a list of integers ``nums`` (which may contain negative numbers) and
    a positive integer window length ``k``, consider every contiguous slice of
    ``nums`` having exactly ``k`` elements and return the largest slice sum.

    The intended algorithm is a single linear scan that maintains a running
    window sum (an O(len(nums)) sliding window), not the O(len(nums) * k)
    approach of re-summing every window from scratch.

    Rules
    -----
    - ``k`` must be an ``int`` with ``1 <= k <= len(nums)``. Otherwise raise
      ``ValueError``. In particular, ``k`` larger than ``len(nums)`` and ``k``
      that is ``0`` or negative are invalid, and an empty ``nums`` is always
      invalid (no window fits).
    - The result is the maximum over all windows; when every element is
      negative the answer is simply the least-negative window sum.
    - ``nums`` must not be mutated.

    Examples
    --------
    >>> max_subarray_sum_k([2, 1, 5, 1, 3, 2], 3)
    9
    >>> max_subarray_sum_k([2, 3], 3)
    Traceback (most recent call last):
        ...
    ValueError: ...
    >>> max_subarray_sum_k([-1, -2, -3, -4], 2)
    -3
    >>> max_subarray_sum_k([5], 1)
    5
    """
    raise NotImplementedError


def first_max_window_start(nums, k):
    """Return the start index of the leftmost window of length ``k`` whose sum
    equals ``max_subarray_sum_k(nums, k)``.

    Among all contiguous subarrays of length exactly ``k`` that achieve the
    maximum window sum, return the smallest (leftmost) starting index. The same
    validation rules as :func:`max_subarray_sum_k` apply: invalid ``k`` raises
    ``ValueError``.

    ``nums`` must not be mutated.

    Examples
    --------
    >>> first_max_window_start([2, 1, 5, 1, 3, 2], 3)
    2
    >>> first_max_window_start([1, 1, 1, 1], 2)
    0
    >>> first_max_window_start([4, 4, 4, 1], 1)
    0
    """
    raise NotImplementedError
