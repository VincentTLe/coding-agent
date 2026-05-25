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
    wset = set(words)
    n = len(s)
    if n == 0:
        return True
    # Only word lengths present in the dictionary are worth trying; this keeps
    # the inner loop tight even for big dictionaries.
    lengths = sorted({len(w) for w in wset if 0 < len(w) <= n})
    if not lengths:
        return False

    # dp[i] = True iff s[:i] can be segmented. dp[0] = True (empty prefix).
    dp = [False] * (n + 1)
    dp[0] = True
    for i in range(1, n + 1):
        for L in lengths:
            if L > i:
                break  # lengths is sorted ascending; no longer fits
            if dp[i - L] and s[i - L:i] in wset:
                dp[i] = True
                break
    return dp[n]
