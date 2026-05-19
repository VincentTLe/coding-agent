# Task 02 — Implement shape functions from stubs

## Goal
Implement the 4 stub functions in `shapes.py` so all tests in
`test_shapes.py` pass.

## Setup
```bash
cd eval/tasks/02_implement && pytest -x
```

## Expected agent flow
1. `read_file("shapes.py")` — see the stubs + docstrings (the spec is in
   the docstrings; agent should implement to match).
2. `read_file("test_shapes.py")` — see the expected values.
3. `write_file("shapes.py", ...)` — implement all 4 functions using
   `math.pi` and basic arithmetic.
4. `run_bash("pytest")` — confirm all 10 tests pass.

## Success criteria
`pytest` exits 0. All 10 tests pass.

## Capability tested
**Code generation** (not debugging). The agent must WRITE working code from
a docstring + tests, mirroring how a developer implements a function spec.
Tests both math fluency and translation of natural-language specs to code.
