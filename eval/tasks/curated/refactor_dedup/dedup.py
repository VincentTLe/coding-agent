"""Order-preserving de-duplication.

NOTE (for the agent): the current implementation is fast for hashable items
but crashes on unhashable ones, and the helper below is broken. Run the tests,
read the contract in the docstrings, and refactor so every test passes without
changing the public signatures.
"""

from typing import Any, Hashable, Iterable, List


def dedup(items: Iterable[Any]) -> List[Any]:
    """Return the items with duplicates removed, preserving FIRST-seen order.

    Two items are duplicates iff they are equal (``==``). The function must
    work for ANY items, including unhashable ones such as ``list`` and
    ``dict`` (e.g. ``dedup([[1], [1], [2]]) == [[1], [2]]``), and for inputs
    that mix hashable and unhashable values.

    Examples:
        >>> dedup([3, 1, 3, 2, 1])
        [3, 1, 2]
        >>> dedup(["a", "b", "a"])
        ['a', 'b']
    """
    seen = set()
    out: List[Any] = []
    for item in items:
        # BUG: this raises TypeError on unhashable items (lists, dicts, ...).
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def first_unique(items: Iterable[Hashable]) -> Any:
    """Return the first item that appears exactly once, or ``None`` if every
    item repeats (or the input is empty).

    Examples:
        >>> first_unique([2, 3, 2, 4, 3])
        4
        >>> first_unique([1, 1, 2, 2])

    """
    counts = {}
    order: List[Any] = []
    for item in items:
        if item not in counts:
            counts[item] = 0
            order.append(item)
        counts[item] += 1
    # BUG: returns the first item whose count is NOT one (i.e. the first
    # repeated item) instead of the first item whose count IS one.
    for item in order:
        if counts[item] != 1:
            return item
    return None
