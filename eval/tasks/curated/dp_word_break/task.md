# dp_word_break — segment a string into dictionary words

## Goal
Implement `word_break(s: str, words: list) -> bool` in `word_break.py`.

Given a string `s` and a list `words` of dictionary words, return `True` if
`s` can be segmented into a sequence of dictionary words concatenated with **no
gaps and no leftover characters**, and `False` otherwise. Dictionary words may
be **reused any number of times**.

### Specification
- Input:
  - `s`: the string to segment (possibly empty). Comparison is exact and
    case-sensitive.
  - `words`: a list of non-empty dictionary words (possibly empty list; may
    contain duplicates, which are irrelevant).
- Output: a `bool`.
- A valid segmentation is a sequence of words `w1, w2, ..., wk` (each `wi` in
  the dictionary, `k >= 0`) such that `w1 + w2 + ... + wk == s`.
- **Empty string**: `s == ""` is the empty concatenation (`k == 0`), so
  `word_break("", words)` is **`True`** for any `words` (including an empty
  dictionary).
- If `s` is non-empty and `words` is empty, the result is `False`.
- Whole-string match: if `s` itself is a dictionary word, the result is
  `True`.
- A correct solution must consider **all** ways to split `s`; a single greedy
  longest-prefix (or shortest-prefix) match is **not** sufficient. For example
  `word_break("catsandog", ["cats", "dog", "sand", "and", "cat"])` is `False`
  even though several prefixes match dictionary words.

### Examples
```
word_break("leetcode", ["leet", "code"])                         == True
word_break("applepenapple", ["apple", "pen"])                    == True
word_break("catsandog", ["cats", "dog", "sand", "and", "cat"])   == False
word_break("", ["a", "b"])                                       == True
word_break("", [])                                               == True
word_break("a", [])                                              == False
word_break("aaaaaaa", ["aaa", "aaaa"])                           == True
word_break("aaaaaaab", ["aaa", "aaaa"])                          == False
word_break("cars", ["car", "ca", "rs"])                          == True
word_break("Apple", ["apple", "pen"])                            == False   # case-sensitive
```

### Constraints / notes
- Pure standard library only.
- `s` may be up to a few hundred characters and the dictionary may hold many
  words; an O(len(s)^2) (or O(len(s) * dict) ) dynamic-programming /
  memoized solution is expected. A naive solution that re-explores the same
  suffixes exponentially will time out on adversarial inputs such as
  `"aaaa...a" + "b"` against `["a", "aa", "aaa", ...]`.
- Do not mutate the inputs.

## Category
dp

## Difficulty
hard

## Tests
hidden

## Source/License
Authored for coding-agent eval. MIT.
