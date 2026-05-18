# C2 — SWE-Bench leaderboards, May 2026

## TL;DR

SOTA Verified: Claude Mythos Preview 93.9%; Opus 4.7 87.6%. Top open-weight: DeepSeek V4 Pro Max 80.6%, Kimi K2.6 80.2%. **Qwen 3.6-27B = 77.2% Verified** self-reported (#18 of 46, #8 open-weight). Top open-source agent: OpenHands + CodeAct v3 = 68.4%. Open-weight × open-agent ceiling: OpenHands + Qwen3-Coder-Next = 71.3%; mini-SWE-agent + Qwen3-Coder-Next = 71.1%.

## Why this matters

From-scratch agent, Qwen 3.6-27B on 2× A6000 via vLLM. Reference: open-weight × open-agent quadrant, bash+file-edit scaffolds land 70-77% Verified. Headline 80-90% numbers use closed models — out of reach.

## SOTA & most-cited

Canonical: **swebench.com** (Princeton), Epoch AI, vals.ai. Aggregators (self-reported): benchlm.ai, llm-stats.com, pricepertoken.com. Aggregator vs official disagree ~3 pts (Opus 4.7: 87.6% benchlm / 82.0% vals.ai) — cross-check.

[UNVERIFIED] llm-stats notes OpenAI stopped reporting Verified after contamination audits; they recommend SWE-Bench Pro.

## Top-10 Verified

| # | Entry | Score | Weights |
|---|---|---|---|
| 1 | Claude Mythos Preview | 93.9% | Closed |
| 2 | Claude Opus 4.7 | 87.6% | Closed |
| 3 | GPT-5.3 Codex | 85.0% | Closed |
| 4 | Claude Opus 4.5 | 80.9% | Closed |
| 5 | Claude Opus 4.6 | 80.8% | Closed |
| 6 | **DeepSeek V4 Pro Max** | 80.6% | **Open** |
| 7 | **Kimi K2.6** | 80.2% | **Open** |
| 8 | GPT-5.2 | 80.0% | Closed |
| 9 | Claude Sonnet 4.6 | 79.6% | Closed |
| 10 | **DeepSeek V4 Pro High** | 79.4% | **Open** |
| 18 | **Qwen 3.6-27B** | **77.2%** | **Open** |

Top agent+model: Augment SWE-Agent + Opus 4.6 = 72.0% (closed agent); OpenHands + CodeAct v3 = 68.4% (open). mini-SWE-agent (Princeton, 100 LOC, bash-only) reports >74%.

**Lite top**: Opus 4.6 62.7%, MiniMax M2.5 56.3%, GLM-5 53.3%, Qwen3-Coder-480B 44.7% (#11). No public Lite score for Qwen 3.6-27B.

## Has Qwen 3.6-27B been submitted?

Self-reported on HF model card: 77.2% Verified, "internal agent scaffold (bash + file-edit), temp=1.0, top_p=0.95, 200K ctx". [UNVERIFIED] swebench.com viewer lists Qwen3-Coder-480B and Qwen2.5-Coder-32B but not Qwen 3.6-27B — no third-party trajectories confirmed.

## Recommendation — demo target

**35-45% on SWE-Bench Lite (≈100-150 / ~300). Stretch 55%.**

Qwen 3.6-27B + a from-scratch bash agent is in mini-SWE-agent-with-open-weights territory. Qwen3-Coder-Next + mini-SWE-agent = 71.1% Verified; our 27B generalist with a bespoke scaffold should land 15-25 pts below Qwen's tuned 77.2%. Lite is ~10-15 pts easier than Verified, so 35-45% Lite ≈ 20-30% Verified-equivalent. Don't quote 77.2% as the demo target — that's Qwen's polished scaffold, not ours.

## Next steps

1. Calibrate on 30-50 Lite tasks first (cheap signal).
2. Add a same-machine mini-SWE-agent + Qwen 3.6-27B baseline (apples-to-apples).
3. Pick tier: Lite (cheap) / Verified (canonical) / Pro (contamination-resistant).

## Open questions

- Reproducible Qwen 3.6-27B trajectories on swebench.com? [UNVERIFIED]
- pass@1 vs pass@k for demo budget?
- Self-reported acceptable or need third-party harness?

## Sources

- https://www.swebench.com/ — official leaderboards
- https://huggingface.co/Qwen/Qwen3.6-27B — Qwen model card
- https://benchlm.ai/benchmarks/sweVerified — Verified aggregator
- https://llm-stats.com/benchmarks/swe-bench-verified — aggregator + contamination note
- https://pricepertoken.com/leaderboards/benchmark/swe-bench-lite — Lite leaderboard
- https://www.vals.ai/benchmarks/swebench — independent re-eval
- https://github.com/SWE-agent/mini-swe-agent — mini-SWE-agent
- https://awesomeagents.ai/leaderboards/swe-bench-coding-agent-leaderboard/ — agent leaderboard
- https://nebius.com/blog/posts/openhands-trajectories-with-qwen3-coder-480b — OpenHands+Qwen
- https://epoch.ai/benchmarks/swe-bench-verified — Epoch tracker
</content>
</invoke>