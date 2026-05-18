# Cached: Ruff — Formatter

Sources:
- https://docs.astral.sh/ruff/formatter/
- https://docs.astral.sh/ruff/formatter/black/
- https://astral.sh/blog/the-ruff-formatter
Fetched: 2026-05-18

## Status

Stable. F-string formatting stabilized in Ruff 0.9.0.

## Compatibility with Black

>99.9% of lines identical to Black on Django/Zulip benchmarks. ~30x faster than Black, ~100x faster than YAPF. Intentional minor deviations documented at `/formatter/black/`.

## Commands

```bash
ruff format                  # format cwd
ruff format path/to/file.py  # single file
ruff format --check          # CI: fail if reformatting needed
```

## `[tool.ruff.format]` example (from docs)

```toml
[tool.ruff]
line-length = 100

[tool.ruff.format]
quote-style = "single"
indent-style = "tab"
docstring-code-format = true
```

Notable knobs:
- `quote-style` — `"double"` (default) / `"single"` / `"preserve"`
- `indent-style` — `"space"` / `"tab"`
- `docstring-code-format = true` — format Python in docstring code blocks
- `line-ending` — `"auto"` / `"lf"` / `"crlf"` / `"native"`

## When to switch from Black

Astral position: for **new** projects, use `ruff format` directly. For existing Black projects, no urgent migration. Don't oscillate between Black and ruff format on the same codebase — pick one.
