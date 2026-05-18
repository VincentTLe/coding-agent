# Cached: Ruff — pre-commit hook

Source: https://github.com/astral-sh/ruff-pre-commit
Fetched: 2026-05-18 (rev v0.15.13 dated 2026-05-14)

## Recommended `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.13
    hooks:
      - id: ruff-check
        args: [ --fix ]
      - id: ruff-format
```

## Hook IDs

- `ruff-check` — linting (modern name; replaces bare `ruff` id)
- `ruff-format` — formatter (added in Ruff 0.0.289)

## Ordering rules

- When `--fix` is set, `ruff-check` MUST run before `ruff-format` (and before any Black/isort, if still used) — auto-fixes can introduce changes that need reformatting.
- Both hooks support `types_or: [python, pyi]`; add `pyproject` to also lint `pyproject.toml`.

## Notes

- Distributed via prebuilt wheels for fast install.
- `prek` (Rust pre-commit replacement) also supports these hooks via `prek.toml`.
