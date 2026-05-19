# Task 01 — Fix string utility bugs

## Goal
Fix all failing tests in `eval/tasks/01_strings/`.

## Setup
```bash
cd eval/tasks/01_strings && pytest -x
```

## Expected agent flow
1. `run_bash("ls")` — see the two files.
2. `run_bash("pytest -x")` — see which tests fail.
3. `read_file("string_utils.py")` — locate the bugs.
4. `write_file("string_utils.py", ...)` — fix `reverse_string` (drop the trailing slice) and `count_vowels` (lowercase the input or include uppercase vowels).
5. `run_bash("pytest")` — confirm all pass.

## Success criteria
`pytest` exits 0. All 10 tests pass.

## Bugs planted (for the human grader, not the agent)
- `reverse_string` returns `s[::-1][:-1]` instead of `s[::-1]`.
- `count_vowels` only checks lowercase `"aeiou"`.

## Capability tested
Multi-bug debug in a single file. Tests the agent's ability to read failing
pytest output, find independent bugs, and fix them in one or more edits.
