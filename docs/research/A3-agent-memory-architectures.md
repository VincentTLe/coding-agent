# A3 — Memory Architectures for Coding Agents (2026)

## TL;DR

For a from-scratch CLI coding agent, the 2026 default is **Claude Code's "markdown on disk"**: always-on `CLAUDE.md`, auto-written `MEMORY.md`, `/compact`-style summarization on overflow. Database-backed systems (Letta, Mem0, Zep) win on retrieval but add server + vector store + per-edit tool-call tax that hurts single-user CLIs. Start with files; add vectors only when measured.

## Why this matters

Long sessions overflow and lose the goal; yesterday's corrections vanish today; build/test commands get re-derived each run. Architecture stratifies into working / episodic / long-term.

## State of the art, 2026

**Working.** FIFO + LLM-summary-on-overflow dominates (Claude Code, OpenCode, Codex CLI); tool results trimmed first. OpenAI's `/responses/compact` does verbatim compaction (user turns literal, assistant turns encrypted). Summary wins quality; opaque wins ratio; verbatim wins accuracy.

**Episodic.** Generative Agents (Park et al., UIST 2023) set the template: append-only memory stream scored by recency + relevance + LLM importance, with periodic reflections written back. For coding: per-task scratchpad (`goal`, `plan`, `findings`, `blockers`) + end-of-task reflections.

**Long-term — three architectures compete:**
- **OS-tiered (MemGPT → Letta):** core + recall + archival; agent issues `core_memory_*` / `archival_memory_*` calls. Letta added MemFS and Letta Code in Dec 2025.
- **Middleware vector (Mem0, Apache-2.0):** fused semantic + BM25 + entity + temporal; 20+ backends; 91.6 LoCoMo, 93.4–94.8 LongMemEval at ~6.9K tokens/query.
- **Temporal KG (Zep/Graphiti):** facts as edges with `(t_valid, t_invalid)`; conflicts invalidate. Hybrid retrieval, no LLM on read, P95 ~300 ms. Beats MemGPT on DMR.

**Coding tools.** Claude Code and Cursor converged on files: `CLAUDE.md` / `.cursor/rules/*.mdc`, path-scoped via frontmatter. Claude Code adds auto-written `MEMORY.md` (v2.1.59+). Both intentionally database-free.

**Benchmarks.** LoCoMo, LongMemEval, BEAM — all conversational. No published benchmark targets coding agents. [UNVERIFIED] one Medium-published coding-memory benchmark is not peer-reviewed.

## Most-used in production

Mem0 (~48–56K stars), Letta, Zep/Graphiti for layers. Claude Code `CLAUDE.md` and Cursor `.cursor/rules/` for coding tools.

## Comparison

| System | Layer | Storage | Retrieval | License | Best fit |
|---|---|---|---|---|---|
| MemGPT / Letta | Long-term tiered | Postgres + vector | Agent tool calls | Apache-2.0 | Server multi-user |
| Mem0 | Long-term middleware | Vector (20+) | Semantic+BM25+entity+temporal | Apache-2.0 | Drop-in cross-session |
| Zep / Graphiti | Long-term graph | Temporal KG | Hybrid no-LLM read | Apache-2.0 / commercial | Time-varying facts |
| Generative Agents | Episodic + reflection | Memory stream | Recency+relevance+importance | Research | Pattern only |
| Claude Code | Working + long-term | Markdown | Path-scoped + always-on | Anthropic | Single-user CLI |
| Cursor rules | Working rules | `.mdc` | Glob-matched | Cursor | Editor-integrated |
| `/compact` | Working overflow | In-process | LLM summary | Anthropic | Long sessions |

## Recommendation

**Claude Code file-based pattern with clean upgrade path to vectors:**

1. **Working** — raw transcript + ~75% token watermark; overflow triggers LLM summary keeping last N turns; re-read `AGENTS.md` post-compact.
2. **Episodic** — structured scratchpad in `.agent/tasks/<id>.md`; end-of-task reflection emits 1–5 promoted facts.
3. **Long-term** — `MEMORY.md` index + on-demand topic files in `.agent/memory/`. Defer vectors until retrieval is the measured bottleneck.
4. **Fact schema** — `{fact, scope, t_valid, source_turn}` so a Graphiti swap is migration, not rewrite.

Month-one problems are tool-calling and prompt assembly, not retrieval. Files give inspectability and zero infra; Mem0/Zep wins only matter at scale.

## Next steps

1. FIFO + summary-on-overflow; re-read `AGENTS.md` post-compact.
2. Task-notebook schema + `note_append` / `note_replace` tools.
3. End-of-task reflection promoting to `MEMORY.md`.
4. Token watermark + manual `/compact`.
5. Replay 10 multi-session tasks; measure goal-retention vs. baseline.

## Open questions

- No coding-specific memory benchmark.
- Reflection quality for code edits vs. narrative undocumented.
- Path-scoped rules vs. on-invoke skills — split unsettled.
- `/compact` survival policy needs explicit design in a custom agent.
- Cross-session identity/consent [UNVERIFIED] cleanly solved by any 2026 system.

## Sources

- [Packer et al., MemGPT, arXiv:2310.08560](https://arxiv.org/abs/2310.08560)
- [Rasmussen et al., Zep, arXiv:2501.13956](https://arxiv.org/abs/2501.13956)
- [Mem0 paper, arXiv:2504.19413](https://arxiv.org/pdf/2504.19413)
- [Park et al., Generative Agents, arXiv:2304.03442](https://ar5iv.labs.arxiv.org/html/2304.03442)
- [Claude Code memory docs](https://code.claude.com/docs/en/memory)
- [Claude Code compaction docs](https://platform.claude.com/docs/en/build-with-claude/compaction)
- [Cursor rules docs](https://cursor.com/docs/rules)
- [Letta — Stateful agents](https://docs.letta.com/guides/core-concepts/stateful-agents/)
- [Mem0 GitHub](https://github.com/mem0ai/mem0)
- [Graphiti GitHub](https://github.com/getzep/graphiti)
- [Mem0, State of AI Agent Memory 2026](https://mem0.ai/blog/state-of-ai-agent-memory-2026)
- [Atlan, Best Memory Frameworks 2026](https://atlan.com/know/best-ai-agent-memory-frameworks-2026/)
- [Morph, Compaction vs Summarization](https://www.morphllm.com/compaction-vs-summarization)
- [Context Compaction Research gist](https://gist.github.com/badlogic/cd2ef65b0697c4dbe2d13fbecb0a0a5f)
- [LoCoMo benchmark](https://snap-research.github.io/locomo/)
