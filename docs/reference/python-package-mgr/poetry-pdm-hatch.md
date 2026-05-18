# Poetry / PDM / Hatch — Reference Notes (cached 2026-05-18)

## Poetry

Source: https://python-poetry.org/

- Latest: Poetry 2.4.1 (released 2026-05-09). 2.3.0 (2026-01-18) added `pylock.toml` export support and re-resolve config.
- Lockfile: `poetry.lock` (TOML, committed). Poetry-specific format, not PEP 751.
- Workflow:
  - `poetry new myproj` / `poetry init`
  - `poetry add requests` / `poetry add --group dev pytest`
  - `poetry install` / `poetry install --sync` (prune extraneous)
  - `poetry lock` / `poetry lock --no-update`
  - `poetry run pytest` / `poetry shell`
- Python versions: relies on system pyenv or asdf; Poetry itself does not download interpreters.
- Speed (2026 benchmarks): cold install from lock ~11 s vs uv ~3 s on Sentry's dep list. Lock generation ~22 s vs uv ~8 s. [UNVERIFIED exact numbers, from third-party shootout]
- Notable 2026 change: optional `pylock.toml` export aligns with PEP 751 standardization.

## PDM

Source: https://pdm-project.org/

- Lockfile: `pdm.lock` (TOML). Version 4.5.0 introduced in PDM 2.17 (cross-platform required explicit strategy in <4.5).
- Workflow:
  - `pdm init`
  - `pdm add requests` / `pdm add -dG dev pytest`
  - `pdm install` / `pdm sync`
  - `pdm lock`
  - `pdm run pytest`
- Strengths: PEP 621 native; supports PEP 582 (`__pypackages__`, no venv) — niche but unique.
- Cross-platform lock by default; `inherit_metadata` strategy on by default since 2.11 for faster installs.
- Can use uv as installer backend for speed.
- Python versions: detects system installs; no built-in downloader (uses `findpython`).

## Hatch

Source: https://hatch.pypa.io/

- Latest: 1.16.5 (released 2026-02-27). [UNVERIFIED exact patch date]
- Lockfile: **no native single-lockfile model**. Supports PEP 751 `pylock.toml` per environment via `hatch env lock` (with `locked = true`).
- For "real" lockfiles, community plugin `hatch-pip-compile` (uses pip-compile or uv under the hood).
- Workflow:
  - `hatch new myproj`
  - `hatch env create`
  - `hatch run pytest`
  - `hatch shell`
  - Environment matrix: define one env that spans 3.11/3.12/3.13 automatically (Hatch's signature feature).
- Strengths: PyPA-maintained, official build backend (`hatchling`), best-in-class build/publish pipeline, matrix testing.
- Weaknesses: lockfile story still maturing in 2026; not a lockfile-first tool.

## pip (baseline)

- Latest: pip 25.x line. No project model, no lockfile, no Python install.
- `requirements.txt` is the de-facto lockfile (flat, unresolved without pip-tools).
- Universally available, zero learning curve, but no dependency resolution caching, no workspaces, no dev groups.

## Benchmark snapshot (Sentry deps, 2026 shootout)

| Operation | uv | Poetry | pip-tools |
|---|---|---|---|
| Cold install from lock | ~3 s | ~11 s | ~33 s |
| Cold lock generation | ~8 s | ~22 s | ~35 s |

Numbers from https://github.com/zanieb/packse-style shootouts and Astral's own BENCHMARKS.md. [UNVERIFIED exact values; rerun for ground truth.]
