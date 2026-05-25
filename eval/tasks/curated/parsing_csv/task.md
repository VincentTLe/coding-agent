# parsing_csv — RFC 4180 style CSV document parser

## Goal
Implement `parse_csv(text)` in `csvparse.py`. It parses an entire CSV document
(the string may contain multiple records) and returns a `list` of records, where
each record is a `list` of field strings. Parse it yourself, character by
character; do **not** use the stdlib `csv` module.

Format:
- Fields are separated by commas `,`.
- Records are separated by `"\n"` (LF) or `"\r\n"` (CRLF). A bare `"\r"` not
  followed by `"\n"` is an ordinary character, NOT a terminator.
- A field is *quoted* if it starts with a double quote `"`. Inside a quoted
  field, commas, `"\n"` and `"\r\n"` are literal data, and a literal double
  quote is written as two double quotes `""`.
- An *unquoted* field is the raw run of characters up to the next comma or line
  terminator. Whitespace is significant and is NOT stripped.

Examples:
- `parse_csv("a,b,c")` -> `[["a", "b", "c"]]`
- `parse_csv("1,2\n3,4")` -> `[["1", "2"], ["3", "4"]]`
- `parse_csv('a,"b,c",d')` -> `[["a", "b,c", "d"]]`
- `parse_csv('"he said ""hi"""')` -> `[['he said "hi"']]`
- `parse_csv('"line1\nline2"')` -> `[["line1\nline2"]]`
- `parse_csv("a,,c")` -> `[["a", "", "c"]]`

Edge cases (NOT errors):
- Empty input `""` -> `[]` (no records).
- A trailing newline does NOT create an extra empty record: `"a,b\n"` ->
  `[["a", "b"]]`.
- A blank line in the middle is a one-field record: `"a\n\nb"` ->
  `[["a"], [""], ["b"]]`.
- Records may have different numbers of fields (no validation).

Raise `ValueError` for malformed quoting:
- An unterminated quoted field (opening quote, no closing quote), e.g. `'"abc'`.
- A quote in the middle of an *unquoted* field, e.g. `'ab"c'`.
- Characters after a closing quote other than a comma or line terminator, e.g.
  `'"ab"c'` or `'"ab" ,c'`.

## Category
parsing

## Difficulty
hard

## Tests
hidden

## Source/License
Authored for coding-agent eval. MIT.
