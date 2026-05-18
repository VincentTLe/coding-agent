# Cached: Ruff — Configuring Ruff

Source: https://docs.astral.sh/ruff/configuration/
Fetched: 2026-05-18

## Files

Ruff reads `pyproject.toml`, `ruff.toml`, or `.ruff.toml`. Equivalent schema; `ruff.toml` omits the `[tool.ruff]` and `tool.ruff` prefixes.

## Defaults (when unspecified)

- `line-length = 88` (Black-compatible)
- `indent-width = 4`
- `target-version = "py310"` (still 3.10 as of 0.15.x; override explicitly for newer projects)
- Format: double quotes, spaces (not tabs)
- Excludes `.git`, `.venv`, `__pycache__`, common build dirs by default

## `[tool.ruff.lint]` skeleton

```toml
[tool.ruff.lint]
select = ["E4", "E7", "E9", "F"]
ignore = []
fixable = ["ALL"]
unfixable = []
dummy-variable-rgx = "^(_+|(_+[a-zA-Z0-9_]*[a-zA-Z0-9]+?))$"
```

Default `select` is conservative: only Pyflakes (`F`) plus pycodestyle errors `E4`/`E7`/`E9`. Warnings (`W`) and McCabe (`C90`) are NOT on by default.

## Plugin sub-tables

```toml
[tool.ruff.lint.flake8-quotes]
docstring-quotes = "double"
```

CLI flags (`--target-version`, `--line-length`) override file settings.

## Python 3.12 specifics

- Set `target-version = "py312"` at top level.
- `[tool.ruff.format] nested-string-quote-style = "preferred"` is only meaningful for py312+.
- `per-file-target-version` can pin specific globs (e.g. scripts on a newer version).
