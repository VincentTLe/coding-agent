# Claude Code Memory System

Source: https://code.claude.com/docs/en/memory (Anthropic official docs)

## Two complementary mechanisms

| Aspect | CLAUDE.md files | Auto memory |
|---|---|---|
| Who writes | You | Claude (v2.1.59+) |
| Contains | Instructions, rules | Learnings, build commands, patterns |
| Loaded | Every session | Every session (first 200 lines / 25 KB of `MEMORY.md`) |

Both are delivered as **user messages after the system prompt**, not in the system prompt. Treated as context, not enforced configuration.

## CLAUDE.md hierarchy (load order, broad → specific)

1. **Managed policy** — `/Library/Application Support/ClaudeCode/CLAUDE.md` (macOS), `/etc/claude-code/CLAUDE.md` (Linux), `C:\Program Files\ClaudeCode\CLAUDE.md` (Windows). Org-wide, can't be excluded by users.
2. **User** — `~/.claude/CLAUDE.md`.
3. **Project** — `./CLAUDE.md` or `./.claude/CLAUDE.md` (checked into VCS).
4. **Local** — `./CLAUDE.local.md` (gitignored).

Claude walks up the directory tree from CWD to the repo root, concatenating all CLAUDE.md/CLAUDE.local.md it finds. Files in subdirectories load **on demand** when Claude reads files in those directories. Imports use `@path/to/file` syntax, up to 5 hops deep.

## `.claude/rules/` (path-scoped instructions)

Markdown files under `.claude/rules/` with optional frontmatter:
```yaml
---
paths:
  - "src/api/**/*.ts"
---
```
Rules **without** `paths` load at session start. Rules **with** `paths` load only when Claude reads matching files. User-level rules in `~/.claude/rules/`.

## Auto memory (v2.1.59+, on by default)

- Per-project directory: `~/.claude/projects/<project>/memory/` (project key derived from git repo, so worktrees share).
- Entry: `MEMORY.md` — concise index, first 200 lines / 25 KB loaded every session.
- Spillover: any number of topic files (`debugging.md`, `api-conventions.md`, ...) — **not** auto-loaded; Claude reads them on demand.
- Plain markdown; user can edit/delete via `/memory`.
- Machine-local; not synced across clouds.

## Context overflow handling — `/compact`

- Auto-fires at ~95% context capacity (25% remaining). Manual `/compact [instructions]` at ~60% gives higher-quality summary.
- Compresses dialog history into a summary, starts a new session with the summary preloaded.
- **Project-root CLAUDE.md is re-read from disk after compaction.** Nested CLAUDE.md files reload lazily.
- Tool results are trimmed; prompt-cache-friendly placement is preserved.

## Why it works for coding agents

It's intentionally **database-free** — everything is markdown on disk. Diffable, reviewable, gitignorable, no extra service to run. The price: no vector recall, no cross-project memory, no embedding-based retrieval. Trades sophistication for inspectability.
