# Task 03 — Add two new functions + tests

## Goal
Add two new functions to `math_ops.py`, and add corresponding pytest cases
to `test_math_ops.py`:

1. `gcd(a: int, b: int) -> int` — greatest common divisor of a and b.
2. `lcm(a: int, b: int) -> int` — least common multiple of a and b.

Both should be in `math_ops.py` next to the existing operations.

Add at least 3 pytest cases for `gcd` and 3 for `lcm`, covering normal
inputs and edge cases (zero, equal values).

## Setup
```bash
cd eval/tasks/03_add_feature && pytest
```

## Expected agent flow
1. `read_file("math_ops.py")` — see existing functions.
2. `read_file("test_math_ops.py")` — see existing test style.
3. `write_file("math_ops.py", ...)` — add gcd + lcm to the existing file.
4. `write_file("test_math_ops.py", ...)` — add tests for both.
5. `run_bash("pytest")` — confirm all old + new tests pass.

## Success criteria
- `gcd` and `lcm` are importable from `math_ops`.
- At least 3 tests for each new function.
- All tests pass (old + new).

## Capability tested
**Multi-step planning + multi-file write**. The agent must:
1. Read existing code style and match it.
2. Write a new function correctly (typical impl: `math.gcd` or Euclid).
3. Write a new test function with sensible cases.
4. Verify the change end-to-end.

This mirrors a real "feature request" workflow.
