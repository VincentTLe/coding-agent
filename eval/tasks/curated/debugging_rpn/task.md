# debugging_rpn — Reverse Polish Notation calculator

## Goal
`rpn.py` evaluates postfix (Reverse Polish Notation) arithmetic. `eval_rpn`
accepts either a whitespace-separated string (`"3 4 +"`) or a list of string
tokens (`["3", "4", "+"]`) and returns the result as a `float`. Supported
binary operators are `+ - * /`.

Important semantics:
- For non-commutative operators, the operand appearing EARLIER in the input is
  the left operand: `"5 1 -"` is `5 - 1 == 4.0`; `"8 2 /"` is `8 / 2 == 4.0`.
- `/` is true division: `"7 2 /" == 3.5`, `"-7 2 /" == -3.5`.
- Empty input, unknown tokens, and malformed expressions raise `ValueError`.

The suite in `test_rpn.py` is failing. Run pytest, localize the bug(s), and fix
`rpn.py` so every test passes. Do not edit the tests.

## Category
debugging

## Difficulty
hard

## Tests
visible

## Source/License
Authored for coding-agent eval. MIT.
