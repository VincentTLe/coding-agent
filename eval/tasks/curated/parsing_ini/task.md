# parsing_ini — INI config parser with sections, continuations & coercion

## Goal
Implement `parse_ini(text)` in `iniparse.py`. It parses an INI configuration and
returns a `dict` mapping section names to dicts of key/value pairs. Write the
parser yourself; do **not** use `configparser` or any other parsing library.

Lines are split on `"\n"`; a trailing `"\r"` on any line is stripped. Line types:
- **Blank line** (empty or all whitespace): ignored, but it terminates any value
  continuation in progress.
- **Comment line** (first non-whitespace char is `;` or `#`): ignored entirely.
  `;`/`#` elsewhere in a line are ordinary characters (no inline comments).
- **Section header** `[name]` (optional surrounding whitespace): `name` is
  stripped and must be non-empty. Dots have no special meaning (`[a.b]` is one
  section literally named `"a.b"`).
- **Key/value** `key = value` or `key : value`: the first `=` or `:` (whichever
  comes first) is the separator. `key` is stripped and must be non-empty; `value`
  is stripped.
- **Continuation**: an indented line (starts with space/tab) that is not
  blank/comment/section/key-value-with-separator. It appends to the most recent
  value, joined with `"\n"`, after stripping. A continuation with no preceding
  key is an error.

Type coercion (applied to the FINAL joined value string):
- `"true"`/`"false"` (case-insensitive) -> `True`/`False`.
- `"null"`/`"none"` (case-insensitive) and `""` -> `None`.
- Integer literal (optional sign, all digits) -> `int`.
- Float literal (parses as float, contains `.`/`e`/`E`) -> `float`.
- Otherwise -> `str`.
- Multi-line (continued) values are NEVER coerced — they stay `str`.

Sections: keys before any header go in the default section named `""` (omitted if
there are none). A repeated header merges into the existing section; a repeated
key overwrites.

Examples:
- `parse_ini("[db]\nhost = localhost\nport = 5432")` -> `{"db": {"host": "localhost", "port": 5432}}`
- `parse_ini("debug = true\n[s]\nx = 1.5")` -> `{"": {"debug": True}, "s": {"x": 1.5}}`
- `parse_ini("[a]\nk = line1\n    line2")` -> `{"a": {"k": "line1\nline2"}}`

Raise `ValueError` for: a malformed section header (`"["`, `"[]"`, `"[a"`, `"a]"`,
`"[a]extra"`); a non-blank/non-comment/non-section line with no `=`/`:` that is
not a valid continuation (a bare word, or an indented line when no key has been
seen yet); and an empty key (`"= value"`).

## Category
parsing

## Difficulty
hard

## Tests
hidden

## Source/License
Authored for coding-agent eval. MIT.
