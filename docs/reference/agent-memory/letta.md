# Letta — Production Stateful-Agent Platform

Sources:
- https://github.com/letta-ai/letta
- https://docs.letta.com/concepts/letta/
- https://docs.letta.com/guides/core-concepts/stateful-agents/
- https://www.letta.com/blog/our-next-phase

## Lineage

Letta is the renamed/productionized continuation of MemGPT (rebrand ~Sep 2024, by the same UC Berkeley team — Packer, Wooders, Gonzalez). It exposes MemGPT-style agents as services behind REST APIs, with all state persisted in a database (Postgres + a vector store).

## Memory model

Letta organizes memory into **blocks** — editable strings the agent can attach, detach, and rewrite via tools. Concrete tiers (inherited from MemGPT):

- **Core memory** — always in-context blocks (persona, human, task-specific blocks). Agent edits with `core_memory_*` tools.
- **Recall memory** — full chronological message log, kept out of context, searchable.
- **Archival memory** — vector-indexed long-term facts; agent calls `archival_memory_insert` / `archival_memory_search`.

Everything (memory blocks, message history, reasoning traces, tool calls) is persisted, so an agent process can be killed and resumed without losing state. This is the "stateful agent" pitch.

## 2025–2026 additions

- **Letta Code** (Dec 2025) — "memory-first" coding agent; advertised as #1 model-agnostic open source agent on Terminal-Bench.
- **MemFS** — a git-tracked memory backend that stores memory as files on disk (so memory diffs are reviewable and version-controlled).
- **Conversations API** (Jan 2026) — shared memory across parallel agent instances talking to the same user.

## Trade-offs

- Pro: clean abstraction, model-agnostic, mature SDK, you can introspect every memory block.
- Con: heavyweight if you only want a CLI coding agent; assumes a server + DB; tool-call-per-edit overhead.
