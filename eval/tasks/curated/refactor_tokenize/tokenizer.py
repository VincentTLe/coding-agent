"""A small string tokenizer.

NOTE (for the agent): the current tokenizer mishandles consecutive delimiters
and ignores quoting entirely. Run the tests to see the failing invariants,
then refactor `tokenize` to satisfy the documented contract without changing
its signature.
"""

from typing import List


def tokenize(text: str, delimiters: str = " ,") -> List[str]:
    """Split ``text`` into tokens on any character in ``delimiters``.

    Contract:
      * Runs of one or more delimiter characters act as a single separator, so
        the result NEVER contains empty strings (``"a,,b"`` -> ``["a", "b"]``).
      * Leading and trailing delimiters are ignored (no empty tokens at the
        ends).
      * A double-quoted substring (``"..."``) is a single token and any
        delimiter characters inside the quotes are kept literally. The
        surrounding quote characters are stripped from the emitted token. A
        quote can also appear in the middle of a token, e.g.
        ``a" b"c`` -> ``a bc``.
      * An empty or all-delimiter string yields ``[]``.

    Examples:
        >>> tokenize("a, b,c")
        ['a', 'b', 'c']
        >>> tokenize('say "hello world" now')
        ['say', 'hello world', 'now']
    """
    # BUG 1: splits on every delimiter char individually, emitting empty
    # strings for consecutive/leading/trailing delimiters.
    # BUG 2: quotes are treated like any other character, so delimiters inside
    # quotes still split the token and the quote chars leak into the output.
    tokens = [text]
    for d in delimiters:
        nxt: List[str] = []
        for piece in tokens:
            nxt.extend(piece.split(d))
        tokens = nxt
    return tokens
