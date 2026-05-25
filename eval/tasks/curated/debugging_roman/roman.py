"""Roman numeral conversion.

Standard (subtractive) Roman numerals for integers 1..3999:
  1 -> "I", 4 -> "IV", 9 -> "IX", 40 -> "XL", 90 -> "XC",
  400 -> "CD", 900 -> "CM", 2024 -> "MMXXIV".

`to_roman` encodes an int -> str; `from_roman` decodes a str -> int.
They must round-trip: from_roman(to_roman(n)) == n for every valid n.
"""

# Value -> symbol table, largest first. Greedy emission walks this table.
_VALUES = [
    (1000, "M"),
    (500, "D"),
    (100, "C"),
    (90, "XC"),
    (50, "L"),
    (40, "XL"),
    (10, "X"),
    (9, "IX"),
    (5, "V"),
    (4, "IV"),
    (1, "I"),
]

_SYMBOL = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def to_roman(n: int) -> str:
    """Encode 1 <= n <= 3999 as a Roman numeral string."""
    if not 1 <= n <= 3999:
        raise ValueError("to_roman expects 1..3999")
    out = []
    for value, symbol in _VALUES:
        while n >= value:
            out.append(symbol)
            n -= value
    return "".join(out)


def from_roman(s: str) -> int:
    """Decode a Roman numeral string into its integer value."""
    if not s:
        raise ValueError("from_roman expects a non-empty string")
    total = 0
    for i, ch in enumerate(s):
        value = _SYMBOL[ch]
        # Subtractive notation: a smaller symbol placed before a larger one is
        # subtracted (IV = 4, IX = 9). Otherwise it is added.
        if i + 1 < len(s) and value <= _SYMBOL[s[i + 1]]:
            total -= value
        else:
            total += value
    return total
