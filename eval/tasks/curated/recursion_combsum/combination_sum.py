def combination_sum(candidates, target):
    """Return every unique combination of ``candidates`` that sums to ``target``.

    ``candidates`` is a list of positive integers and ``target`` is an integer.
    Find all unique multisets of candidate values whose sum is exactly
    ``target``. The **same candidate value may be chosen any number of times**
    (including zero). Two combinations are the same if they contain the same
    values the same number of times, regardless of order.

    Output format (must match exactly)
    ----------------------------------
    - Each combination is a ``list`` of ints sorted in **non-decreasing** order.
    - The returned value is a ``list`` of such combinations, sorted in ascending
      lexicographic order (compare the sorted combinations element by element).
    - With ``target == 0`` there is exactly one combination, the empty one, so
      return ``[[]]``.
    - If no combination sums to ``target`` (e.g. ``target`` negative, or no
      candidate small enough), return ``[]``.

    Input rules
    -----------
    - ``candidates`` must contain only positive integers (``> 0``); a value
      ``<= 0`` (including ``0`` and any ``bool``) raises ``ValueError``.
    - ``target`` must be an ``int`` (not a ``bool``); otherwise raise
      ``ValueError``.
    - Duplicate values in ``candidates`` must not produce duplicate
      combinations: deduplicate the candidate set first.
    - ``candidates`` must not be mutated.

    Examples
    --------
    >>> combination_sum([2, 3, 6, 7], 7)
    [[2, 2, 3], [7]]
    >>> combination_sum([2, 3, 5], 8)
    [[2, 2, 2, 2], [2, 3, 3], [3, 5]]
    >>> combination_sum([2], 1)
    []
    >>> combination_sum([3, 5, 8], 0)
    [[]]
    """
    raise NotImplementedError
