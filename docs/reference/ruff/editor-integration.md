# Cached: Ruff — Editor integration

Source: https://docs.astral.sh/ruff/editors/setup/
Fetched: 2026-05-18

All modern editors speak to a single `ruff server` (LSP), shipped in the `ruff` binary.

## VS Code

Extension: `charliermarsh.ruff` (>= 2024.32.0). Provides diagnostics, code actions, format-on-save. Pin matching `ruff` version in workspace settings or rely on the bundled one.

## PyCharm

Native since 2025.3: **Settings → Python → Tools → Ruff**. Two modes: Interpreter (find installed) or Path (system `$PATH`).

## Neovim (0.11+)

```lua
vim.lsp.config('ruff', { cmd = { 'ruff', 'server' } })
```
Format-on-save via `conform.nvim` with `ruff_format`.

## Helix / Emacs / Sublime / Zed

- Helix: `command = "ruff"`, `args = ["server"]`
- Emacs Eglot: `("ruff" "server")`, hook `eglot-format` to save
- Sublime: LSP + LSP-ruff packages
- Zed: built-in by default; tune via `lsp.ruff.initialization_options.settings`
