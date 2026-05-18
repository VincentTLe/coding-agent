# Claude Code Bash tool (cached reference)

Source: https://platform.claude.com/docs/en/agents-and-tools/tool-use/bash-tool
Fetched: 2026-05-18

## Tool identity
- Tool type: `bash_20250124`, name `bash` — schema-less (input schema is built into the model).
- Adds ~245 input tokens to API calls.

## Parameters
| Parameter | Required | Description |
|-----------|----------|-------------|
| `command` | Yes (unless restart) | The bash command to run |
| `restart` | No | `true` to restart the bash session |

## Documented semantics
- Persistent bash session: env vars and cwd persist across calls. State is client-side; the API is stateless and the application owns session lifetime.
- Returns combined stdout/stderr text to the model.
- No streaming: "Results returned after completion."
- No interactive commands (no `vim`, `less`, password prompts).
- Large outputs "may be truncated."

## Operational limits (Claude Code in practice)
From GitHub issues #25881 and #19901:
- Default per-command timeout: 120000 ms (2 minutes).
- Maximum timeout: 600000 ms (10 minutes) — hard ceiling, no env override.
- Output cap: 30,000 characters. Middle-truncation preserves head and tail. Override via `BASH_MAX_OUTPUT_LENGTH` env var. Recent builds also save full output to disk so the agent can re-read it.

## Background tasks
- Ctrl+B / `run_in_background: true` starts the command async, returns a task id immediately.
- `BashOutput` polling tool reads new output since last check (per shell_id) and reports exit code when done.
- Known limitation: high latency between event in process and the agent observing it; tokens spent on polling.

## Known quirks
- stderr/stdout interleaving is not preserved — stdout lines tend to appear before stderr lines (issue #2734). Workaround: `cmd 2>&1`.
- Reading `/dev/stdin` inside the Bash tool causes a hang (issue #16306).
- Spawning `claude -p` as a child can suppress output of the entire bash session (issue #28407).

## Documented safety guidance (from official docs)
- Run in an isolated environment (Docker/VM).
- Prefer allowlist over blocklist; reject shell operators (`&&`, `||`, `|`, `;`, `&`, `>`, `<`, `>>`).
- For stronger isolation, use `shell=False` with `shlex.split`.
- Set `ulimit` resource constraints; filter `sudo`, `rm -rf`, etc.; log every command.

## Notable system-prompt-level guidance to the model
- Prefer Read/Grep/Glob tools over `cat`/`head`/`tail`/`find`/`ls`/`grep`.
- If grep is needed, use `rg` (ripgrep) — pre-installed.
- Avoid `cd`; use absolute paths instead.
