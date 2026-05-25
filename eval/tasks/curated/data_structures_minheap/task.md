# data_structures_minheap — Binary min-heap

## Goal
Implement the `MinHeap` class in `min_heap.py`: an array-backed binary min-heap
of comparable items. Replace every `NotImplementedError` with a correct,
efficient implementation using your own sift-up / sift-down logic. **Do not use
the `heapq` module** — the tests assert structural invariants your own code
must maintain, and `as_sorted` must not mutate the heap.

### API
- `MinHeap(items=None)` — construct a heap. If `items` is given, bulk-load it in
  **O(n)** using Floyd's build-heap (heapify), not by repeated `push`. The heap
  invariant must hold immediately after construction.
- `push(item) -> None` — insert `item` in **O(log n)**.
- `pop_min() -> item` — remove and return a smallest item in **O(log n)**.
  Raise `IndexError` on an empty heap.
- `peek() -> item` — return a smallest item without removing it, in **O(1)**.
  Raise `IndexError` on an empty heap.
- `__len__() -> int` — number of items currently stored.
- `as_sorted() -> list` — return all items in ascending order **without
  mutating** the heap (the heap must be unchanged and still valid afterwards).

### Heap invariant
Using a 0-based array where node `i` has children at `2*i+1` and `2*i+2`: every
child must be `>=` its parent. Therefore the root (index 0) is always a minimum.
Duplicate values are allowed and must be handled correctly. Items are compared
with `<` only.

### Examples
```
h = MinHeap([5, 3, 8, 1, 9, 2])
h.peek()        # -> 1
len(h)          # -> 6
h.pop_min()     # -> 1
h.pop_min()     # -> 2
h.push(0)
h.peek()        # -> 0
h.as_sorted()   # -> [0, 3, 5, 8, 9]   (heap still has these 5 items)
len(h)          # -> 5

empty = MinHeap()
empty.pop_min() # raises IndexError
```

## Category
data_structures

## Difficulty
hard

## Tests
hidden

## Source/License
Authored for coding-agent eval. MIT.
