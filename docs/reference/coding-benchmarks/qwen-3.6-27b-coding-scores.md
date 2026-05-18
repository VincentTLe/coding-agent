# Qwen3.6-27B reported coding benchmark scores — cache May 2026

Sources:
- Qwen blog: https://qwen.ai/blog?id=qwen3.6-27b
- HF model card: https://huggingface.co/Qwen/Qwen3.6-27B
- Aggregator: https://benchlm.ai/coding
- Third-party review: https://www.buildfastwithai.com/blogs/qwen3-6-27b-review-2026
- Aggregator: https://llm-stats.com/models/qwen3.6-plus

## Self-reported by Qwen (blog)

| Benchmark | Qwen3.6-27B | vs prev-gen Qwen3.5-397B-A17B |
|---|---|---|
| SWE-bench Verified | 77.2 | 76.2 |
| SWE-bench Pro | 53.5 | 50.9 |
| Terminal-Bench 2.0 | 59.3 | 52.5 |
| SkillsBench | 48.2 | 30.0 |
| GPQA Diamond | 87.8 | (general reasoning) |

## NOT self-reported

- HumanEval / HumanEval+ — not in blog.
- MBPP / MBPP+ — not in blog.
- LiveCodeBench (any version) — not in blog for the 27B. (Qwen3.6 Plus, the closed-API variant, is reported at 87.1 on v6.)
- BigCodeBench — not in blog.
- MultiPL-E — not in blog.

[UNVERIFIED] buildfastwithai (Apr 23, 2026): "independent third-party verification outside Qwen's scaffolding are limited."

## Implications for our project

- Qwen has clearly bet on agentic-coding benches (SWE / Terminal / Skills) and abandoned the HumanEval/MBPP/LiveCodeBench family in their own reporting.
- We have no official LiveCodeBench / BigCodeBench number for our exact model to compare against. We'll need to run our own to establish a baseline.
- For our smoke-test purposes this is FINE — we use these benchmarks to verify pipeline correctness, not to compete on leaderboards.
