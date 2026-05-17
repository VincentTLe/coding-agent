# Coding Agent from Scratch

A from-scratch implementation of an AI coding agent on locally-served open-weight models. No agent frameworks.

**Course**: Math/Stat 361 Research (Knox College)
**Advisor**: Prof. Andrew Leahy
**Final demo**: May 29, 2026

## Why from scratch?

Frameworks like LangChain, LangGraph, and CrewAI hide the core mechanics behind abstractions. This project implements every component — tool calling, agent loop, memory, planning — by hand, to demonstrate concrete understanding of how modern coding agents (Claude Code, Codex, Cursor) work under the hood.

## Stack

- Python 3.12, managed via `uv`
- Inference: vLLM serving Qwen 3.6-27B with tensor-parallel-size=2
- Hardware: 2× NVIDIA RTX A6000 (96GB total, NVLink x4)
- Client: OpenAI Python SDK against vLLM's OpenAI-compatible endpoint
- Dependencies: stdlib + `openai` + `httpx` + `python-dotenv` only

## Repo layout

- `src/` — agent core (orchestrator, tool registry, agent loop)
- `examples/` — one concept per file, runnable standalone, in order
- `tests/` — unit tests
- `demo_repo/` — small mock repo the agent operates on during demo
- `scripts/` — shell scripts (vLLM startup, etc.)
- `docs/reference/` — cached official docs (see AGENTS.md Rule B)
- `slides/` — final presentation materials

## Status

🚧 In active development. Owner is learning the stack as the project is built.
