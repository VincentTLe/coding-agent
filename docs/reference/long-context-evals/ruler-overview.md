# RULER — Reference Notes

**Source:** NVIDIA/RULER (https://github.com/NVIDIA/RULER) — arXiv 2404.06654, COLM 2024.

## What RULER tests
Synthetic benchmark, 13 tasks across 4 categories at configurable sequence
lengths (4K → 1M+). Designed to expose quality decay where vanilla NIAH stays
saturated.

- **Retrieval (8)** — NIAH variants (single/multi-key, multi-value, multi-query).
- **Multi-hop tracing (1)** — variable tracking, coref chain resolution proxy.
- **Aggregation (2)** — Common / frequent words extraction.
- **Question answering (2)** — SQuAD- and HotpotQA-based with injected
  distractors.

## "Effective context length"
Longest length where a model stays above the Llama-2-7B-at-4K score of 85.6.
Effective length is typically 50–65% of advertised context.

## Qwen3 RULER scores (from NVIDIA/RULER table)

| Model         | 32K  | 64K  | 128K |
|---------------|------|------|------|
| Qwen3-235B    | 95.1 | 93.3 | 90.6 |
| Qwen3-32B     | 94.4 | 91.8 | 85.6 |
| Qwen3-14B     | 96.1 | 94.0 | 85.1 |
| Qwen3-8B      | 91.2 | 82.1 | 77.4 |
| Qwen3-4B      | 87.8 | 77.8 | 66.0 |

Qwen3.6-27B not yet on the leaderboard (May 2026). Qwen3-32B is the closest
analog: 85.6 at 128K is right at the "effective" threshold.

## RULER-1M and RULER-64K splits
Separate leaderboards at llm-stats.com/benchmarks/ruler-1000k and
ruler-64k. Top: Nemotron 3 Super 120B-A12B (0.917), Phi-3.5-MoE (0.871).
Frontier closed models (GPT-4.1, Claude Opus, Gemini 3) sit at the top of
HELM Long Context (RULER subset).

## Caveat
RULER is synthetic. Strong RULER does not guarantee strong real-world
long-doc reasoning — see LongBench v2, LooGLE v2, NoLiMa for that.
