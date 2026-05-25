def knapsack(weights: list, values: list, capacity: int) -> int:
    """Solve the 0/1 knapsack problem: maximum value within ``capacity``.

    You are given ``weights[i]`` and ``values[i]`` for ``n`` items, and an
    integer ``capacity``. Choose a subset of the items so that the total
    weight does **not exceed** ``capacity`` and the total value is **maximised**.
    Each item may be taken **at most once** (0/1, not fractional, not
    unbounded). Return the maximum achievable total value.

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
    raise NotImplementedError
