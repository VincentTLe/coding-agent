# F2 — Ruff configuration for a new Python 3.12 project (May 2026)

## TL;DR

Keep one tool: **Ruff for lint + format**, pair with mypy/ty. Expand the repo's current `select = ["E","F","W","I","UP"]` to a curated 15-prefix set, enable `[tool.ruff.format]`, add pre-commit at `rev: v0.15.13`. Don't use `select=["ALL"]`. Skip `D`, `ANN`, `PL` for now.

## Why now

Adding rules to a fresh codebase is cheap; doing it later is a fix-all-noqa weekend.

## State of the art, May 2026

- **Ruff 0.15.13** (2026-05-14): ~900 rules; 100–155x faster than flake8+isort+black.
- **`ruff format`** stable since 0.9.0; >99.9% line-identical to Black; ~30x faster.
- **Pre-commit** `astral-sh/ruff-pre-commit@v0.15.13`; hook IDs `ruff-check`, `ruff-format`.
- **Editors**: VS Code `charliermarsh.ruff`; PyCharm native (2025.3+); Neovim 0.11 `vim.lsp.config`; Zed built-in.
- **Adoption** [UNVERIFIED]: Stack Overflow 2025 most-admired tool; FastAPI, Pydantic, Airflow, Pandas.
- Types out of scope — pair with mypy or Astral `ty`.

## Most-used in 2026

New-project stack: **Ruff + uv + mypy/ty**, replacing flake8+black+isort+pyupgrade+parts of pylint. Astral's baseline is `["E","F","UP","B","SIM","I"]`; curated lists dominate.

## `select = ["ALL"]` in practice

Astral verbatim: *"Use `ALL` with discretion. Enabling `ALL` will implicitly enable new rules whenever you upgrade."* Cost: silent CI breaks on upgrade; noisy categories (`FBT`, `CPY`, `PLR2004`, `ANN401`, `D`); implicit policy from conflict auto-resolution. Verdict: a curated 12–16 prefix list wins.

## D, N, B, C90, ANN, ARG, PL?

| Prefix | Add now? | Reason |
|---|---|---|
| `B` bugbear | **Yes** | High-signal, few false positives |
| `C90` McCabe | **Yes** | One knob, catches god-functions |
| `N` pep8-naming | **Yes** | Free; drift-prevention |
| `ARG` unused args | **Yes** | Catches stale tool signatures |
| `D` pydocstyle | **No** | Pick convention first; revisit on public API |
| `ANN` annotations | **No** | Redundant with `mypy --strict` |
| `PL` Pylint port | **No** | `PLR` noisy; cherry-pick `PLE`/`PLW` later |

Also enable: `SIM`, `C4`, `RUF`, `PTH`, `S` (agent runs shell), `PT`, `TID`.

## Comparison

| Tool | vs Ruff | Status 2026 |
|---|---|---|
| **Ruff** lint+format | 1x | de-facto standard |
| Black | ~30x slower | no urgent migration |
| isort | covered by Ruff `I` | superseded |
| flake8+plugins | ~100x slower | superseded |
| Pylint | far slower | only for type-aware checks |
| mypy/pyright/ty | n/a | **complementary** |

## Recommendation — concrete `[tool.ruff]` block

```toml
[tool.ruff]
line-length = 100
target-version = "py312"
extend-exclude = ["build", "dist", ".venv"]

[tool.ruff.lint]
select = [
    "E", "W", "F", "I", "UP",
    "B", "C4", "SIM", "RUF",
    "C90", "N", "PTH", "ARG",
    "S", "PT", "TID",
]
ignore = ["E501", "S101", "B008"]  # length=formatter; assert in tests; FastAPI default-call
fixable = ["ALL"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S", "ARG", "PLR2004"]
"scripts/**" = ["T201"]

[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.ruff.lint.isort]
known-first-party = ["coding_agent"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
docstring-code-format = true
line-ending = "lf"
```

Defer: `D` (pick `google`/`numpy` first), `ANN` (only if not strict-mypy), `PL` (cherry-pick), `ERA`.

## Next steps

```bash
uv run ruff check --fix .
uv run ruff format .
uv add --dev ruff   # pin so CI matches local

cat > .pre-commit-config.yaml <<'EOF'
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.13
    hooks:
      - id: ruff-check
        args: [--fix]
      - id: ruff-format
EOF
uv run pre-commit install
```

CI: `ruff check --output-format=github .` then `ruff format --check .`. VS Code: install `charliermarsh.ruff`, set as default Python formatter, enable format-on-save.

## Open questions

- Ruff dev-dep version + pre-commit `rev` drift — keep in sync.
- Docstring convention when `D` lands: `google` vs `numpy`. [UNVERIFIED]
- mypy vs Astral `ty` — separate note; `ty` pre-1.0 in 2026.

## Sources

- Astral docs: [Configuration](https://docs.astral.sh/ruff/configuration/), [Linter](https://docs.astral.sh/ruff/linter/), [Rules](https://docs.astral.sh/ruff/rules/), [Formatter](https://docs.astral.sh/ruff/formatter/), [Black deviations](https://docs.astral.sh/ruff/formatter/black/), [FAQ](https://docs.astral.sh/ruff/faq/), [Editor setup](https://docs.astral.sh/ruff/editors/setup/)
- Repos: [astral-sh/ruff](https://github.com/astral-sh/ruff), [astral-sh/ruff-pre-commit](https://github.com/astral-sh/ruff-pre-commit) (v0.15.13, 2026-05-14)
- Astral blog: [The Ruff Formatter](https://astral.sh/blog/the-ruff-formatter)
- Adoption context [UNVERIFIED]: [Better Stack](https://betterstack.com/community/guides/scaling-python/ruff-explained/), [pydevtools recommended defaults](https://pydevtools.com/handbook/how-to/how-to-configure-recommended-ruff-defaults/)
