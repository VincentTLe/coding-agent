def word_break(s: str, words: list) -> bool:
    """Return True iff ``s`` can be segmented into dictionary words.

    Given a string ``s`` and a list ``words`` of dictionary words, return
    ``True`` if ``s`` can be split into a sequence of dictionary words
    concatenated with no gaps and no leftover characters. Each dictionary word
    may be reused any number of times. The empty string is the empty
    concatenation and returns ``True``. Return ``False`` otherwise.

    Examples
    --------
    >>> word_break("leetcode", ["leet", "code"])
    True
    >>> word_break("applepenapple", ["apple", "pen"])
    True
    >>> word_break("catsandog", ["cats", "dog", "sand", "and", "cat"])
    False
    >>> word_break("", ["a", "b"])
    True
    """
    raise NotImplementedError
