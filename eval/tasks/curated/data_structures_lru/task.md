# data_structures_lru — Least-Recently-Used cache

## Goal
Implement the `LRUCache` class in `lru_cache.py` so that it behaves as a
fixed-capacity cache evicting the **least-recently-used** entry. The stub
methods currently raise `NotImplementedError`; replace each with a correct,
efficient implementation.

### API
- `LRUCache(capacity: int)` — construct a cache holding at most `capacity`
  entries. A `capacity` less than 1 must raise `ValueError`.
- `get(key) -> value | None` — return the value for `key`, or `None` if the key
  is not present. A **hit counts as a use**: it makes `key` the
  most-recently-used entry.
- `put(key, value) -> None` — insert or update `key`. If the key already
  exists, overwrite its value. In both cases `key` becomes the
  most-recently-used entry. If inserting a *new* key would exceed `capacity`,
  evict the **least-recently-used** key first.
- `__contains__(key) -> bool` — membership test (`key in cache`). This is a
  pure query and must **NOT** change recency order.
- `__len__() -> int` — current number of cached entries.

### Recency semantics
"Recently used" is defined by both `get` (on a hit) and `put`. The entry
touched most recently is the *last* to be evicted; the one untouched longest is
evicted first. Updating an existing key via `put` refreshes its recency.

### Complexity
`get`, `put`, `__contains__`, and `__len__` must each run in **O(1)** average
time (use a dict plus a doubly-linked list, or `collections.OrderedDict`). A
solution that scans all entries to find the LRU victim is too slow and may
violate ordering invariants tested here.

### Examples
```
c = LRUCache(2)
c.put("a", 1)
c.put("b", 2)
c.get("a")        # -> 1   (now "a" is most-recent, "b" is LRU)
c.put("c", 3)     # evicts "b"
c.get("b")        # -> None
c.get("a")        # -> 1
len(c)            # -> 2
"a" in c          # -> True  (does not change recency)
c.put("d", 4)     # evicts "c" (LRU), not "a"
c.get("c")        # -> None
c.get("a")        # -> 1
```

## Category
data_structures

## Difficulty
hard

## Tests
hidden

## Source/License
Authored for coding-agent eval. MIT.
