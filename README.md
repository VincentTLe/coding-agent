# Coding Agent from Scratch

**A from-scratch ReAct coding agent — no agent frameworks — driving a local Qwen3-14B model to read, edit, run, and verify code.**

🇻🇳 Tiếng Việt: [README.vi.md](README.vi.md)

This is a coding agent built from first principles: no LangChain, no LangGraph, no CrewAI. The ReAct loop, the tool layer, the sandbox, and the context management are all hand-written against the raw OpenAI-compatible chat-completions API. The model runs locally — **Qwen3-14B served by vLLM** on a single NVIDIA A6000 — and is given **11 tools**; the file tools are confined to a workspace by a **path-traversal guard** (see *Sandbox and safety* for the honest threat model). The interesting part is reliability: the agent runs `pytest`, reads the failures, patches the source, and re-runs until the suite is green, and the interactive REPL survives long sessions through **token-budget context compaction**. A **627-task benchmark harness** measures all of this with honest, hidden-test scoring.

Built as Math/Stat 361 undergraduate research at Knox College (advisor: Prof. Andrew Leahy).

---

## Highlights

- **Built from scratch** — the agent loop, tool dispatch, sandbox, and streaming UI are hand-written. The only third-party pieces are the OpenAI SDK (HTTP transport) and vLLM (model serving).
- **Runs a local open-weight model** — Qwen3-14B via vLLM, OpenAI-compatible endpoint, fully on-prem on one A6000. No hosted API.
- **11 tools across 5 groups** — file I/O, code discovery, execution, delegation, and completion (see table below).
- **Verifies its own work** — it executes the test suite, inspects failures, edits the source, and loops until tests pass. Demonstrated end-to-end fixing a buggy repo to **11/11 passing**.
- **Sandboxed and crash-resistant** — every file operation is confined to an explicit workspace directory via a path-traversal guard; tool failures are returned to the model as text rather than crashing the loop.
- **Context compaction** — the interactive REPL estimates token usage and auto-summarizes old history past a 24k-token threshold while keeping the 10 most recent messages verbatim, so it stays inside a 32K context window on long tasks.
- **Safe-by-design edits** — surgical edits require an exact, unique match; multi-edit is all-or-nothing, so a failed edit never leaves a half-modified file.
- **627-task eval harness** — a benchmark of 163 HumanEval+, 424 sanitized MBPP, 37 hand-authored hard tasks, and 3 legacy demos. It runs agents in parallel (`--jobs N`), scores each with an independent `pytest` the agent never controls, **hides benchmark tests from the agent while it works** so it can't hard-code answers, and a validation gate proves every task is real (reference solution passes, stub fails).

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Terminal (you)  ── type a task → watch streamed output        │
└───────────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────┐
│  Agent process  (cli/chat.py REPL, or cli/solve.py / src.agent)│
│  ────────────────────────────────────────────────────────     │
│   ReAct loop:                                                  │
│     1. Send messages + tool schemas to the model               │
│     2. Stream back: reasoning · answer · tool_calls             │
│     3. If no tool_calls → done                                 │
│     4. Else execute each tool, append results, loop            │
│     5. Safety net: stop after max iterations                   │
│   Context compaction kicks in past 24k estimated tokens        │
└───────────────────────────────┬──────────────────────────────┘
                                 │ HTTP  POST /v1/chat/completions
                                 ▼
┌──────────────────────────────────────────────────────────────┐
│  vLLM server  (localhost:8765)                                 │
│  ────────────────────────────────                              │
│   Model:    Qwen3-14B (BF16, ~28 GB) on one A6000              │
│   Context:  --max-model-len 32768  (32K)                       │
│   Parsers:  --reasoning-parser qwen3   (splits <think> blocks) │
│             --tool-call-parser hermes  (parses tool-call XML)  │
│             --enable-auto-tool-choice                          │
└──────────────────────────────────────────────────────────────┘
```

The loop is plain ReAct (reason → act → observe), implemented directly against the chat-completions protocol. The model emits tool calls in the Hermes format and a `<think>` reasoning block; vLLM's **hermes tool-call parser** and **qwen3 reasoning parser** turn those into structured `tool_calls` and `reasoning_content` that the agent reads. Tools are a registry (`name → function` plus a JSON schema list), so adding a tool is append-only — the loop never changes.

---

## The 11 tools

All defined in [`src/tools.py`](src/tools.py) — implementation, JSON schema, and a single `execute_tool()` dispatcher side by side.

| Group | Tool | What it does |
|---|---|---|
| **File I/O** | `read_file` | Return the full contents of a file. |
| | `write_file` | Overwrite or create a file with full content. |
| | `apply_patch` | Surgical search-and-replace; `old_text` must match **exactly once** (refuses ambiguous edits). |
| | `multi_edit` | Multiple edits to one file, applied **atomically** (all-or-nothing). |
| **Discovery** | `list_dir` | List a directory's files and sub-directories with sizes. |
| | `glob_files` | Match files by glob pattern (e.g. `**/*.py`). |
| | `grep_files` | Regex search across files, returning `path:line` hits. |
| **Execution** | `run_bash` | Run a shell command (pytest, git, pip…), 600s timeout. |
| | `run_python` | Run a short Python snippet, 60s timeout. |
| **Delegation** | `spawn_subagent` | Run a child agent in a separate process for an isolated subtask (300s timeout, 8 iterations). |
| **Completion** | `finish` | Explicitly end the session with a one-line summary; replying in prose without a tool call does **not** finish the task. |

**Why `spawn_subagent` is a separate process:** the child gets its own message history (context isolation), a crash in the child can't take down the parent, and a hard 300s timeout plus an 8-iteration cap bound recursion.

---

## Context compaction

Long conversations overflow the 32K context window. The interactive REPL ([`cli/chat.py`](cli/chat.py)) handles this automatically:

- `estimate_tokens()` approximates token usage each turn (roughly chars / 4).
- When the estimate crosses `COMPACT_THRESHOLD_TOKENS = 24000` (~75% of context), `compact_messages()` summarizes the older history into a single message and keeps the most recent `KEEP_RECENT_MESSAGES = 10` messages verbatim.
- `/compact` forces it manually; `/tokens` shows the current estimate against the threshold.

A subtle but important detail: the summary boundary must land on a user-role message, so an assistant's `tool_calls` is never orphaned from its `tool` result (otherwise the API rejects the request). Compaction is treated as a state-management correctness problem, not just truncation.

---

## Sandbox and safety

- **`_safe_path(path, workspace)`** resolves every requested path against the workspace directory passed in and refuses anything that escapes it — a CWE-22 path-traversal defense. The workspace is an explicit parameter threaded through `run_agent(goal, workspace, ...)` and `execute_tool(name, args, workspace)` — there is no global workspace state. The seven path-taking tools (`read_file`, `write_file`, `apply_patch`, `multi_edit`, `grep_files`, `glob_files`, `list_dir`) cannot read or write outside the workspace (the CLI default is `demo_repo/`).
- **Threat model and limitations.** The sandbox protects against model *accidents* on file paths, not against arbitrary code: the three execution tools (`run_bash`, `run_python`, `spawn_subagent`) run with the invoking user's full privileges, constrained only by `cwd` and a timeout. A command like `cat ~/.ssh/id_rsa` or an absolute-path write is not blocked. This is a deliberate trade-off for a local research agent on the owner's own machine; true isolation would require a container/bwrap layer, which this project does not claim to have.
- **Errors are returned, not raised.** `execute_tool()` catches exceptions and bad arguments and returns them to the model as `ERROR: ...` strings, so a failed tool call becomes feedback the agent can recover from instead of a crash.
- **Edits are safe by construction.** `apply_patch` refuses to edit on zero or multiple matches; `multi_edit` validates all edits before writing, so the file on disk is never left partially modified.

---

## Quickstart

Requires the vLLM server running (one NVIDIA GPU with enough VRAM for Qwen3-14B in BF16, ~28 GB) and the project virtualenv.

**1. Start the model server** ([`scripts/start_vllm.sh`](scripts/start_vllm.sh) — Qwen3-14B, 32K context, port 8765):

```bash
bash scripts/start_vllm.sh
# wait for "Application startup complete"; verify with:
curl -sf http://localhost:8765/v1/models
```

**2. Run the interactive REPL** (streaming chat + tools + `/think`, `/compact`, `/tokens`):

```bash
python cli/chat.py
```

**3. Or run a one-shot task** with the non-streaming agent loop:

```bash
python cli/solve.py "Fix all failing tests in demo_repo/"
# equivalently: python -m src.agent "Fix all failing tests" --workspace demo_repo
```

**4. Run the eval harness** ([`eval/run.py`](eval/run.py)) over the benchmark:

```bash
python eval/run.py                          # all 627 tasks, one at a time
python eval/run.py --jobs 8                  # 8 agents in parallel
python eval/run.py --filter difficulty=hard  # filter by metadata
python eval/run.py 01_strings                # a single task
```

---

## Results and status

End-to-end verified on `demo_repo/`: starting from a buggy `is_prime`/`factorial`/`calculator`, the agent ran `run_bash(pytest)` → `read_file` → `apply_patch` → `run_bash(pytest)` and reached **11/11 tests passing** — fixing only the source, never the tests.

At scale, the eval harness ([`eval/README.md`](eval/README.md)) runs **627 tasks**: 163 HumanEval+, 424 sanitized MBPP, 37 hand-authored hard tasks (debugging, refactor, multi-file, DP, graphs, data structures, OOP, parsing, algorithms, recursion), and 3 legacy demos. Each run snapshots and restores the task fixtures, scores with an independent `pytest` the agent never controls, and **hides the benchmark tests from the agent while it works** (restored only for grading) so it implements from the spec rather than hard-coding outputs; debug/refactor tasks keep tests visible so the agent can use `pytest` as a feedback signal. A guardrail nudges the model if it replies without acting and records `no_action` rather than failing silently, and a validation gate (`eval/validate_tasks.py`) proves every task is real before it counts. The latest clean full run scored **422/627 (67.3%, 95% CI 64–71%)**: **HumanEval+ 79.8%**, **de-leaked MBPP 66.7%**, **curated hand-written hard 21.6%**; by difficulty **easy 74% · medium 74% · hard 54%**, with **66/627** tasks ending in `no_action`. An earlier run reported 79.9%, but that figure was inflated by an MBPP benchmark leak — for ~93% of the 424 MBPP tasks, 2 of the 3 graded asserts had leaked into the agent-visible goal; that leak is now fixed (spec-only goals, regenerated), while HumanEval+ was never affected. Full per-task results and the per-category/difficulty breakdown live in **`eval/results/`** (older runs there predate the fix; see [`eval/README.md`](eval/README.md)).

**Honest scope.** This is undergraduate research, not a SWE-Bench entry. HumanEval/MBPP are well-known and partially saturated for modern models, so the benchmark tier is a breadth + harness-sanity signal while the curated hard tier is the more honest stress test; an open-weight 14B model is stochastic, so pass rates are best read over multiple runs (`--repeats K`). Known limitations: limited interruptibility and no tool-result caching. The vLLM server is run on demand on a shared GPU, not kept always-on.

---

## Repo layout

```
coding-agent/
├── cli/                    how you RUN the real agent
│   ├── chat.py             primary REPL: streaming + tools + compaction
│   └── solve.py            one-shot task runner
├── src/                    the agent library (importable, no side effects)
│   ├── agent.py            ReAct loop — run_agent(goal, workspace, ...)
│   ├── tools.py            11 tools + JSON schemas + dispatcher + sandbox
│   └── prompts.py          system prompt
├── examples/               teaching ladder: 01→04, read to learn (not to run)
├── tests/                  pytest unit tests (sandbox, tools, dispatcher)
├── eval/                   the 627-task benchmark harness
│   ├── run.py              parallel runner (snapshot → run → score → restore)
│   ├── validate_tasks.py   quality gate (reference passes, stub fails)
│   ├── convert_benchmark.py regenerates HumanEval+/MBPP tasks
│   └── tasks/              bench/ (HE+ & MBPP) · curated/ · legacy demos
├── demo_repo/              default sandbox workspace (11-test demo)
└── scripts/start_vllm.sh   launch the vLLM server
```

**Further reading:**
- [`SYSTEM_DEEP_DIVE.md`](docs/SYSTEM_DEEP_DIVE.md) — a thorough walkthrough of the chat-completions protocol, streaming, tool calling, and every tool's rationale.
- [`PRESENTATION.html`](docs/decks/PRESENTATION.html) — slide deck for the research checkpoint.
- [`eval/README.md`](eval/README.md) — the benchmark, how to run it, and its caveats.

---

*Math/Stat 361 Research, Knox College — advisor Prof. Andrew Leahy.*
