# uv — Official Reference Notes (cached 2026-05-18)

Source: https://docs.astral.sh/uv/ (Astral)

## Version

- Latest stable: uv 0.11.14 (released 2026-05-04 per GitHub Releases / PyPI). [UNVERIFIED specific date]
- Written in Rust, distributed as a single static binary.

## Installation (standalone)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

- Help: `curl -LsSf https://astral.sh/uv/install.sh | sh -s -- --help`
- Disable PATH modification: `... | env UV_NO_MODIFY_PATH=1 sh`
- CI-friendly install: set `UV_UNMANAGED_INSTALL=/path` to drop binary without touching profiles.
- Pin a version in CI: `curl -LsSf https://astral.sh/uv/0.11.14/install.sh | sh` (URL-pinned).

## Core commands (project mode)

| Command | Purpose |
|---------|---------|
| `uv init <name>` | New project: pyproject.toml + .python-version + starter src |
| `uv add <pkg>[==ver]` | Add runtime dep (writes pyproject + uv.lock, syncs .venv) |
| `uv add --dev <pkg>` | Add to dev group |
| `uv remove <pkg>` | Remove dep |
| `uv sync` | Reconcile .venv with uv.lock (CI: add `--locked --all-extras --dev`) |
| `uv lock` | Refresh uv.lock from pyproject |
| `uv run <cmd>` | Auto-syncs then runs in project env (no manual activate) |
| `uv tree` | Show resolved dep graph |
| `uv export --format requirements-txt` | Emit pip-compatible requirements.txt |
| `uv python install 3.11 3.12 3.13` | Install multiple CPython builds |
| `uv python pin 3.12` | Pin via `.python-version` |
| `uv run --python 3.13 pytest` | One-off override of interpreter |

## Lockfile

- File: `uv.lock` (TOML, committed to VCS).
- Cross-platform by default; resolves wheels/markers for every supported platform.
- Auto-managed: `uv run` re-locks if pyproject.toml has changed.

## Python interpreter management

- Downloads prebuilt CPython distributions (python-build-standalone). No system pyenv needed.
- `uv python install` finishes in seconds vs. pyenv compile.
- `--python <ver>` flag overrides .python-version for a single invocation; works on `run`, `sync`, `add`.

## GitHub Actions recipe

```yaml
- uses: astral-sh/setup-uv@v8
  with:
    version: "0.11.14"
    enable-cache: true
- run: uv sync --locked --all-extras --dev
- run: uv run pytest tests
```

- Cache: action persists `UV_CACHE_DIR`; run `uv cache prune --ci` to slim it.
- Python: either rely on `uv python install` (driven by `.python-version`) or use `actions/setup-python` with `python-version-file: ".python-version"` for slightly faster cold starts.

## pip compatibility surface

- `uv pip install / compile / sync` — drop-in pip-tools replacement.
- `uv export --format requirements-txt > requirements.txt` — emit a pinned flat file for Docker / Lambda / legacy deploy tools.
- Differences vs pip-compile: no implicit output file, strips extras by default, doesn't emit index URLs unless `--emit-index-url`.
- No user-install fallback (unlike pip's `--user` automatic fallback).

## Replaces (per official README)

pip, pip-tools, pipx, poetry, pyenv, twine, virtualenv (single binary, one toolchain).
