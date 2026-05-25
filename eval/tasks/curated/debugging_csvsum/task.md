# debugging_csvsum — CSV parsing + column sum

## Goal
`csvsum.py` hand-rolls a tiny CSV reader (stdlib only — do not switch to the
`csv` module).

- `parse_line(line)` splits one CSV line into fields, honouring quoting:
  commas inside double quotes are literal (`'"Smith, John",10'` ->
  `['Smith, John', '10']`), a doubled quote is one literal quote
  (`'"a""b"'` -> `['a"b']`), and the wrapping quotes are stripped.
- `sum_column(text, column)` reads a CSV document whose first line is a header,
  locates `column` by name, and returns the `float` sum of that column over the
  data rows. Blank lines are ignored; values may be integers or decimals
  (`"100.50"` contributes `100.5`).

The suite in `test_csvsum.py` is failing. Run pytest, localize the bug(s), and
fix `csvsum.py` so every test passes. Do not edit the tests. Watch the edge
cases: escaped doubled quotes, quoted fields containing commas (which must keep
later columns aligned), and decimal values.

## Category
debugging

## Difficulty
hard

## Tests
visible

## Source/License
Authored for coding-agent eval. MIT.
