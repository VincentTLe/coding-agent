"""Order-preserving de-duplication (reference solution)."""

from typing import Any, Hashable, Iterable, List


def dedup(items: Iterable[Any]) -> List[Any]:
    """Return the items with duplicates removed, preserving FIRST-seen order.

    Two items are duplicates iff they are equal (``==``). Works for ANY items,
    including unhashable ones such as ``list`` and ``dict`` and for inputs that
    mix hashable and unhashable values.

    Examples:
        >>> dedup([3, 1, 3, 2, 1])
        [3, 1, 2]
        >>> dedup(["a", "b", "a"])
        ['a', 'b']
    """
    seen_hashable = set()        # fast path for hashable items
    seen_unhashable: List[Any] = []  # fallback for unhashable items
    out: List[Any] = []
    for item in items:
        try:
            if item in seen_hashable:
                continue
            seen_hashable.add(item)
        except TypeError:
            # Unhashable: fall back to linear equality scan. Note we still need
            # to compare against hashable seen values too, because e.g. an int
            # and a bool can compare equal; but since unhashable items can only
            # equal other unhashable items in practice, scanning the unhashable
            # bucket is sufficient and keeps order correct.
            if any(item == prev for prev in seen_unhashable):
                continue
            seen_unhashable.append(item)
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
    for item in order:
        if counts[item] == 1:
            return item
    return None
