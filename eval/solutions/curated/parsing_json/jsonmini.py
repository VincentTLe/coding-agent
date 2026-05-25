"""Parse a small JSON subset into Python objects (reference solution).

A hand-written recursive-descent parser over the raw string with an index.
"""

_WS = " \t\n\r"
_ESCAPES = {
    '"': '"',
    "\\": "\\",
    "/": "/",
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
}


class _Parser:
    def __init__(self, text):
        self.s = text
        self.i = 0
        self.n = len(text)

    # -- low level helpers --------------------------------------------------
    def _err(self, msg):
        raise ValueError(f"{msg} at index {self.i}")

    def _skip_ws(self):
        while self.i < self.n and self.s[self.i] in _WS:
            self.i += 1

    def _peek(self):
        if self.i < self.n:
            return self.s[self.i]
        return None

    # -- entry point --------------------------------------------------------
    def parse(self):
        self._skip_ws()
        if self.i >= self.n:
            self._err("empty input")
        value = self._value()
        self._skip_ws()
        if self.i != self.n:
            self._err("trailing content after value")
        return value

    # -- value dispatch -----------------------------------------------------
    def _value(self):
        self._skip_ws()
        ch = self._peek()
        if ch is None:
            self._err("unexpected end of input")
        if ch == "{":
            return self._object()
        if ch == "[":
            return self._array()
        if ch == '"':
            return self._string()
        if ch == "-" or ch.isdigit():
            return self._number()
        if self.s.startswith("true", self.i):
            self.i += 4
            return True
        if self.s.startswith("false", self.i):
            self.i += 5
            return False
        if self.s.startswith("null", self.i):
            self.i += 4
            return None
        self._err(f"unexpected character {ch!r}")

    # -- object -------------------------------------------------------------
    def _object(self):
        assert self.s[self.i] == "{"
        self.i += 1
        result = {}
        self._skip_ws()
        if self._peek() == "}":
            self.i += 1
            return result
        while True:
            self._skip_ws()
            if self._peek() != '"':
                self._err("expected string key in object")
            key = self._string()
            self._skip_ws()
            if self._peek() != ":":
                self._err("expected ':' after object key")
            self.i += 1
            value = self._value()
            result[key] = value
            self._skip_ws()
            ch = self._peek()
            if ch == ",":
                self.i += 1
                continue
            if ch == "}":
                self.i += 1
                return result
            self._err("expected ',' or '}' in object")

    # -- array --------------------------------------------------------------
    def _array(self):
        assert self.s[self.i] == "["
        self.i += 1
        result = []
        self._skip_ws()
        if self._peek() == "]":
            self.i += 1
            return result
        while True:
            value = self._value()
            result.append(value)
            self._skip_ws()
            ch = self._peek()
            if ch == ",":
                self.i += 1
                continue
            if ch == "]":
                self.i += 1
                return result
            self._err("expected ',' or ']' in array")

    # -- string -------------------------------------------------------------
    def _string(self):
        assert self.s[self.i] == '"'
        self.i += 1
        out = []
        while True:
            if self.i >= self.n:
                self._err("unterminated string")
            ch = self.s[self.i]
            if ch == '"':
                self.i += 1
                return "".join(out)
            if ch == "\\":
                self.i += 1
                if self.i >= self.n:
                    self._err("unterminated escape")
                esc = self.s[self.i]
                if esc in _ESCAPES:
                    out.append(_ESCAPES[esc])
                    self.i += 1
                elif esc == "u":
                    hex4 = self.s[self.i + 1:self.i + 5]
                    if len(hex4) != 4 or any(c not in "0123456789abcdefABCDEF" for c in hex4):
                        self._err("invalid \\u escape")
                    out.append(chr(int(hex4, 16)))
                    self.i += 5
                else:
                    self._err(f"invalid escape \\{esc}")
            elif ord(ch) < 0x20:
                self._err("unescaped control character in string")
            else:
                out.append(ch)
                self.i += 1

    # -- number -------------------------------------------------------------
    def _number(self):
        start = self.i
        if self._peek() == "-":
            self.i += 1
        # integer part
        if self._peek() == "0":
            self.i += 1
        elif self._peek() is not None and self._peek().isdigit():
            while self._peek() is not None and self._peek().isdigit():
                self.i += 1
        else:
            self._err("invalid number")
        is_float = False
        # fraction
        if self._peek() == ".":
            is_float = True
            self.i += 1
            if self._peek() is None or not self._peek().isdigit():
                self._err("invalid number: digits required after '.'")
            while self._peek() is not None and self._peek().isdigit():
                self.i += 1
        # exponent
        if self._peek() in ("e", "E"):
            is_float = True
            self.i += 1
            if self._peek() in ("+", "-"):
                self.i += 1
            if self._peek() is None or not self._peek().isdigit():
                self._err("invalid number: digits required in exponent")
            while self._peek() is not None and self._peek().isdigit():
                self.i += 1
        text = self.s[start:self.i]
        return float(text) if is_float else int(text)


def parse(text):
    if not isinstance(text, str):
        raise ValueError("input must be a string")
    return _Parser(text).parse()
