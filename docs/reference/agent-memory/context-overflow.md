# Context Window Overflow — How Coding Agents Handle It (2026)

Sources:
- Claude Code `/compact`: https://platform.claude.com/docs/en/build-with-claude/compaction
- "Context Compaction Research: Claude Code, Codex CLI, OpenCode, Amp" — https://gist.github.com/badlogic/cd2ef65b0697c4dbe2d13fbecb0a0a5f
- OpenAI Responses API `/compact`: loss-aware compression returning encrypted compaction item.
- OpenCode: https://deepwiki.com/sst/opencode/2.4-context-management-and-compaction
- Morph, "Compaction vs Summarization": https://www.morphllm.com/compaction-vs-summarization

## Three strategies seen in production

| Strategy | What it does | Wins | Loses |
|---|---|---|---|
| **Verbatim compaction** | Keeps prior user messages literal; replaces assistant/tool turns with encrypted blobs the model can decode. (OpenAI `/responses/compact`.) | Accuracy, inspectability for user side. | Highest token cost; opaque to dev. |
| **LLM summarization** | Calls a model to write a natural-language summary of old turns. (Claude Code `/compact`, OpenCode.) | Best overall quality, human-readable. | Latency hit; can drop details. |
| **Opaque compression** | Encoded/encrypted compressed form. (OpenAI Responses.) | Highest compression ratio. | Black box, vendor-locked. |

No single approach dominates all dimensions (per Morph's comparison).

## Tiered tactics layered on top

1. **Tool-result trimming** — drop or truncate old tool outputs first; cheapest and least lossy because results are usually re-derivable.
2. **Prompt-cache-friendly placement** — keep stable prefix (system prompt, CLAUDE.md) intact so KV cache survives.
3. **Auto-trigger threshold** — Claude Code fires `/compact` at ~95% context (25% remaining). Manual at ~60% gives higher-quality summary because less to compress.
4. **What survives** — project-root CLAUDE.md is **re-read from disk** post-compact. Nested CLAUDE.md reload lazily on next subdir read.
5. **Branch summarization** (Pi-agent) — when the agent navigates away from a sub-task tree, summarize the branch and drop the raw turns.

## Observational memory (Mastra 1.0, 2026)

Two background agents — Observer and Reflector — distill dialog into date-stamped observations written to disk. Achieves 3–6× compression for text agents, 5–40× for tool-heavy ones. Generative-Agents-style reflection applied to coding workflows.

## Practical recommendation for a from-scratch agent

- Start with **summarization-on-overflow** triggered by token-budget watermark.
- Keep an **always-on header** of system prompt + CLAUDE.md-equivalent that survives compaction (re-read each turn).
- Add **tool-result trimming** before reaching for summarization — it's almost free quality.
- Cache the pre-summary turns to disk (audit/debug); the model never reads them again, but you can.
