# Cached: Ruff — Linter & rule prefixes

Sources:
- https://docs.astral.sh/ruff/linter/
- https://docs.astral.sh/ruff/rules/
- https://docs.astral.sh/ruff/faq/
Fetched: 2026-05-18

## Rule prefixes (selected, ~900 rules total in 0.15.x)

| Prefix | Origin | Notes |
|---|---|---|
| `E`, `W` | pycodestyle | `E` = errors, `W` = warnings (off by default) |
| `F` | Pyflakes | unused imports, undefined names — high value |
| `I` | isort | import ordering; complements ruff format |
| `UP` | pyupgrade | auto-modernizes for `target-version` |
| `B` | flake8-bugbear | likely-bug patterns; safe & high signal |
| `SIM` | flake8-simplify | simpler equivalents (`if x == True` etc.) |
| `C4` | flake8-comprehensions | comprehension idioms |
| `C90` | McCabe | cyclomatic complexity threshold |
| `N` | pep8-naming | PEP 8 names; some false positives on libs |
| `D` | pydocstyle | docstring presence/format; pick a convention |
| `ANN` | flake8-annotations | type-annotation coverage; redundant with strict mypy |
| `ARG` | flake8-unused-arguments | unused fn / lambda args |
| `PL` | Pylint port | semantic checks; some noisy (PLR magic numbers) |
| `RUF` | Ruff-native | Ruff-specific lints |
| `S` | flake8-bandit | security smells |
| `TID`, `TCH` | tidy/type-checking imports | structural import policy |
| `PT` | flake8-pytest-style | pytest idioms |
| `PTH` | flake8-use-pathlib | replace `os.path` with `pathlib` |
| `ERA` | eradicate | commented-out code |
| `PIE`, `RET`, `RSE`, `SLF` | misc | style/clarity |

## Astral guidance on `select = ["ALL"]`

> "Use `ALL` with discretion. Enabling `ALL` will implicitly enable new rules whenever you upgrade."

Conflicting rules (e.g. `D203` vs `D211`) are auto-resolved but ALL pulls in noisy categories (`CPY` copyright, `FBT` boolean traps, `PLR` magic-value, `ANN` everywhere).

Recommended starter set (Astral): `["E", "F"]` then grow.
Astral baseline for serious projects: `["E", "F", "UP", "B", "SIM", "I"]`.

## What Ruff does NOT do

- Type checking. Pair with mypy / pyright / ty.
- Third-party plugins (not yet supported as of 0.15.x).

## `pydocstyle` conventions

Pick exactly one convention to avoid D203/D211 etc. conflicts:
```toml
[tool.ruff.lint.pydocstyle]
convention = "google"   # or "numpy" or "pep257"
```
