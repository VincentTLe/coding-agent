"""Reference solution for the MinHeap task.

Array-backed binary min-heap with explicit sift-up / sift-down and an O(n)
Floyd build-heap. No dependence on the ``heapq`` module.
"""

from __future__ import annotations

from typing import Iterable, List, Optional


class MinHeap:
    def __init__(self, items: Optional[Iterable] = None) -> None:
        self._data: List = list(items) if items is not None else []
        # Floyd's build-heap: sift down every non-leaf node, O(n).
        for i in range(len(self._data) // 2 - 1, -1, -1):
            self._sift_down(i)

    def _sift_up(self, i: int) -> None:
        data = self._data
        while i > 0:
            parent = (i - 1) // 2
            if data[i] < data[parent]:
                data[i], data[parent] = data[parent], data[i]
                i = parent
            else:
                break

    def _sift_down(self, i: int) -> None:
        data = self._data
        n = len(data)
        while True:
            left = 2 * i + 1
            right = 2 * i + 2
            smallest = i
            if left < n and data[left] < data[smallest]:
                smallest = left
            if right < n and data[right] < data[smallest]:
                smallest = right
            if smallest == i:
                break
            data[i], data[smallest] = data[smallest], data[i]
            i = smallest

    def push(self, item) -> None:
        self._data.append(item)
        self._sift_up(len(self._data) - 1)

    def pop_min(self):
        data = self._data
        if not data:
            raise IndexError("pop_min from an empty heap")
        last = data.pop()
        if not data:
            return last
        root = data[0]
        data[0] = last
        self._sift_down(0)
        return root

    def peek(self):
        if not self._data:
            raise IndexError("peek from an empty heap")
        return self._data[0]

    def __len__(self) -> int:
        return len(self._data)

    def as_sorted(self) -> List:
        # Sort a COPY of the backing array; the heap itself is untouched.
        clone = MinHeap.__new__(MinHeap)
        clone._data = list(self._data)
        out: List = []
        while clone._data:
            out.append(clone.pop_min())
        return out
