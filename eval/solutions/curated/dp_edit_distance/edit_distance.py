def edit_distance(a: str, b: str) -> int:
    """Return the Levenshtein edit distance between strings ``a`` and ``b``.

    The edit distance is the minimum number of single-character edits
    required to transform ``a`` into ``b``, where the allowed edits are:

      - insert a single character,
      - delete a single character,
      - substitute one character for another.

    Each edit costs exactly 1. The result is symmetric: the distance from
    ``a`` to ``b`` equals the distance from ``b`` to ``a``.

    Examples
    --------
    >>> edit_distance("kitten", "sitting")
    3
    >>> edit_distance("flaw", "lawn")
    2
    >>> edit_distance("", "")
    0
    >>> edit_distance("abc", "")
    3
    >>> edit_distance("abc", "abc")
    0
    """
    n, m = len(a), len(b)
    # Trivial cases also covered by the loop, but cheap to short-circuit.
    if n == 0:
        return m
    if m == 0:
        return n

    # Space-optimized DP: keep only the previous row of the (n+1)x(m+1) table.
    # prev[j] = edit distance between a[:i-1] and b[:j].
    prev = list(range(m + 1))
    for i in range(1, n + 1):
        cur = [i] + [0] * m
        ai = a[i - 1]
        for j in range(1, m + 1):
            cost = 0 if ai == b[j - 1] else 1
            cur[j] = min(
                prev[j] + 1,        # deletion (drop a[i-1])
                cur[j - 1] + 1,     # insertion (add b[j-1])
                prev[j - 1] + cost,  # match or substitution
            )
        prev = cur
    return prev[m]
