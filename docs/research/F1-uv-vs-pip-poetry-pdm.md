# F1 — uv vs pip vs Poetry vs PDM vs Hatch in 2026

## TL;DR

Use **uv** for `/home/tle/code/coding-agent`. It is the only mainstream manager that combines a Rust-fast resolver, cross-platform lockfile, built-in Python interpreter management, and a single-binary install. Action: `curl -LsSf https://astral.sh/uv/install.sh | sh`, then `uv sync`. No committed `requirements.txt`; generate one on demand if a downstream tool needs it.

## Why this matters now

The repo already ships `pyproject.toml` with `requires-python = ">=3.12"` and a `dev` extras group, but no lockfile and no manager on the system. Picking now avoids a migration later.

## State of the art, May 2026

- **uv 0.11.14** (Astral, 2026-05-04) — Rust binary, replaces pip + pip-tools + pipx + poetry + pyenv + virtualenv + twine.
- **Poetry 2.4.1** (2026-05-09); 2.3 added `pylock.toml` export. No interpreter management.
- **PDM 2.x** — `pdm.lock` v4.5 cross-platform; can use uv as installer backend.
- **Hatch 1.16.5** (~2026-02) — PyPA-blessed build/publish + matrix envs; lockfile only via per-env `pylock.toml` or `hatch-pip-compile` plugin.
- **pip 25.x** — universal baseline, no lockfile or resolver caching.

## Most-used in 2026

uv adoption has overtaken Poetry for new projects since mid-2025 (DataCamp/Cuttlesoft writeups, PyCharm uv-workspaces beta in 2026-05). Poetry persists in mature enterprise stacks; Hatch dominates library publishing; PDM has a small loyal base; pip remains everywhere but rarely chosen as primary. [UNVERIFIED — no 2026 PSF survey yet.]

## Comparison

| Feature | uv | Poetry | PDM | Hatch | pip |
|---|---|---|---|---|---|
| Lockfile | `uv.lock` cross-plat auto | `poetry.lock` | `pdm.lock` cross-plat | per-env `pylock.toml` opt-in | none |
| Cold install vs uv | 1x | ~3-4x slower | ~2-3x slower | n/a | ~10-100x slower |
| Installs Python itself | yes | no | no | no | no |
| Workspaces | yes | yes | yes | yes | no |
| `requirements.txt` export | `uv export` | plugin | `pdm export` | plugin | native |
| Bootstrap | `curl \| sh`, no Python | needs Python | needs Python | needs Python | bundled |

Speed ratios from Astral BENCHMARKS.md and 2026 third-party shootouts (Sentry deps: uv ~3s cold install vs Poetry ~11s; lock gen ~8s vs ~22s). [UNVERIFIED exact figures.]

## Recommendation

Adopt **uv**. Single `curl | sh` bootstrap (no Python prerequisite); ~10x faster than Poetry; `pyproject.toml` (already present) + auto-managed `uv.lock`; `uv python pin 3.12` satisfies the pinned-Python requirement without pyenv; PEP 751 export available for downstream interop. Reject Poetry (slower, no Python install), PDM (no advantage — even uses uv internally for speed), Hatch (better suited for library publishing; revisit when we publish).

Do **not** keep a committed `requirements.txt` — it would drift from `uv.lock`. Generate one only in Docker build stages: `uv export --format requirements-txt --no-dev > requirements.txt`.

## Next steps (concrete commands)

```bash
# 1. Install uv (no Python required).
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env

# 2. Pin Python 3.12 in repo (downloads CPython 3.12 if missing).
cd /home/tle/code/coding-agent
uv python pin 3.12

# 3. Lock + venv from existing pyproject.toml.
uv sync --all-extras       # runtime + [dev] group

# 4. Daily workflow.
uv add httpx                       # runtime dep
uv add --dev pytest-asyncio        # dev dep
uv run pytest                      # auto-syncs first
uv lock --upgrade-package openai   # bump one dep

# 5. CI (GitHub Actions):
#   - uses: astral-sh/setup-uv@v8
#     with: { version: "0.11.14", enable-cache: true }
#   - run: uv sync --locked --all-extras --dev
#   - run: uv run pytest tests
```

Commit: `pyproject.toml`, `uv.lock`, `.python-version`. Gitignore `.venv/`.

## Open questions

- Confirm exact uv version installed (run `uv --version`) and pin that string in CI. [UNVERIFIED]
- Renovate/Dependabot config for `uv.lock` — both now support it; syntax not yet drafted for this repo.
- Build backend if we ever publish to PyPI: `hatchling` vs `uv build`. Defer until on the roadmap.

## Sources

- uv docs: https://docs.astral.sh/uv/ , https://docs.astral.sh/uv/getting-started/installation/ , https://docs.astral.sh/uv/guides/projects/ , https://docs.astral.sh/uv/concepts/projects/sync/ , https://docs.astral.sh/uv/guides/integration/github/ , https://docs.astral.sh/uv/pip/compatibility/
- uv GitHub + benchmarks: https://github.com/astral-sh/uv , https://github.com/astral-sh/uv/blob/main/BENCHMARKS.md , https://github.com/astral-sh/uv/releases
- Poetry 2.3 announcement: https://python-poetry.org/blog/announcing-poetry-2.3.0/
- PDM lockfile: https://pdm-project.org/latest/usage/lockfile/
- Hatch envs / releases: https://hatch.pypa.io/dev/environment/ , https://github.com/pypa/hatch/releases
- 2026 comparisons: https://pratikpathak.com/uv-vs-pdm-vs-poetry-2026-comparison/ , https://cuttlesoft.com/blog/2026/01/27/python-dependency-management-in-2026/ , https://pydevtools.com/handbook/explanation/which-python-package-manager-should-i-use/
- PyCharm 2026 uv workspaces: https://blog.jetbrains.com/pycharm/2026/05/support-for-uv-poetry-and-hatch-workspaces-beta/
