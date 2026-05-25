# data_structures_unionfind — Disjoint Set Union (Union-Find)

## Goal
Implement the `UnionFind` class in `union_find.py`: a disjoint-set structure
over hashable elements with **path compression** and **union by rank/size**.
Replace every `NotImplementedError` with a correct implementation matching the
contract below. Elements are added lazily on first reference.

### API
- `UnionFind()` — create an empty structure (no elements, `count == 0`).
- `find(x) -> representative` — return the canonical representative of `x`'s
  set. If `x` is unseen, add it as its own singleton first. Two elements return
  the same representative **iff** they are in the same set. Apply **path
  compression** while resolving.
- `union(x, y) -> bool` — merge the sets of `x` and `y`. Return `True` if they
  were in different sets (a merge occurred) or `False` if already together.
  Add unseen elements first. Use **union by rank or size** to keep trees
  shallow. A successful merge decreases `count` by 1.
- `connected(x, y) -> bool` — `True` iff `x` and `y` are in the same set
  (adding unseen elements first).
- `add(x) -> None` — ensure `x` exists as at least a singleton. **Idempotent**:
  re-adding an existing element must not merge or reset it.
- `count` — (property) the number of disjoint sets currently present.
- `size(x) -> int` — number of elements in `x`'s set (adding `x` first if
  unseen, giving 1).
- `groups() -> list[list]` — the current partition: a list of groups, each
  group a list of members **sorted ascending**, and the outer list sorted by
  each group's smallest member. (Assume elements are mutually comparable.)

### Invariants to respect
- `find` must be consistent: `find(x) == find(y)` exactly when `x` and `y` are
  connected. Representatives may be any member of the set, but must be stable
  within a set at any point in time.
- After `union(a, b)`, `connected(a, b)` is `True` and the two sets' sizes add
  up. `count` equals the number of groups returned by `groups()`.
- Union is transitive: union(a,b) then union(b,c) means a, b, c are all
  connected and `size` of any of them is 3.

### Examples
```
uf = UnionFind()
uf.add(1); uf.add(2); uf.add(3)
uf.count                 # -> 3
uf.connected(1, 2)       # -> False
uf.union(1, 2)           # -> True
uf.union(1, 2)           # -> False  (already merged)
uf.connected(1, 2)       # -> True
uf.count                 # -> 2
uf.size(1)               # -> 2
uf.union(2, 3)           # -> True   (transitively links 1,2,3)
uf.connected(1, 3)       # -> True
uf.size(3)               # -> 3
uf.count                 # -> 1
uf.groups()              # -> [[1, 2, 3]]
uf.find(99)              # -> 99 (unseen element becomes its own set)
uf.count                 # -> 2
```

## Category
data_structures

## Difficulty
hard

## Tests
hidden

## Source/License
Authored for coding-agent eval. MIT.
