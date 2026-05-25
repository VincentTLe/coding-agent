# dp_edit_distance — Levenshtein edit distance

## Goal
Implement `edit_distance(a: str, b: str) -> int` in `edit_distance.py`.

Return the **Levenshtein edit distance** between strings `a` and `b`: the
minimum number of single-character edits needed to transform `a` into `b`.
The three allowed edit operations, each of cost **1**, are:

- **insert** a single character,
- **delete** a single character,
- **substitute** one character with another.

### Specification
- Input: two strings `a` and `b` (each possibly empty). Characters may be any
  Unicode characters; comparison is case-sensitive (`'A' != 'a'`).
- Output: a single non-negative `int`, the minimum total edit cost.
- The metric is **symmetric**: `edit_distance(a, b) == edit_distance(b, a)`.
- If the two strings are equal, the distance is `0`.
- If one string is empty, the distance equals the length of the other (all
  inserts or all deletes).
- A substitution counts as a single edit (cost 1), never as a delete + insert.

### Examples
```
edit_distance("kitten", "sitting")  == 3   # k→s, e→i, +g
edit_distance("flaw", "lawn")       == 2   # delete f, append n
edit_distance("sunday", "saturday") == 3
edit_distance("", "")               == 0
edit_distance("abc", "")            == 3
edit_distance("abc", "abc")         == 0
edit_distance("a", "b")             == 1
edit_distance("intention", "execution") == 5
```

### Constraints / notes
- Pure standard library only.
- Must run efficiently for strings up to a few hundred characters (an
  O(len(a) * len(b)) dynamic-programming solution is expected; do not
  enumerate all edit sequences).
- Do not mutate the inputs.

## Category
dp

## Difficulty
hard

## Tests
hidden

## Source/License
Authored for coding-agent eval. MIT.
