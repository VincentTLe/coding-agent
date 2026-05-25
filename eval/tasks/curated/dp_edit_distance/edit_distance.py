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
    raise NotImplementedError
