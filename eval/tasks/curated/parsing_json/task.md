# parsing_json — tiny JSON subset parser

## Goal
Implement `parse(text)` in `jsonmini.py`. It parses a string in the JSON subset
described below and returns the equivalent Python object. Write the parser
yourself (recursive descent is natural); do **not** use the stdlib `json` module
or any other parsing library.

Grammar (a strict subset of JSON):

```
value    := object | array | string | number | 'true' | 'false' | 'null'
object   := '{' ws '}' | '{' members '}'
members  := pair (',' pair)*
pair     := ws string ws ':' value
array    := '[' ws ']' | '[' elements ']'
elements := value (',' value)*
string   := '"' chars '"'
number   := '-'? int frac? exp?
```

Mapping to Python:
- object -> `dict` (on duplicate keys, the later value wins)
- array  -> `list`
- string -> `str`
- integer (no `.` and no exponent) -> `int`
- number with `.` or exponent -> `float`
- `true`/`false` -> `True`/`False`; `null` -> `None`

String rules: double-quoted only (single quotes invalid). Supported escapes:
`\"` `\\` `\/` `\b` `\f` `\n` `\r` `\t` and `\uXXXX` (exactly four hex digits).
Any other backslash escape is invalid. A raw control character (codepoint < 0x20,
e.g. a literal newline/tab) inside a string is invalid.

Number rules: optional leading `-` (no leading `+`); integer part is `0` or a
non-zero digit followed by more digits (no leading zeros like `01`); optional
`.` followed by one or more digits; optional `e`/`E` with optional sign and one
or more digits. `"-"`, `".5"`, `"5."`, `"1."`, `"1e"`, `"+1"` are all invalid.

Whitespace (space, tab, newline, carriage return) between tokens and around the
whole document must be ignored.

Examples:
- `parse('{"a": 1, "b": [2, 3]}')` -> `{"a": 1, "b": [2, 3]}`
- `parse("[true, false, null]")` -> `[True, False, None]`
- `parse('"caf\\u00e9"')` -> `"café"`
- `parse("1e3")` -> `1000.0` (float); `parse("42")` -> `42` (int)

Raise `ValueError` on any malformed input, including: empty/whitespace-only input;
trailing content after a complete value (`'1 2'`, `'{} []'`); trailing commas
(`'[1,]'`, `'{"a":1,}'`); missing commas/colons; unquoted keys; single-quoted
strings; unterminated strings/arrays/objects; unknown literals (`True`, `NULL`,
`undefined`); and bad escapes or `\u` sequences.

## Category
parsing

## Difficulty
hard

## Tests
hidden

## Source/License
Authored for coding-agent eval. MIT.
