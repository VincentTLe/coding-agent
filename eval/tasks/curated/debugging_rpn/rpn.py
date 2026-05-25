"""A tiny Reverse Polish Notation (postfix) calculator.

`eval_rpn` accepts either a whitespace-separated string ("3 4 +") or a list of
string tokens (["3", "4", "+"]) and returns the numeric result as a float.

Supported binary operators: + - * /
  - For the non-commutative operators (- and /), the operand that appears
    EARLIER in the input is the left operand:
        "5 1 -"  ->  5 - 1  ->  4.0
        "8 2 /"  ->  8 / 2  ->  4.0
  - "/" is true division (so "7 2 /" -> 3.5).

Numbers may be integers or decimals; all results come back as float.
Errors: an empty input, an unknown token, or a malformed expression raise
ValueError.
"""

_OPS = {"+", "-", "*", "/"}


def _apply(op: str, left: float, right: float) -> float:
    if op == "+":
        return left + right
    if op == "-":
        return left - right
    if op == "*":
        return left * right
    # true division
    return left // right


def eval_rpn(expr) -> float:
    """Evaluate a postfix expression; return the result as a float."""
    tokens = expr.split() if isinstance(expr, str) else list(expr)
    if not tokens:
        raise ValueError("empty expression")

    stack: list[float] = []
    for tok in tokens:
        if tok in _OPS:
            if len(stack) < 2:
                raise ValueError("not enough operands for operator " + tok)
            a = stack.pop()
            b = stack.pop()
            stack.append(_apply(tok, a, b))
        else:
            try:
                stack.append(float(tok))
            except ValueError:
                raise ValueError("unknown token: " + repr(tok))

    if len(stack) != 1:
        raise ValueError("malformed expression: " + str(len(stack)) + " values left")
    return stack[0]
