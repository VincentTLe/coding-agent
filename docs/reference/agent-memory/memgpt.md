# MemGPT — OS-Inspired Hierarchical Memory

Source: Packer et al., "MemGPT: Towards LLMs as Operating Systems," arXiv:2310.08560 (Oct 2023; revised 2024). https://arxiv.org/abs/2310.08560

## Core idea

Treat the LLM context window like RAM and an external store like disk. The agent itself issues function calls to **page** information between tiers. This is "virtual context management" — an analogue of OS virtual memory paging.

## Tiers

- **Main context** (in-window, like RAM):
  - **System instructions** — fixed.
  - **Core memory** — small editable working block; persona + user facts the agent always wants to see. Updated by `core_memory_append`, `core_memory_replace`.
  - **FIFO message buffer** — recent dialog turns; oldest evicted on overflow.
- **External context** (out-of-window, like disk):
  - **Recall memory** — full message history; queried by `conversation_search`.
  - **Archival memory** — long-term semantic store (vector DB); read/write via `archival_memory_insert`, `archival_memory_search`.

## Control flow

LLM emits structured tool calls; a runtime executes them and "interrupts" the model with results (OS-style). On context pressure, the agent calls a self-summarization tool to recursively compress the FIFO buffer, preserving deltas it cares about.

## Evaluation

- **Document QA** beyond native context length (multi-document needle-in-haystack).
- **Multi-session chat** — long-running personas with cross-session recall.

## Status (2026)

MemGPT became the **Letta** project in late 2024; the original repo is archived. The pattern (core/recall/archival + self-managed paging) is the canonical baseline every later system (Zep, Mem0, LangMem, Letta) compares against.

## Why it matters for a coding agent

- Gives a clean mental model for what to keep "always on" (core memory = project conventions, current task goal) vs. what to retrieve on demand (archival = past sessions, file digests).
- Self-issued tool calls keep the agent in control of its own context — no hidden middleware mutating prompts.
- The FIFO + summarize-on-overflow pattern is what Claude Code's `/compact` is doing in spirit.
