# LongBench v2 — Reference Notes

**Source:** https://longbench2.github.io/ , ACL 2025 Long.
**Repo:** THUDM/LongBench.

## What it tests
503 hard multiple-choice questions, 8K → 2M words, 6 task families:

1. Single-doc QA
2. Multi-doc QA
3. Long in-context learning
4. Long dialog history
5. Code repo understanding
6. Long structured-data understanding

Three length tiers: Short (0–32K), Medium (32K–128K), Long (128K–2M).

## Top scores (with CoT)
- Gemini 2.5 Pro — 63.3%
- Gemini 2.5 Flash — 62.1%
- Qwen3-235B-A22B-Thinking-2507 — 60.6%
- DeepSeek-R1 — 58.3%
- Human experts (15 min) — 53.7%

llm-stats reports Qwen3.5-397B-A17B at 0.632 (leaderboard top, 2026).

## Qwen scores
- Qwen3-235B-A22B-Thinking-2507 — 60.6
- Qwen3-235B-A22B-Instruct-2507 — 58.3
- Qwen3-235B-A22B — 50.1
- Qwen3-32B — 49.2
- Qwen2.5-72B — 43.5

Qwen3.6-27B not yet on the leaderboard.

## Takeaway
The hard end of long-context: reasoning, not just retrieval. Best dense open
model at 27B class would land in the 45–52 range based on Qwen3-32B's 49.2.
