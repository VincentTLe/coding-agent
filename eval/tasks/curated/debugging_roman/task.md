# debugging_roman — Roman numeral encode/decode

## Goal
`roman.py` converts between integers (1..3999) and Roman numerals via
`to_roman(n)` and `from_roman(s)`. The two functions are meant to be exact
inverses: `from_roman(to_roman(n)) == n` for every valid `n`.

The test suite in `test_roman.py` is currently failing. Run pytest to see the
failures, localize the bug(s), and fix `roman.py` so every test passes. Do not
edit the tests. Reference behaviour:

- `to_roman(4) == "IV"`, `to_roman(400) == "CD"`, `to_roman(900) == "CM"`,
  `to_roman(1994) == "MCMXCIV"`, `to_roman(3999) == "MMMCMXCIX"`.
- `from_roman("II") == 2`, `from_roman("IV") == 4`, `from_roman("MCMXCIV") == 1994`.
- Out-of-range input to `to_roman` raises `ValueError`.

## Category
debugging

## Difficulty
hard

## Tests
visible

## Source/License
Authored for coding-agent eval. MIT.
