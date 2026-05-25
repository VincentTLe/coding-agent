"""Tokenize and evaluate arithmetic expressions.

Implement ``evaluate(expr)`` which parses and evaluates an arithmetic
expression given as a string and returns the resulting number (an ``int``
when the result is integral, otherwise a ``float``).

Supported grammar (whitespace between tokens is insignificant)::

    expr    := term (('+' | '-') term)*
    term    := factor (('*' | '/') factor)*
    factor  := ('+' | '-') factor | primary
    primary := NUMBER | '(' expr ')'
    NUMBER  := digits ['.' digits]        (e.g. 12, 3.5, 0.25)

Rules:
  * '+' and '-' are left-associative and lower precedence than '*' and '/'.
  * '*' and '/' are left-associative.
  * Unary '+' and '-' bind tighter than the binary operators and may stack
    (e.g. "--3" == 3, "-+-2" == 2).
  * '/' is true division. The result is returned as an ``int`` when it is a
    whole number (e.g. "6/3" -> 2, "6/4" -> 1.5, "2+2" -> 4).
  * Numbers may be integers or decimals with a fractional part. A leading or
    trailing dot (".5" or "5.") is NOT allowed.

Errors (raise ``ValueError``):
  * Empty / blank input.
  * Any unexpected or unknown character (e.g. '%', letters).
  * Malformed number (e.g. "1.2.3", "1..2").
  * Unbalanced parentheses (missing ')' or extra ')').
  * Missing operand (e.g. "1+", "*3", "()", "1 2", "(1+)").
  * Division by zero.
"""


def evaluate(expr):
    """Evaluate an arithmetic expression string and return int/float.

    See the module docstring for the full grammar and error rules.
    """
    raise NotImplementedError
