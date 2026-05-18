# D3 — Shell Execution Tool Design for Coding Agents (2026)

## TL;DR

Adopt a `run_bash` tool shaped like Claude Code's (one `command` string plus optional `timeout_sec`, `cwd`, `run_in_background`, `restart`) with OpenHands-style soft/hard timeouts and a companion `bash_output` poller. Defaults: 120 s soft / 600 s hard timeout, 30,000-char middle-truncated output (full spilled to disk), combined stdout+stderr, persistent shell, no interactive TTY, sandbox-first safety.

## Why

`run_bash` is the foundation: every build, test, lint, install, and git op flows through it. Anthropic flags persistent-shell access as a measured Terminal-Bench 2.0 driver. The 2026 design space has converged on a single string command + persistent shell; the choices that matter are defaults, background handling, and where safety lives.

## State of the art, 2026

- **Claude Code (`bash_20250124`)** — schema-less, persistent. Default 120 s, hard ceiling 600 s. 30,000-char cap, middle-truncated; `BASH_MAX_OUTPUT_LENGTH` overrides; full output spilled to disk in recent builds. `run_in_background` + `BashOutput` polling. Known quirks: stderr/stdout interleaving broken, `/dev/stdin` hangs, no live streaming.
- **OpenHands `execute_bash`** — `{command, cwd?, timeout?, is_input?, reset?}`. 10 s soft (prompts agent to wait/interact) + hard `timeout` (default 300 s). Returns `{exit_code, stdout, stderr, ...}` with `exit_code: null` while running. Docker sandbox, WebSocket streaming, per-repo `.openhands/hooks.json` PreToolUse hooks.
- **Aider `/run`** — no sandbox, no blocklist, no timeout. Combined output, post-run "add to chat?" prompt. Non-zero exit drives lint/test loops.
- **SWE-agent** — stateless `subprocess.run` per action (swappable to `docker exec`).

**Consensus:** one `command` string; persistent shell + cwd/env (except SWE-agent); combined stdout+stderr (separation caused Claude Code's interleaving bug); sandboxing is the real defense — agent-layer allowlists get bypassed by `&&`, `;`, `|`, `$(…)`, and backticks.

**Most-used:** Claude Code's `bash` tool is the de-facto standard.

## Comparison

| Concern | Claude Code | OpenHands | Aider | Recommended |
|---|---|---|---|---|
| Default / max timeout | 120 / 600 s | 300 s hard, 10 s soft | none | 120 s soft / 600 s hard |
| Output cap | 30k chars, mid-trunc, disk spill | undocumented | unbounded | 30k chars, mid-trunc, spill `.agent/logs/<id>.log` |
| Streaming | No | WebSocket | No | No in v1 |
| stderr/stdout | Separate (broken) | Separate fields | Combined | Combined `2>&1` to model; raw on disk |
| stdin | Unsupported, hangs | `is_input` | TTY | Refuse `/dev/stdin` in v1 |
| cwd / env | Persists in session | Per-call cwd; env persists | Inherits | Persists; `restart` clears |
| Background | `run_in_background` + `BashOutput` | soft-timeout interactive | None | `run_in_background` + `bash_output` |
| Multi-line | Heredocs | Heredocs | Heredocs | Heredocs (documented) |
| Blocked cmds | Sandbox + hooks | hooks.json | None | PreToolUse hook + sandbox |

## Recommendation — schema and defaults

```json
{
  "name": "run_bash",
  "description": "Run a bash command in a persistent shell. cwd and env persist. stdout+stderr merged. Heredocs for multi-line. Prefer Read/Grep over cat/grep/find; if grep, use rg. No interactive commands (vim, less, prompts). Long jobs: run_in_background then poll bash_output.",
  "input_schema": {
    "type": "object",
    "properties": {
      "command":           {"type": "string"},
      "timeout_sec":       {"type": "integer", "minimum": 1, "maximum": 600, "default": 120},
      "cwd":               {"type": "string"},
      "run_in_background": {"type": "boolean", "default": false},
      "restart":           {"type": "boolean", "default": false}
    },
    "required": ["command"]
  }
}
```

Companion `bash_output`: `{task_id, mode: incremental|tail:100|full, filter?}`.

**Load-bearing defaults:** 120 s soft / 600 s hard; 30k-char middle-truncated output with full transcript on disk; combined stdout+stderr; cwd defaults to project root; env persists until `restart`; always include `[exit: N, duration: 1.2s, truncated: true]`; no v1 stdin.

**Safety defaults:** (1) sandbox is the primary defense — container, non-root, tmpfs scratch, no host net; (2) PreToolUse hook with small deny list matched after `$(…)`/backtick expansion: `rm -rf /|~|/*`, `sudo`, `su -`, `dd if=/dev/zero of=/dev/sd*`, `mkfs.*`, `shutdown`, `reboot`, `chmod -R 777 /`, `chown -R … /`, fork-bomb, `curl … | sh`, `wget … | bash`; (3) no agent-layer string allowlist (chained commands bypass it); (4) audit log `.agent/audit.jsonl`; (5) route large writes to file-write tool.

## Next steps

1. `BashSession` (`subprocess.Popen(["bash","-i"])`, merged stream via PTY or `2>&1`, reader threads).
2. Soft timeout via `select`; SIGTERM at soft, SIGKILL +5 s; hard cap kills the tree.
3. `task_id` registry + log-spill files.
4. PreToolUse deny-list hook; test against chained-command bypass corpus.
5. Sandbox: Docker `--read-only`, tmpfs `/tmp`, project mount, `--cap-drop=ALL --security-opt=no-new-privileges`.
6. Tool description steers model: use `rg`, absolute paths over `cd`, heredocs for multi-line.

## Open questions

- Live streaming to agent (not just user) in v1? [UNVERIFIED] Claude Code doesn't; OpenHands does. Defer.
- PTY vs pipe? Pipe in v1 (forces non-interactive).
- `cwd` accept `~`/relative? Recommend absolute-only.
- Background log retention? [UNVERIFIED] 24 h or session end.

## Sources

- [Anthropic Bash tool docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/bash-tool)
- [Claude Code #25881 hard timeout](https://github.com/anthropics/claude-code/issues/25881)
- [Claude Code #19901 30k output / middle-truncation](https://github.com/anthropics/claude-code/issues/19901)
- [Claude Code #2734 stderr/stdout interleaving](https://github.com/anthropics/claude-code/issues/2734)
- [Claude Code #16306 `/dev/stdin` hang](https://github.com/anthropics/claude-code/issues/16306)
- [Claude Code #2550 background bash](https://github.com/anthropics/claude-code/issues/2550)
- [Claude Code #9997 BashOutput output_mode](https://github.com/anthropics/claude-code/issues/9997)
- [Claude Code #36637 chained-command bypass](https://github.com/anthropics/claude-code/issues/36637)
- [mfyz allowlist substitution bypass](https://mfyz.com/claude-code-allowlist-command-substitution-bypass/)
- [OpenHands execute_bash API](https://docs.openhands.dev/sdk/guides/agent-server/api-reference/bash/execute-bash-command)
- [OpenHands PR #8106 hard timeout](https://github.com/All-Hands-AI/OpenHands/pull/8106)
- [OpenHands #7422 10 s soft timeout](https://github.com/All-Hands-AI/OpenHands/issues/7422)
- [OpenHands hooks docs](https://docs.openhands.dev/openhands/usage/customization/hooks)
- [Aider lint/test docs](https://aider.chat/docs/usage/lint-test.html)
- [Aider #1337 Run Shell Commands](https://github.com/Aider-AI/aider/issues/1337)
- [SWE-agent](https://github.com/SWE-agent/SWE-agent)
- [Piebald-AI Claude Code system prompts](https://github.com/Piebald-AI/claude-code-system-prompts)
