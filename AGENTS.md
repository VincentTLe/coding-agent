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

### Rule A — Verify before recommending (extends §2 of `~/AGENTS.md`)

Before recommending or implementing any of the following, perform a web search of official sources and briefly cite what you found in the response or commit message:

- A library, package, or framework choice
- A specific version of a dependency
- A model tag, repo name, or quantization variant
- A vLLM flag, OpenAI SDK parameter, or API field
- A CUDA / driver / Python version compatibility claim
- An architectural pattern claimed to be "standard" or "best practice"

Priority of sources:
1. Official documentation (e.g. docs.vllm.ai, platform.openai.com, huggingface.co model card)
2. Official GitHub repo (README, releases, maintainer-marked issues)
3. Peer-reviewed paper or arxiv preprint
4. Reputable blog post less than 6 months old, marked as such

If you cannot verify within roughly 2 minutes of search, say so explicitly. Do NOT proceed on training-data memory. LLMs are trained to a fixed date; technology evolves; hallucinated versions and flags waste hours of debugging.

### Rule B — Cache official docs locally (RAG-style reference)

When a non-trivial technology is first used in this project, cache its relevant docs locally:

1. Save the relevant section(s) into `docs/reference/<technology>/`. Format: markdown or plain text. Filename should hint at content (e.g. `vllm-serving-flags.md`).
2. Append one line to `docs/reference/INDEX.md`:
   `<technology>: <official URL>, downloaded YYYY-MM-DD, covers <topic>`
3. When implementing or modifying anything that touches that technology, read the cached doc first. Then verify on the live source if the cache is older than 30 days.

This protects against drift between AI memory and current docs, and gives the owner a portable reference.

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
