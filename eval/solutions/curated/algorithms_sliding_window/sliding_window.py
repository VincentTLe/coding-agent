def _validate(nums, k):
    n = len(nums)
    if not isinstance(k, int) or isinstance(k, bool):
        raise ValueError("k must be an int")
    if n == 0 or k < 1 or k > n:
        raise ValueError("k must satisfy 1 <= k <= len(nums)")


def max_subarray_sum_k(nums, k):
    """Return the maximum sum of any contiguous subarray of length exactly ``k``."""
    _validate(nums, k)
    window = sum(nums[:k])
    best = window
    for i in range(k, len(nums)):
        window += nums[i] - nums[i - k]
        if window > best:
            best = window
    return best


def first_max_window_start(nums, k):
    """Return the start index of the leftmost maximum-sum window of length ``k``."""
    _validate(nums, k)
    window = sum(nums[:k])
    best = window
    best_start = 0
    for i in range(k, len(nums)):
        start = i - k + 1
        window += nums[i] - nums[i - k]
        if window > best:
            best = window
            best_start = start
    return best_start
