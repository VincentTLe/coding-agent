# refactor_tokenize — a delimiter/quote-aware string tokenizer

## Goal
`tokenizer.py` contains `tokenize(text, delimiters=" ,")` which splits a string
into tokens. Its test suite (`test_tokenizer.py`) is currently RED because the
naive implementation mishandles consecutive delimiters and ignores quoting.

Refactor `tokenize` so every test passes, keeping the signature
`tokenize(text: str, delimiters: str = " ,") -> List[str]`.

The contract the tests enforce:
- Any character in `delimiters` separates tokens. A **run** of one or more
  delimiter characters acts as a single separator, so the result NEVER
  contains empty strings from delimiters: `tokenize("a,,b") == ["a", "b"]`.
- Leading and trailing delimiters are ignored: `tokenize(",a,b,") == ["a","b"]`.
- A double-quoted substring is a single token; delimiter characters inside the
  quotes are kept literally and the surrounding quote characters are stripped:
  `tokenize('say "hello world" now') == ["say", "hello world", "now"]`.
- A quote may appear in the middle of a token and joins with the surrounding
  text: `tokenize('a" b"c') == ["a bc"]`.
- An explicitly quoted empty string is a deliberate empty token:
  `tokenize('a "" b') == ["a", "", "b"]`.
- An empty or all-delimiter string yields `[]`.

Read the failing tests, identify the edge cases the current splitter gets
wrong (consecutive/leading/trailing delimiters and quoting), and rewrite the
function — a single-pass character scanner is the natural approach.

## Category
refactor

## Difficulty
hard

## Tests
visible

## Source/License
Authored for coding-agent eval. MIT.
