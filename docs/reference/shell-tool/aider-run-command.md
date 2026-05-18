# Aider /run command (cached reference)

Sources:
- https://aider.chat/docs/usage/lint-test.html
- https://aider.chat/docs/scripting.html
- https://github.com/Aider-AI/aider/issues/1337
Fetched: 2026-05-18

## Design
- `/run <cmd>` lets the user run a command in the terminal environment Aider is launched from.
- No sandbox. Aider is a CLI pair-programmer; it inherits the user's shell, env, and cwd.
- Captures combined stdout+stderr.
- After execution, Aider prompts "Add the output to the chat?" — the user chooses whether to feed it back to the model.
- Exit code is interpreted in lint/test workflows: non-zero on stdout/stderr means "please fix this".

## Safety model
- Not a sandbox. Suggesting-shell-commands is on by default.
- When the model proposes a command, the user is prompted Y/N (and can edit before running).
- No documented blocklist of dangerous commands — relies entirely on user confirmation.
- No documented timeout — relies on user pressing Ctrl-C.

## Implications for our project
- Aider's model is "human in the loop, no sandbox." That's a different threat model from autonomous Claude Code-style agents.
- Useful precedent: explicit confirmation prompts, optionally piping output back into chat.
