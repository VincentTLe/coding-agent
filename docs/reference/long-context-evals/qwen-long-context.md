# Qwen 3.6-27B — Long Context Notes

## Stated capability (huggingface.co/Qwen/Qwen3.6-27B)
- **Native context**: 262,144 tokens (256K).
- **Extensible**: up to 1,010,000 tokens via static YaRN.
- **Recommended minimum**: keep context at ≥128K to preserve thinking.

## YaRN config (from official model card)
```json
{
  "rope_type": "yarn",
  "factor": 4.0,
  "original_max_position_embeddings": 262144,
  "rope_theta": 10000000,
  "mrope_interleaved": true,
  "mrope_section": [11, 11, 10],
  "partial_rotary_factor": 0.25
}
```
- factor 2.0 → ~524K
- factor 4.0 → ~1.0M (vLLM recipe warns short-context quality drops)

## What we actually know about quality

Qwen has **not published** RULER / LongBench v2 / NIAH numbers for 3.6-27B
specifically as of 2026-05-18. We have to infer from neighbors:

- **Qwen3-32B on RULER**: 94.4 @ 32K, 91.8 @ 64K, 85.6 @ 128K (sharp drop
  to the "effective" threshold at 128K). [UNVERIFIED carry-forward]
- **Qwen3-32B on LongBench v2**: 49.2 (vs. 53.7 human, 60.6 for Qwen3-235B-Thinking).
- **Qwen 3 Max effective context (independent eval)**: 64K–128K — same band
  as Claude Sonnet 4 (nrehiew.github.io/blog/long_context).
- **HF blog / "Bridging the gap to proprietary LLMs in long context"
  (ICLR 2025)** flags Qwen3 family as "competitive ≤128K, sharp degradation
  beyond 256K despite dual chunk attention and attention temperature scaling".

## Likely Qwen 3.6-27B profile [UNVERIFIED extrapolation]
- 32K → 94+ on RULER (matches 3-32B floor).
- 64K → 90+ on RULER.
- 128K → ~85 on RULER, ~50 on LongBench v2.
- 200K → noticeable retrieval and reasoning decay; quality "usable for
  retrieval, unreliable for multi-hop reasoning".
- 256K (native ceiling) → quality degraded; OK for needle-style lookup,
  weak for synthesis. Qwen 3.6 line was tested by Alibaba at 200K for
  SWE-Bench and 256K for Terminal-Bench 2.0 (qwen.ai/blog), so the team
  uses 200–256K as the working ceiling for agent workloads.
- 1M (YaRN factor 4) → not for production reasoning; OK for "scan and find".

## Hardware fit on 2× A6000 (96 GB total)
- BF16 + 256K context typically needs more than 96 GB KV-cache at full
  batch; expect to cap **max-model-len ≈ 200K** with FP8 weights and
  batched serving on dual A6000.
- vLLM recipe recommends FP8 for single 40-GB GPUs at 262K; on 2× A6000,
  FP8 + tensor parallel 2 should run 200K comfortably.
- Avoid YaRN factor > 2.0 in production: short-context regressions are
  documented in vLLM recipes and HF model card.

## Practical cutoff for our agent prompt budget
**Recommend hard cap at 128K tokens** for the coding agent prompt
(system + tools + history + retrieved files):
- Stays below RULER "effective" floor for 3-class peer (85.6 @ 128K).
- Leaves headroom under the 200K KV-cache ceiling on 2× A6000 FP8.
- Anything beyond 128K should be retrieval-augmented chunks, not raw dump.

**Stretch ceiling**: 200K for one-shot read-only tasks (whole-repo grep
summary). Treat reasoning quality past 128K as best-effort.
