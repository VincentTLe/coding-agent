# Coding Agent from Scratch

A from-scratch implementation of an AI coding agent on locally-served open-weight models. No agent frameworks.

**Course**: Math/Stat 361 Research (Knox College)
**Advisor**: Prof. Andrew Leahy
**Final demo**: May 29, 2026

## Why from scratch?

Frameworks like LangChain, LangGraph, and CrewAI hide the core mechanics behind abstractions. This project implements every component — tool calling, agent loop, memory, planning — by hand, to demonstrate concrete understanding of how modern coding agents (Claude Code, Codex, Cursor) work under the hood.

## Stack

- Python 3.12, managed via `uv`
- Inference: vLLM 0.21.0 serving Qwen3-14B (single GPU, tensor-parallel-size=1)
- Hardware: 1× NVIDIA RTX A6000 (48GB); second A6000 left free for other lab users
- Client: OpenAI Python SDK against vLLM's OpenAI-compatible endpoint
- Dependencies: stdlib + `openai` + `httpx` + `python-dotenv` (+ `pytest` for tests)

## Quick start

```bash
git clone https://github.com/VincentTLe/coding-agent
cd coding-agent
uv venv && source .venv/bin/activate && uv sync
cp .env.example .env                            # defaults are fine for local vLLM

# In a separate tmux session, start the vLLM server (~1-2 min to boot):
bash scripts/start_vllm.sh

# Once you see "Application startup complete", in your main shell:
python examples/01_chat.py                                          # interactive chat
python examples/05_agent_loop.py "Fix the failing test in demo_repo/"   # full agent
```

## What it does today

The agent runs a ReAct loop (think → call tool → observe → repeat) against
a local Qwen3-14B. It has three tools:

- `read_file(path)` — read a text file inside the workspace
- `write_file(path, content)` — overwrite a file with new content
- `run_bash(command, timeout)` — run a shell command inside the workspace

Workspace is sandboxed by `src.tools.set_workspace(path)`; by default the
agent is pinned to `demo_repo/`. The demo task is to fix a deliberately
broken `add(a, b)` function so the pytest suite passes.

## Repo layout

```
coding-agent/
├── examples/
│   ├── 01_chat.py            # stateless multi-turn chat (concept demo)
│   └── 05_agent_loop.py      # CLI wrapper for the agent
├── src/
│   ├── agent.py              # ReAct loop (the heart of the system)
│   ├── tools.py              # read_file / write_file / run_bash + JSON schemas
│   └── prompts.py            # single system prompt
├── demo_repo/                # tiny Python project with a deliberate bug
├── scripts/start_vllm.sh     # reproducible vLLM launch
├── docs/
│   ├── research/             # 30-topic pre-research (5K+ lines)
│   └── reference/            # cached official docs (AGENTS.md Rule B)
└── slides/demo.md            # checkpoint deck
```

## Roadmap

- **Phase 1 (now → May 29)** — basic agent + eval set + final demo.
- **Phase 2 (Jun)** — Reflexion loop + persistent `MEMORY.md`.
- **Phase 3 (Jul–Aug)** — LoRA fine-tuning on collected agent traces.
- **Phase 4 (Aug+, exploratory)** — agent generates new tools, edits its own
  prompts, moves toward recursive self-improvement.

Full plan: `docs/` (research) and the project plan in `~/.claude/plans/`.

## Status

In active development. Owner is learning the stack while building.
