# parsing_arith — arithmetic expression evaluator

## Goal
Implement `evaluate(expr)` in `arith.py`. It takes an arithmetic expression as a
string, parses it, and returns the resulting number: an `int` when the result is
a whole number, otherwise a `float`. You must tokenize the string yourself and
parse it according to the grammar below (e.g. recursive descent or shunting-yard).
Do **not** use `eval`/`exec` or any expression-parsing library.

Grammar (whitespace between tokens is insignificant):

```
expr    := term (('+' | '-') term)*
term    := factor (('*' | '/') factor)*
factor  := ('+' | '-') factor | primary
primary := NUMBER | '(' expr ')'
NUMBER  := digits ['.' digits]        (e.g. 12, 3.5, 0.25)
```

Rules:
- `+` `-` are left-associative and lower precedence than `*` `/`.
- `*` `/` are left-associative.
- Unary `+`/`-` bind tighter than the binary operators and may stack
  (`"--3"` == 3, `"-+-2"` == 2). `*` and `/` are binary only (never unary).
- `/` is true division. Return an `int` when the value is whole, else a `float`:
  `"6/3"` -> `2` (int), `"6/4"` -> `1.5` (float), `"2+2"` -> `4` (int).
- Numbers are integers or decimals with digits on **both** sides of the dot.
  A leading or trailing dot (`".5"`, `"5."`) is invalid.

Examples:
- `evaluate("2+3*4")` -> `14`
- `evaluate("(2+3)*4")` -> `20`
- `evaluate("10-3-2")` -> `5`
- `evaluate("16/4/2")` -> `2`
- `evaluate("2*(3+4*(5-2))")` -> `30`
- `evaluate("3+-5")` -> `-2`
- `evaluate("  ( 1 + 2 ) * 3 ")` -> `9`

Raise `ValueError` for: empty/blank input; unknown characters (e.g. `%`, letters,
`^`); malformed numbers (`"1.2.3"`, `"1..2"`, `".5"`, `"5."`); unbalanced
parentheses (missing or extra `)`); missing operands (`"1+"`, `"*3"`, `"()"`,
`"1 2"`, `"(1+)"`, `"2**3"`); and division by zero.

## Category
parsing

## Difficulty
hard

## Tests
hidden

## Source/License
Authored for coding-agent eval. MIT.
