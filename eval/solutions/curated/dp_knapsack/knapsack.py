def knapsack(weights: list, values: list, capacity: int) -> int:
    """Solve the 0/1 knapsack problem: maximum value within ``capacity``.

    You are given ``weights[i]`` and ``values[i]`` for ``n`` items, and an
    integer ``capacity``. Choose a subset of the items so that the total
    weight does not exceed ``capacity`` and the total value is maximised.
    Each item may be taken at most once (0/1, not fractional, not unbounded).
    Return the maximum achievable total value.

    Examples
    --------
    >>> knapsack([1, 3, 4, 5], [1, 4, 5, 7], 7)
    9
    >>> knapsack([2, 3, 4], [3, 4, 5], 5)
    7
    >>> knapsack([], [], 10)
    0
    >>> knapsack([5], [10], 4)
    0
    """
    if capacity < 0:
        return 0

    # 1D space-optimized DP. dp[c] = best value with total weight <= c.
    dp = [0] * (capacity + 1)
    base = 0  # value contributed by zero-weight items (always free to take)

    for w, v in zip(weights, values):
        if w == 0:
            # A zero-weight item never consumes capacity; if its value is
            # positive it is always worth taking. (Negative values aren't in
            # the spec, but max(0, v) keeps it safe.)
            base += max(0, v)
            continue
        if w > capacity:
            continue  # cannot ever fit
        # Iterate capacities downward so each item is used at most once.
        for c in range(capacity, w - 1, -1):
            cand = dp[c - w] + v
            if cand > dp[c]:
                dp[c] = cand

    return dp[capacity] + base
