"""A small string tokenizer (reference solution)."""

from typing import List


def tokenize(text: str, delimiters: str = " ,") -> List[str]:
    """Split ``text`` into tokens on any character in ``delimiters``.

    Contract:
      * Runs of one or more delimiter characters act as a single separator, so
        the result NEVER contains empty strings (``"a,,b"`` -> ``["a", "b"]``).
      * Leading and trailing delimiters are ignored.
      * A double-quoted substring (``"..."``) is a single token and any
        delimiter characters inside the quotes are kept literally. The quote
        characters are stripped from the emitted token. A quote may appear in
        the middle of a token, e.g. ``a" b"c`` -> ``a bc``.
      * An empty or all-delimiter string yields ``[]``.

    Examples:
        >>> tokenize("a, b,c")
        ['a', 'b', 'c']
        >>> tokenize('say "hello world" now')
        ['say', 'hello world', 'now']
    """
    delim = set(delimiters)
    tokens: List[str] = []
    current: List[str] = []
    have_token = False  # distinguishes "" (an explicit empty quoted token) from no token
    in_quotes = False

    for ch in text:
        if ch == '"':
            in_quotes = not in_quotes
            have_token = True  # entering/leaving quotes starts a token even if empty
            continue
        if in_quotes:
            current.append(ch)
            have_token = True
            continue
        if ch in delim:
            if have_token:
                tokens.append("".join(current))
                current = []
                have_token = False
        else:
            current.append(ch)
            have_token = True

    if have_token:
        tokens.append("".join(current))
    return tokens
