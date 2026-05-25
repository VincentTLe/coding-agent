# examples/ — the teaching ladder

A reading ladder, not a runnable app. Open the files **in order** and read them
top-to-bottom: each one adds exactly one idea on top of the last, building toward
the real agent in [`src/`](../src). The comments are dense (mostly Vietnamese) and
explain every line — the point is to *understand* how a coding agent works, then
go read the production code.

Every lesson is self-contained and runnable. They target the local setup in
`.env`: **Qwen3-14B served by vLLM** (OpenAI-compatible API). Make sure the server
is up, then:

```bash
source .venv/bin/activate
python examples/01_chat.py          # or 02_, 03_, 04_
```

## The ladder

| # | File | Teaches | Key new concept |
|---|------|---------|-----------------|
| 1 | [`01_chat.py`](01_chat.py) | Plain multi-turn chat, **no tools** | The server is stateless; the `messages` list **is** the memory. |
| 2 | [`02_one_tool.py`](02_one_tool.py) | Give the model **one** tool, handle **one** `tool_call` by hand | Tool JSON schema, `msg.tool_calls`, the `role:"tool"` result message, and the `tool_call_id` that pairs them. |
| 3 | [`03_react_loop.py`](03_react_loop.py) | The minimal **ReAct loop** (reason → act → observe) over 2–3 tools | Looping until no `tool_calls` or `max_iters`; the **pairing invariant** (one tool result per `tool_call_id`) and **termination**. |
| 4 | [`04_sandbox_safety.py`](04_sandbox_safety.py) | The **safety layer** between the model and your machine | `_safe_path` confining file ops to a workspace (a path-escape gets rejected), and the "tools return `ERROR` strings, never raise" contract — so the model can *recover* from a bad call instead of crashing the loop. |

Read them in sequence: 01 → 02 → 03 → 04. Lesson 3 is the distilled heart of
`src/agent.py`; lessons 2–4 import the real `execute_tool` / `TOOL_SCHEMAS` /
`_safe_path` from [`src/tools.py`](../src/tools.py) so what you read matches what
the agent actually runs.

## Running the real agent

The lessons are for *learning*. To actually **drive the agent**, use the CLIs in
[`cli/`](../cli) (these wrap the same `src/agent.py` engine):

```bash
# Interactive REPL — streaming reply + live thinking + step-by-step tool calls
python cli/chat.py

# One-shot — run a single task to completion and exit
python cli/solve.py "Fix the failing tests in demo_repo/"

# Or call the agent module directly (what cli/solve.py wraps)
python -m src.agent "Fix the failing tests in demo_repo/"
```

## The real implementation lives in `src/`

- [`src/agent.py`](../src/agent.py) — the production ReAct loop (`run_agent`): time
  budget, API-error handling, the "nudge" when the model answers without acting,
  and careful `finish_reason` bookkeeping. Lesson 3 is this loop with the extras stripped off.
- [`src/tools.py`](../src/tools.py) — the 10 tools (`read_file`, `write_file`,
  `run_bash`, `apply_patch`, `multi_edit`, `grep_files`, `glob_files`, `list_dir`,
  `run_python`, `spawn_subagent`), plus `_safe_path`, the `TOOLS` / `TOOL_SCHEMAS`
  registry, and the `execute_tool(name, json_args, workspace)` dispatcher.
- [`src/prompts.py`](../src/prompts.py) — the single system prompt the agent runs with.
