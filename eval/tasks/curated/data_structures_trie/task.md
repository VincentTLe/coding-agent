# data_structures_trie — Prefix tree (Trie)

## Goal
Implement the `Trie` class in `trie.py`: a prefix tree storing a set of
strings. Replace every `NotImplementedError` with a correct implementation
matching the contract below. Operations are case-sensitive and must accept any
characters (including unicode and the empty string).

### API
- `Trie()` — create an empty trie (zero words).
- `insert(word) -> None` — add `word`. Inserting the same word twice is
  idempotent: the second insert must not increase `__len__`.
- `search(word) -> bool` — True iff `word` was inserted **as a complete word**
  (not merely as a prefix of some other inserted word).
- `starts_with(prefix) -> bool` — True iff **some inserted word** begins with
  `prefix`. Every inserted word is a prefix of itself. `starts_with("")` is
  True whenever the trie is non-empty (and False when empty).
- `delete(word) -> bool` — remove `word` if present; return True if something
  was removed, else False. Deleting must not affect other words sharing a
  prefix, and must prune nodes so a prefix that *only* led to the deleted word
  is no longer reported by `starts_with`.
- `words_with_prefix(prefix) -> list[str]` — all inserted words starting with
  `prefix`, sorted lexicographically. `prefix=""` returns every word, sorted.
  No match returns `[]`.
- `__len__() -> int` — number of distinct words currently stored.

### Key distinctions to get right
- A prefix that was never inserted as a word makes `search` False but
  `starts_with` True (e.g. insert "apple"; `search("app")` is False,
  `starts_with("app")` is True).
- The **empty string** can be inserted as a word: then `search("")` is True.
- After deleting the only word under a branch, that branch's prefixes must stop
  matching, but a still-present word on a shared branch must keep matching.

### Examples
```
t = Trie()
t.insert("apple")
t.search("apple")        # -> True
t.search("app")          # -> False  (prefix, not an inserted word)
t.starts_with("app")     # -> True
t.insert("app")
t.search("app")          # -> True
len(t)                   # -> 2
t.words_with_prefix("ap")# -> ["app", "apple"]
t.delete("app")          # -> True
t.search("app")          # -> False
t.search("apple")        # -> True   (unaffected)
t.starts_with("appl")    # -> True
len(t)                   # -> 1
```

## Category
data_structures

## Difficulty
hard

## Tests
hidden

## Source/License
Authored for coding-agent eval. MIT.
