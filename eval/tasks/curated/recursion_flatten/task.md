# recursion_flatten — Flatten an arbitrarily nested list of ints

## Goal
Implement two functions in `flatten.py` that recursively flatten nested lists
of integers.

### `flatten(nested) -> list`
Return a new flat list containing every integer in `nested` in left-to-right
(depth-first) order. `nested` is a list whose elements are each either an `int`
or another arbitrarily-nested list of the same kind. Nesting may be arbitrarily
deep.

### `flatten_depth(nested, depth) -> list`
Like `flatten`, but unwrap at most `depth` levels of nesting. `depth == 0`
returns a shallow copy (no unwrapping); `depth == 1` splices in only the top
level of sublists; deeper nesting beyond `depth` is left intact in the output.

### Specification
- Only `list` counts as a nestable container. Tuples, sets, strings, dicts, and
  other iterables are **not** containers — they are leaves.
- Every leaf reached must be an `int`, and `bool` (a subclass of `int`) must be
  **rejected**: any `bool` leaf, or any leaf that is neither a `list` nor a
  non-`bool` `int`, raises `TypeError`. The top-level argument must be a `list`
  (else `TypeError`).
- Empty lists at any depth contribute nothing.
- For `flatten_depth`, `depth` must be an `int` with `depth >= 0` (a `bool` is
  not a valid `depth`), else `ValueError`. Elements left nested **beyond**
  `depth` are preserved untouched and are **not** inspected for leaf validity.
- Neither function mutates its input; both return a new list.

### Examples
```
flatten([1, [2, [3, 4], 5], [[6]], 7]) == [1, 2, 3, 4, 5, 6, 7]
flatten([])                            == []
flatten([[], [[]], [[[]]]])            == []
flatten([1, [2, [3, [4, [5]]]]])       == [1, 2, 3, 4, 5]
flatten([True])                        -> TypeError

flatten_depth([1, [2, [3, [4]]]], 0)   == [1, [2, [3, [4]]]]
flatten_depth([1, [2, [3, [4]]]], 1)   == [1, 2, [3, [4]]]
flatten_depth([1, [2, [3, [4]]]], 2)   == [1, 2, 3, [4]]
flatten_depth([1, [2, [3, [4]]]], 99)  == [1, 2, 3, 4]
flatten_depth([1, [True]], 0)          == [1, [True]]   # buried bool not inspected
flatten_depth([1, [True]], 1)          -> TypeError      # cut depth reaches it
```

### Constraints / notes
- Pure standard library only. Solve via recursion over the nested structure;
  do not rely on string conversion or third-party flatten helpers.
- Must handle deeply nested input (hundreds of levels) correctly.

## Category
recursion

## Difficulty
hard

## Tests
hidden

## Source/License
Authored for coding-agent eval. MIT.
