# AGENTS.md — coding-agent project

This project inherits all rules from `~/AGENTS.md`. Read that file first.
This file adds project-specific context and three project-specific rules.

## Project context

- Course: Math/Stat 361 Research (Knox College, advisor: Prof. Andrew Leahy)
- Final demo: May 29, 2026
- Purpose: A from-scratch coding agent. Every line must be understandable to the owner. AI assistants help; they do not autopilot.
- Owner's prior pain point: AI-generated codebases the owner could not explain. Avoid that failure mode here.

## Stack (verified — change only with owner approval)

- Python 3.12 via `uv` (NOT conda for this project)
- Inference: vLLM serving **Qwen3-14B** (BF16) on a **single GPU (GPU1)**.
  Key flags in `scripts/start_vllm.sh`: `--max-model-len 32768` (32K context),
  `--gpu-memory-utilization 0.75`, `--reasoning-parser qwen3`,
  `--tool-call-parser hermes`, `--port 8765`. Launched in tmux; NOT kept always-on.
  (No tensor-parallelism — it runs on one card.)
- Endpoint: OpenAI-compatible at `http://localhost:8765/v1` (port may change; always read `.env`).
  `.env` keys: `VLLM_BASE_URL`, `VLLM_MODEL_NAME` (`Qwen/Qwen3-14B`).
- Client: OpenAI Python SDK
- Dependencies allowed without asking: `openai`, `httpx`, `python-dotenv`. Anything else → ask first.

## What's built (current state — verify against source before relying on it)

- **Tools** live in `src/tools.py`: **10 tools** exposed via the `TOOLS` dict and
  `TOOL_SCHEMAS` (OpenAI function-calling format), in four groups:
  - File I/O: `read_file`, `write_file`, `apply_patch`, `multi_edit`
  - Discovery: `list_dir`, `glob_files`, `grep_files`
  - Execution: `run_bash`, `run_python`
  - Delegation: `spawn_subagent` (passes its workspace down to the child)
  Every file path is routed through `_safe_path(path, workspace)` — the
  **sandbox**. The workspace is an **explicit parameter** (`run_agent(goal,
  workspace, ...)`, `execute_tool(name, args, workspace)`); there is no global
  `WORKSPACE` and no `set_workspace` anymore. This is load-bearing safety, not
  decoration; never weaken or bypass it.
- **Library vs. entry points.** `src/` is the importable library (importing
  `src.agent` is side-effect-free — the client is created lazily by
  `get_client()`). You RUN the agent from `cli/`:
  - `cli/chat.py` — interactive streaming REPL with **context compaction** and
    slash commands (`python cli/chat.py`)
  - `cli/solve.py` — one-shot task runner (also `python -m src.agent "task" --workspace dir`)
  `examples/` is now a **teaching ladder** (read to learn, not the runtime):
  `01_chat.py` → `02_one_tool.py` → `03_react_loop.py` → `04_sandbox_safety.py`.
  `tests/` holds pytest unit tests (sandbox, tools, dispatcher).
- **Context compaction** (in `cli/chat.py`): auto-summarizes history at
  `COMPACT_THRESHOLD_TOKENS = 24000` (~75% of the 32K window), keeping the last
  `KEEP_RECENT_MESSAGES = 10` verbatim. Helpers: `estimate_tokens()`,
  `compact_messages()`. Slash commands include `/compact` (summarize now) and
  `/tokens` (show current estimate).
- **Benchmark** in `eval/`: `python eval/run.py` runs the agent over **627 tasks**
  (163 HumanEval+, 424 sanitized MBPP, 37 curated hard tasks, 3 legacy demos) and
  scores each by an independent `pytest` the agent never controls. Parallel
  (`--jobs N`), with honest hidden-test scoring, a `no_action` guardrail, and a
  validation gate (`eval/validate_tasks.py`). See `eval/README.md`.

## Project-specific rules (extend `~/AGENTS.md`)

### Rule A — Verify before recommending or implementing

Trigger: any time you are about to write, recommend, or rely on something that meets ANY of these criteria:

1. **External / third-party**: it's defined by an outside project (vLLM, OpenAI SDK, HuggingFace, PyTorch, Qwen, CUDA, uv, Docker, etc.) — not the Python standard library and not code we wrote in this repo.
2. **Versioned**: the correct answer depends on which version is installed (a flag, parameter, API field, behavior, deprecation, etc.).
3. **Time-sensitive**: it could have changed after Claude's training cutoff — model tags on HuggingFace, package versions on PyPI, recommended practices in fast-moving areas (LLM inference, agent design, etc.).
4. **Owner uncertainty**: the owner has expressed they don't know how this thing works, even if it's old/stable (e.g. "I've used Node.js but don't understand the event loop"). In this case, Rule B (cache docs) applies so the owner can review later.

If a task touches any of the above → web-search official sources first. Skip the search only when ALL of these are true:
- It's pure Python standard library or basic language syntax
- It's logic we wrote in this repo (read the file, don't search)
- The owner has not flagged it as something they're learning

Source priority:
1. Official documentation (e.g. docs.vllm.ai, platform.openai.com, huggingface.co model card)
2. Official GitHub repo (README, releases, maintainer-marked issues)
3. Peer-reviewed paper or arxiv preprint
4. Reputable blog post less than 6 months old, marked as such

If you cannot verify within ~2 minutes of search, say so explicitly. Do NOT proceed on training-data memory. LLMs are trained to a fixed date; technology evolves; hallucinated versions and flags waste hours of debugging.

### Rule B — Cache official docs locally (RAG-style reference)

Trigger: same as Rule A. Any time Rule A's web search produced useful official material, cache it.

Specifically, cache when:
- The search returned official docs or release notes that the project will reference more than once
- The owner asked to learn this technology (Rule A criterion 4) — cache for their study even if Claude only needs it once
- The information is liable to drift (versioned APIs, flags, model tags)

Steps:
1. Save the relevant section(s) into `docs/reference/<technology>/`. Format: markdown or plain text. Filename hints at content (e.g. `vllm-serving-flags.md`, `openai-tool-use-schema.md`).
2. Append one line to `docs/reference/INDEX.md`:
   `<technology>: <official URL>, downloaded YYYY-MM-DD, covers <topic>`
3. When implementing or modifying anything that touches that technology, read the cached doc first. If the cache is older than 30 days, verify against the live source.

Do NOT cache:
- Python stdlib documentation (use `python -m pydoc` or read source)
- Things the owner already knows well and didn't ask to study
- One-off blog posts (cite in commit message instead)

### Rule C — Verbose by default for the agent runtime

The coding agent built in this project must log each step it takes — tool invocations, tool results, model reasoning when available. The owner needs to observe behavior to learn from it. Silent execution defeats the project's purpose. Verbosity overrides any "production polish" impulse, unless the owner explicitly asks to quiet it.

## Coding conventions (non-negotiable)

- **Simple, minimal, readable.** The owner must be able to explain every line.
  No clever abstractions, no frameworks, no premature generality. Prefer plain
  functions over classes when a function does the job.
- **Dense Vietnamese comments.** Source files are commented in Vietnamese,
  explaining the *why* and the mechanics — written so the owner can study and
  re-explain the code later. Match the existing comment style (see `src/tools.py`,
  `cli/chat.py`). Keep comments dense but accurate; do not let them drift
  from the code.
- **Do NOT add new `src/*.py` files casually.** The source surface is small and
  deliberate. Adding a module is a structural decision — ask the owner first.
  Extend an existing file when reasonable.
- **The sandbox (`_safe_path` in `src/tools.py`) is critical.** Every file
  operation must go through it. Never bypass, relax, or route around it.
- **Never commit Claude attribution.** Do NOT write "Co-Authored-By: Claude" or
  "Generated with Claude Code" (or any equivalent) in commits or PRs.

## Stay-in-scope reminders

- Do NOT touch `~/code/lv2-agent`, `~/code/open_deep_research`, `~/code/fine-tune-research`.
- Do NOT modify the system Ollama service or other users' processes on this shared server.
- Prefer GPU1 (typically idle) for new work; use `CUDA_VISIBLE_DEVICES`.
- Disk is at 73% — be mindful of downloads.

## Demo target

A working coding agent that:
1. Accepts a natural-language task
2. Uses tools (read/write file, run bash) to operate on `demo_repo/`
3. Loops until the task is done or the agent explicitly declares it cannot proceed
4. Logs every step verbosely to stdout
5. The owner can explain every line of source code

Reference test scenario: agent fixes a failing test in `demo_repo/` end to end.
