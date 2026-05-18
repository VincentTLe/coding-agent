# Zep + Graphiti — Temporal Knowledge Graph Memory

Sources:
- Rasmussen et al., "Zep: A Temporal Knowledge Graph Architecture for Agent Memory," arXiv:2501.13956 (Jan 2025). https://arxiv.org/abs/2501.13956
- https://github.com/getzep/graphiti
- https://www.getzep.com/product/open-source/

## Core idea

Memory as a **temporal knowledge graph**, not a vector blob. Every fact is an edge with explicit validity intervals `(t_valid, t_invalid)`. New facts can supersede old ones without deleting history.

## Components

- **Graphiti** — open-source temporal context graph engine (the actual store). Nodes are entities, edges are timestamped relationships/facts.
- **Zep** — hosted/commercial agent-memory service built on Graphiti, plus retrieval APIs.

## Retrieval

Hybrid: semantic embeddings + BM25 keyword + direct graph traversal, scored and fused. **No LLM call on the read path** — that's how Zep claims P95 ~300 ms.

## Conflict handling

On insert, semantic+keyword+graph search checks if the new fact contradicts existing facts. If so, Graphiti **invalidates** the prior fact (sets `t_invalid`) rather than deleting it. The graph thus stores the full history; queries can be time-scoped ("as of date X").

## Benchmarks

- **DMR** (MemGPT's own benchmark): Zep 94.8% vs MemGPT 93.4%.
- **LongMemEval**: up to +18.5 points over baselines, ~90% latency reduction.

## Coding-agent fit

Strong for cross-session facts that **change over time**: "the API key rotated", "we switched from Yarn to pnpm in commit X", "this module owns Y as of last week." Overkill for transient working memory inside a single task.
