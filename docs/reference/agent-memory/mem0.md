# Mem0 — Universal Memory Layer

Sources:
- https://github.com/mem0ai/mem0 (Apache 2.0)
- https://mem0.ai/blog/state-of-ai-agent-memory-2026
- https://mem0.ai/blog/ai-memory-benchmarks-in-2026
- "Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory," arXiv:2504.19413

## Positioning

A middleware library you drop **between** your app and the LLM. Every model call passes through Mem0; it extracts facts from the turn, writes them to a memory store, and (on retrieval) injects only the most relevant facts back into the prompt. Not an agent framework — a memory layer.

## Architecture

- **Three memory types** (production taxonomy Mem0 promotes):
  - **Episodic** — what happened (turns).
  - **Semantic** — what is known (facts, preferences).
  - **Procedural** — how things are done (workflows, conventions).
- **Multi-scope IDs** — every memory tagged with `user_id`, `agent_id`, `run_id`/`session_id`, `app_id`/`org_id`. Retrieval merges across scopes.
- **Multi-signal retrieval (2026)** — semantic embedding + BM25 keyword + entity-link scoring, fused, plus temporal-aware reranking.
- **Single-pass ADD-only** — memories accumulate; no destructive overwrites. Resolution at read time via temporal validity.

## Backends

- 20+ vector stores (Qdrant, Pinecone, Weaviate, PGVector, Neptune Analytics, Redis, ...).
- 21+ framework integrations (LangChain, LangGraph, CrewAI, OpenAI Agents SDK, Mastra).
- Default config: GPT-5-mini for extraction, `text-embedding-3-small`, Qdrant.

## Benchmarks (per Mem0 blog, Apr 2026)

- **LoCoMo**: 91.6 (their leading config).
- **LongMemEval**: 93.4–94.8 depending on variant.
- ~6,900 tokens/query vs ~26,000 for full-context baselines.

## When to pick it for a coding agent

Good fit when you want vector recall across sessions without writing your own embed/store/retrieve stack. Bad fit if you want the agent itself to *own* its memory operations (MemGPT/Letta style) — Mem0 hides them in middleware.
