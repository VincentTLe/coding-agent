def flatten(nested):
    """Recursively flatten an arbitrarily nested list of integers into a flat list.

    ``nested`` is a list whose elements are each either an ``int`` or another
    such (arbitrarily nested) list. Return a new flat ``list`` containing every
    integer, in left-to-right (depth-first) order. Nesting may be arbitrarily
    deep, and there is no bound on depth.

    Rules
    -----
    - Only ``list`` is treated as a nestable container. Tuples, sets, strings,
      and other iterables are NOT containers here.
    - Every leaf must be an ``int``. ``bool`` is a subclass of ``int`` but must
      be REJECTED: encountering a ``bool`` leaf raises ``TypeError``. Any leaf
      that is neither a ``list`` nor a non-``bool`` ``int`` raises
      ``TypeError``.
    - Empty lists (at any depth) contribute nothing.
    - The input must not be mutated; a brand-new list is returned.

    Examples
    --------
    >>> flatten([1, [2, [3, 4], 5], [[6]], 7])
    [1, 2, 3, 4, 5, 6, 7]
    >>> flatten([])
    []
    >>> flatten([[], [[]], [[[]]]])
    []
    >>> flatten([1, [2, [3, [4, [5]]]]])
    [1, 2, 3, 4, 5]
    """
    raise NotImplementedError


def flatten_depth(nested, depth):
    """Flatten ``nested`` by at most ``depth`` levels.

    Like :func:`flatten`, but only unwraps up to ``depth`` levels of nesting.
    With ``depth == 0`` the list is returned as a shallow copy (no unwrapping).
    With ``depth == 1`` only the top level of sublists is spliced in, and so on.
    Any nesting deeper than ``depth`` is preserved as nested lists in the
    output.

    Rules
    -----
    - ``depth`` must be an ``int`` with ``depth >= 0``; otherwise raise
      ``ValueError`` (a ``bool`` is not a valid ``depth``).
    - Container/leaf typing is identical to :func:`flatten`: only ``list`` is a
      container, and any leaf that is reached and is not a ``list`` must be a
      non-``bool`` ``int`` or a ``TypeError`` is raised. Note that elements left
      nested beyond ``depth`` are NOT inspected for validity.
    - The input must not be mutated; a new list is returned.

    Examples
    --------
    >>> flatten_depth([1, [2, [3, [4]]]], 0)
    [1, [2, [3, [4]]]]
    >>> flatten_depth([1, [2, [3, [4]]]], 1)
    [1, 2, [3, [4]]]
    >>> flatten_depth([1, [2, [3, [4]]]], 2)
    [1, 2, 3, [4]]
    >>> flatten_depth([1, [2, [3, [4]]]], 99)
    [1, 2, 3, 4]
    """
    raise NotImplementedError
