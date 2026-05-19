"""A tiny calculator module. There is a bug in `add`."""


def add(a: int, b: int) -> int:
    # BUG: returns a - b instead of a + b. The agent must find and fix this.
    return a - b


def multiply(a: int, b: int) -> int:
    return a * b
