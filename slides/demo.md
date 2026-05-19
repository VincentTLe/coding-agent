# Coding Agent — Checkpoint Demo

Student: Tan Le | Advisor: Prof. Andrew Leahy | Math/Stat 361 Research
Date: 2026-05-20 | Final demo: 2026-05-29

---

## Slide 1 — Title + motivation

**From-scratch coding agent**

- Course: Math/Stat 361 Research, Knox College
- Advisor: Prof. Andrew Leahy
- Final demo: May 29, 2026 — today is a checkpoint
- Motivation (addressing the May 5 feedback): build ONE skill end-to-end with
  deep understanding, instead of an AI-assembled app the author cannot
  explain. Every line of this codebase is mine to defend.

---

## Slide 2 — Architecture

```
            [User goal: "Fix the failing test"]
                         |
                         v
                ┌────────────────────┐
                │   Agent loop       │   src/agent.py
                │   (ReAct)          │   ~150 lines
                └────────────────────┘
                     |          ^
                     v          | tool result
            ┌────────────┐  ┌────────────┐
            │  vLLM      │  │  tools.py  │
            │  Qwen3-14B │  │  read_file │
            │  BF16 / 1× │  │  write_file│
            │  A6000     │  │  run_bash  │
            └────────────┘  └────────────┘
```

- Model decides which tool to call via JSON schemas (`TOOL_SCHEMAS`).
- Agent loop appends results, loops until the model stops calling tools.
- Sandbox: tools confined to `demo_repo/` — agent cannot edit its own source.

---

## Slide 3 — What was built (checkpoint files)

- `examples/01_chat.py` — stateless multi-turn chat (concept: messages list as memory)
- `src/tools.py` — `read_file`, `write_file`, `run_bash` + OpenAI tool schemas + sandbox
- `src/prompts.py` — single system prompt (versioned for future fine-tuning)
- `src/agent.py` — the ReAct loop (LLM → tool calls → results → loop)
- `examples/05_agent_loop.py` — CLI wrapper for the demo
- `demo_repo/calculator.py` + `test_calculator.py` — a tiny Python project with a
  deliberate bug for the agent to find and fix
- `scripts/start_vllm.sh` — reproducible vLLM launch for Qwen3-14B
- `docs/research/` — 5K+ lines of pre-research, all sources cached locally

GitHub: github.com/VincentTLe/coding-agent (public)

---

## Slide 4 — Live demo

Command:

```
$ python examples/05_agent_loop.py "Fix the failing test in demo_repo/"
```

Expected trace (what the prof will see in the terminal):

```
=== Turn 1 ===
[tool] run_bash({"command":"ls"})         -> calculator.py, test_calculator.py
=== Turn 2 ===
[tool] run_bash({"command":"pytest -x"})  -> FAIL: add(2,3) == -1, expected 5
=== Turn 3 ===
[tool] read_file({"path":"calculator.py"}) -> sees `return a - b`
=== Turn 4 ===
[tool] write_file({"path":"calculator.py", "content":"...return a + b..."})
=== Turn 5 ===
[tool] run_bash({"command":"pytest"})     -> 3 passed
=== Turn 6 ===
[assistant] Bug fixed; all tests pass.
Agent finished.
```

What this proves: autonomous loop, real file edits, verifiable result.

---

## Slide 5 — Key design choices

- **Open-weight LLM (Qwen3-14B via vLLM)** — runs on the lab's RTX A6000;
  no API spend, no vendor lock-in, reproducible by anyone with the same
  hardware.
- **OpenAI-compatible API + `base_url` swap** — same client code can target
  vLLM, Ollama, GPT-4o cloud, or Claude (via proxy). Swap one `.env` line.
- **JSON-schema tool definitions** — the model picks tools by structured
  schema, not by parsing freeform text. Same mechanism Claude Code uses.
- **ReAct loop in 1 function (`run_agent`)** — think → act → observe →
  repeat. Terminates when the model returns no tool_calls.
- **Sandboxed tools** — `set_workspace(path)` constrains read/write/bash to
  one directory. Agent cannot touch `/etc`, home, or its own source.
- **Verbose logging (Rule C in AGENTS.md)** — every tool call printed; the
  trace is both auditable now and the seed dataset for Phase 3 fine-tuning.

---

## Slide 6 — Roadmap

- **Now → May 29 (Phase 1)** — harden the basic agent, build an eval set of
  10–15 hand-crafted bug-fix tasks, rehearse final demo.
- **June (Phase 2)** — Reflexion loop (agent writes a critique on failure,
  retries with the critique prepended) + persistent `MEMORY.md`. Literature
  precedent: +10–15% pass rate.
  - Refs: Reflexion (arXiv 2303.11366); AlphaCodium (arXiv 2401.08500).
- **July–August (Phase 3)** — LoRA fine-tuning on collected agent traces via
  Unsloth + Qwen3-14B. DPO on (pass, fail) pairs. Realistic gain: 1–3% per
  cycle. Hardware: 1× A6000 fits comfortably (QLoRA, rank 16).
  - Ref: TT-SI (arXiv 2510.07841).
- **August+ (Phase 4, exploratory)** — agent generates new tools for itself
  (ToolMaker-style), edits its own system prompt with a separate evaluator
  agent (SSI-FM-style). 5–6 month research-grade work; open question for
  senior thesis.

Open-weight model + unlimited lab GPU = sustainable platform for long-term
agent research, no recurring API cost.
