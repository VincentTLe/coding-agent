def coin_change(coins: list, amount: int) -> int:
    """Return the minimum number of coins that sum exactly to ``amount``.

    You are given a list of distinct positive coin denominations and a target
    ``amount``. Each denomination may be used an unlimited number of times.
    Return the fewest number of coins whose values add up to exactly
    ``amount``. If no combination of coins sums to exactly ``amount``, return
    ``-1``.

    Examples
    --------
    >>> coin_change([1, 2, 5], 11)
    3
    >>> coin_change([2], 3)
    -1
    >>> coin_change([1, 2, 5], 0)
    0
    >>> coin_change([186, 419, 83, 408], 6249)
    20
    """
    if amount == 0:
        return 0
    if amount < 0:
        return -1

    INF = amount + 1  # sentinel: more coins than could ever be needed
    # best[a] = minimum coins to make sum `a` exactly.
    best = [0] + [INF] * amount
    for a in range(1, amount + 1):
        for c in coins:
            if c <= a:
                cand = best[a - c] + 1
                if cand < best[a]:
                    best[a] = cand
    return -1 if best[amount] >= INF else best[amount]
