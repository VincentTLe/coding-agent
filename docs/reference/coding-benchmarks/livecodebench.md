# LiveCodeBench — cache May 2026

Sources:
- Site: https://livecodebench.github.io/
- Leaderboard: https://livecodebench.github.io/leaderboard.html
- GitHub: https://github.com/livecodebench/livecodebench
- HF blog: https://huggingface.co/blog/leaderboard-livecodebench
- v6 aggregator: https://llm-stats.com/benchmarks/livecodebench-v6
- Pro paper (OpenReview): https://openreview.net/pdf?id=U5RIVFtat1
- Artificial Analysis: https://artificialanalysis.ai/evaluations/livecodebench

## What

Holistic, contamination-free code eval. Continuously harvests problems from LeetCode, AtCoder, Codeforces. Tasks are annotated with release date so you can evaluate on time-windows POST a model's training cutoff. Four scenarios: code generation, self-repair, code execution, test-output prediction. Metric: pass@1.

## Releases / problem counts

- release_v6: problems from May 2023 - Apr 2025, total 1055 problems.
- Common reporting subsets vary widely (131 to ~454 to ~1000) — must pin the version when comparing.
- LiveCodeBench Pro (2025/2026): 584 problems from top-tier contests, drops LeetCode (most contaminated), olympiad-medalist authored.

## Freshness / contamination

Strongest contamination control in the family: filter to problems released AFTER a model's cutoff. Pro version takes it further.

## 2026 leaderboard (LiveCodeBench v6)

Top closed: DeepSeek V4 Pro Max 93.5, V4 Flash Max 91.6, Gemini 3.1 Pro Preview 88.5, GPT-5.2 Codex 88.0. [UNVERIFIED — aggregator scores vary across sources.]

Top open-weight: Kimi K2.6 ~89.6 (Moonshot self-report). GLM-4.7 Thinking cited as "best open-source overall" on LiveCodeBench. Qwen3.6 Plus (closed-API variant) 87.1 on v6.

**Qwen3.6-27B (our model)**: NOT explicitly reported on LiveCodeBench by Qwen as of this writing. [UNVERIFIED] Qwen's blog focuses on agentic benches (SWE/Terminal/Skills).

## Use for our project

Best single benchmark for "raw code competence without contamination." Run on a small time-window slice that post-dates Qwen3.6-27B's cutoff (Mar 2026-ish). ~100-200 problems is enough for a meaningful smoke test in <1 hour on 2× A6000.
