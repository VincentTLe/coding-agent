# OpenHands execute_bash tool (cached reference)

Sources:
- https://docs.openhands.dev/sdk/guides/agent-server/api-reference/bash/execute-bash-command
- https://github.com/All-Hands-AI/OpenHands/pull/8106 (hard timeout PR)
- https://github.com/All-Hands-AI/OpenHands/issues/7422 (soft timeout proposal)
- https://docs.openhands.dev/openhands/usage/customization/hooks
Fetched: 2026-05-18

## Architecture
- Sandboxed runtime (Docker by default; QEMU microVM and Daytona variants exist).
- Runtime exposes three action types: `IPythonRunCellAction`, `CmdRunAction`, `BrowserInteractiveAction`.
- WebSocket event streaming for real-time observation back from the sandbox.
- V1 SandboxService has configurable defaults (e.g. default_timeout_seconds=120 at the sandbox level).

## execute_bash parameters
| Parameter | Description |
|-----------|-------------|
| `command` | The bash command to execute |
| `cwd` | Optional working directory override |
| `timeout` | Max seconds the command may run (hard timeout) |
| `is_input` | Whether the input should be sent as stdin to a running process |
| `reset` | Reset the bash session |

## Defaults
- Hard timeout (per-call): default 300 s, set via `timeout`.
- Soft timeout (no-new-output prompt): 10 s; after 10 s of silence the runtime prompts the agent that it may wait longer, send empty/other commands to interact, or set `timeout` for future commands.
- Sandbox startup timeout: 120 s (SANDBOX_TIMEOUT env override).

## Return shape (`BashOutput`)
- `command`
- `exit_code` — null while running, integer once complete
- `stdout`
- `stderr`
- execution order / sequencing metadata

## Safety
- `.openhands/hooks.json` per-repo hooks: pre-execution scripts that can block dangerous commands (e.g. `rm -rf /`), enforce quality gates before "finish", inject context.
- Sandboxed execution is the primary defense; agent has root-ish powers inside the container only.
