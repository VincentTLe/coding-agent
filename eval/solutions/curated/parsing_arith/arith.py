"""Tokenize and evaluate arithmetic expressions (reference solution).

Recursive-descent parser over a token stream, evaluating as it parses.
"""


def _tokenize(expr):
    """Turn the source string into a list of tokens.

    Number tokens are ('num', value); operator/paren tokens are ('op', ch).
    Raises ValueError on unknown characters or malformed numbers.
    """
    tokens = []
    i = 0
    n = len(expr)
    while i < n:
        ch = expr[i]
        if ch.isspace():
            i += 1
            continue
        if ch in "+-*/()":
            tokens.append(("op", ch))
            i += 1
            continue
        if ch.isdigit() or ch == ".":
            j = i
            seen_dot = False
            digits_before = False
            digits_after = False
            while j < n and (expr[j].isdigit() or expr[j] == "."):
                if expr[j] == ".":
                    if seen_dot:
                        raise ValueError(f"malformed number near index {i}")
                    seen_dot = True
                else:
                    if seen_dot:
                        digits_after = True
                    else:
                        digits_before = True
                j += 1
            text = expr[i:j]
            if seen_dot:
                # A dot requires digits on BOTH sides ("5." and ".5" are invalid).
                if not (digits_before and digits_after):
                    raise ValueError(f"malformed number {text!r}")
                value = float(text)
            else:
                value = int(text)
            tokens.append(("num", value))
            i = j
            continue
        raise ValueError(f"unexpected character {ch!r} at index {i}")
    return tokens


class _Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def _peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def _advance(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def parse(self):
        if not self.tokens:
            raise ValueError("empty expression")
        value = self._expr()
        if self.pos != len(self.tokens):
            tok = self.tokens[self.pos]
            raise ValueError(f"unexpected trailing token {tok}")
        return value

    def _expr(self):
        value = self._term()
        while True:
            tok = self._peek()
            if tok == ("op", "+"):
                self._advance()
                value = value + self._term()
            elif tok == ("op", "-"):
                self._advance()
                value = value - self._term()
            else:
                break
        return value

    def _term(self):
        value = self._factor()
        while True:
            tok = self._peek()
            if tok == ("op", "*"):
                self._advance()
                value = value * self._factor()
            elif tok == ("op", "/"):
                self._advance()
                divisor = self._factor()
                if divisor == 0:
                    raise ValueError("division by zero")
                value = value / divisor
            else:
                break
        return value

    def _factor(self):
        tok = self._peek()
        if tok == ("op", "+"):
            self._advance()
            return self._factor()
        if tok == ("op", "-"):
            self._advance()
            return -self._factor()
        return self._primary()

    def _primary(self):
        tok = self._peek()
        if tok is None:
            raise ValueError("unexpected end of expression (missing operand)")
        kind, val = tok
        if kind == "num":
            self._advance()
            return val
        if tok == ("op", "("):
            self._advance()
            value = self._expr()
            closing = self._peek()
            if closing != ("op", ")"):
                raise ValueError("missing closing parenthesis")
            self._advance()
            return value
        raise ValueError(f"unexpected token {tok} (missing operand)")


def _normalize(value):
    """Return an int when value is whole, else a float."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def evaluate(expr):
    if not isinstance(expr, str):
        raise ValueError("expression must be a string")
    tokens = _tokenize(expr)
    if not tokens:
        raise ValueError("empty expression")
    result = _Parser(tokens).parse()
    return _normalize(result)
