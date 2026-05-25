"""Parse a small JSON subset into Python objects.

Implement ``parse(text)`` that parses a string in the JSON subset described
below and returns the corresponding Python object. Do **not** use the stdlib
``json`` module (or any other parsing library) — write the parser yourself.

Grammar (a strict subset of JSON):
  * value   := object | array | string | number | 'true' | 'false' | 'null'
  * object  := '{' ws '}' | '{' members '}'
  * members := pair (',' pair)*
  * pair    := ws string ws ':' value
  * array   := '[' ws ']' | '[' elements ']'
  * elements:= value (',' value)*
  * string  := '"' chars '"'
  * number  := '-'? int frac? exp?

Mapping to Python:
  * object  -> dict      (later duplicate keys overwrite earlier ones)
  * array   -> list
  * string  -> str
  * integer (no '.' and no exponent) -> int
  * number with '.' or exponent      -> float
  * true/false -> True/False ; null -> None

String rules:
  * Strings are double-quoted. Single quotes are NOT allowed.
  * Supported escapes: \\" \\\\ \\/ \\b \\f \\n \\r \\t and \\uXXXX (exactly four
    hex digits). Any other backslash escape is invalid.
  * A literal control character (codepoint < 0x20, e.g. a raw newline or tab)
    inside a string is invalid; such characters must be escaped.

Number rules:
  * Optional leading '-'. No leading '+'.
  * Integer part: a single '0', or a non-zero digit followed by more digits.
    Leading zeros like "01" are invalid.
  * Optional fraction '.' followed by one or more digits.
  * Optional exponent 'e'/'E', optional sign, then one or more digits.
  * "-" alone, ".5", "5.", "1." , "1e", "+1" are all invalid.

Whitespace (space, tab, newline, carriage return) is allowed between any tokens
and around the whole document, and must be ignored.

Errors — raise ``ValueError`` on any malformed input, including (non-exhaustive):
  * Empty / whitespace-only input.
  * Trailing content after a complete value (e.g. '1 2', '{} []').
  * Trailing commas ('[1,]', '{"a":1,}').
  * Missing commas, missing colons, unquoted keys, single-quoted strings.
  * Unterminated strings / objects / arrays.
  * Unknown literals (e.g. 'True', 'NULL', 'undefined').
  * Bad escapes or bad \\u sequences.
"""


def parse(text):
    """Parse a JSON-subset string and return the Python object.

    See the module docstring for the exact grammar and error rules.
    """
    raise NotImplementedError
