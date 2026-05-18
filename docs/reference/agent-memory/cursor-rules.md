# Cursor Project Memory & Rules (2026)

Sources:
- https://cursor.com/docs/rules
- https://docs.cursor.com/context/rules

## Modern format: `.cursor/rules/*.mdc`

Replaces the legacy single `.cursorrules` file. Each rule is a markdown file with optional YAML frontmatter; lives in `.cursor/rules/`; version-controlled with the project.

```yaml
---
description: "When and why this rule applies"
alwaysApply: false
globs: src/**/*.ts
---
# Rule body in markdown
```

## Four activation modes

| Mode | Trigger |
|---|---|
| **Always Apply** | `alwaysApply: true` — injected into every Agent prompt. |
| **Auto Attached** | `globs:` — attached when Agent touches matching files. |
| **Agent Requested** | Agent decides based on `description` field. |
| **Manual** | Only when user @-mentions the rule, e.g. `@my-rule`. |

## Scope

Applies to **Agent (Chat) only**. Cursor Tab and Inline Edit (Cmd-K) **do not** use rules.

## Legacy `.cursorrules`

Still read for backward compatibility. Migration is incremental: copy chunks into individual `.mdc` files, delete the old file when empty.

## `AGENTS.md`

Cursor also reads a project-root `AGENTS.md` (plain markdown, no frontmatter). Same concept, cross-tool: Claude Code, Cursor, OpenCode, others can all share it.

## Comparison to Claude Code

| | Claude Code | Cursor |
|---|---|---|
| File extension | `.md` | `.mdc` (markdown + frontmatter) or `.md` |
| Location | `CLAUDE.md`, `.claude/rules/` | `.cursor/rules/` |
| Path-scoping | `paths:` frontmatter on rules | `globs:` frontmatter |
| Always-on baseline | All CLAUDE.md ancestors load | `alwaysApply: true` rules |
| On-demand load | Subdir CLAUDE.md, rules w/o paths | Agent-Requested, Auto-Attached |
| Auto memory | Yes (Claude writes `MEMORY.md`) | No (rules are user-authored) |
| Cross-tool sync | Reads `AGENTS.md` via import or symlink | Reads `AGENTS.md` natively |

Both intentionally avoid vector DBs for project memory — both bet that **plain markdown on disk** is the right primitive for a coding agent.
