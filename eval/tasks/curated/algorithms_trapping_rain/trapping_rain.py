def trap(heights):
    """Return the total units of water trapped after raining over an elevation map.

    ``heights`` is a list of non-negative integers where ``heights[i]`` is the
    height of a unit-width bar at position ``i``. After rain, water collects in
    the valleys between taller bars. Return the total amount of trapped water.

    For any index ``i`` the water that rests on top of bar ``i`` equals
    ``min(max(heights[:i+1]), max(heights[i:])) - heights[i]`` when that
    quantity is positive, and ``0`` otherwise. The answer is the sum of trapped
    water over all indices.

    Rules
    -----
    - ``heights`` contains non-negative integers. If any element is negative,
      raise ``ValueError``.
    - An empty list, a single bar, or two bars trap ``0`` (no valley can hold
      water).
    - Water never spills past the ends of the array; the leftmost and rightmost
      bars act as the only outer walls.
    - ``heights`` must not be mutated.

    The expected approach runs in O(len(heights)) time and O(1) extra space
    (the two-pointer technique), not the O(n) extra-array prefix/suffix method
    and certainly not an O(n^2) per-index scan.

    Examples
    --------
    >>> trap([0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1])
    6
    >>> trap([4, 2, 0, 3, 2, 5])
    9
    >>> trap([1, 2, 3])
    0
    >>> trap([])
    0
    """
    raise NotImplementedError
