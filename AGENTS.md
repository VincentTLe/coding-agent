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
- Inference: vLLM serving Qwen 3.6-27B with tensor-parallel-size=2
- Endpoint: OpenAI-compatible at `http://localhost:8765/v1` (port may change; always read `.env`)
- Client: OpenAI Python SDK
- Dependencies allowed without asking: `openai`, `httpx`, `python-dotenv`. Anything else → ask first.

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
