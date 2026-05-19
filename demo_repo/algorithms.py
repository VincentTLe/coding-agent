"""
Common math algorithms — there are TWO intentional bugs in this file.
The agent must locate and fix both so all pytest cases pass.
"""


def is_prime(n: int) -> bool:
    """Return True if n is a prime number (n >= 2)."""
    if n < 2:
        return False
    # BUG #1: range starts at 1 — `n % 1 == 0` is always True, so this
    # function always returns False. The correct start is 2.
    for i in range(1, n):
        if n % i == 0:
            return False
    return True


def factorial(n: int) -> int:
    """Return n! (n factorial). factorial(0) = 1, factorial(5) = 120."""
    if n < 0:
        raise ValueError("n must be non-negative")
    result = 1
    # BUG #2: range stops at n, so the multiplication misses the final
    # factor n itself. factorial(5) returns 24 instead of 120.
    for i in range(1, n):
        result *= i
    return result


def fibonacci(n: int) -> int:
    """Return the nth Fibonacci number. fib(0)=0, fib(1)=1."""
    if n < 0:
        raise ValueError("n must be non-negative")
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a
