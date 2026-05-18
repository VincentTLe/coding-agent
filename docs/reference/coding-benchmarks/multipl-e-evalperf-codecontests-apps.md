# MultiPL-E / EvalPerf / CodeContests / APPS — cache May 2026

## MultiPL-E

Sources:
- GitHub: https://github.com/nuprl/MultiPL-E
- Site: https://nuprl.github.io/MultiPL-E/
- Aggregator: https://llm-stats.com/benchmarks/multipl-e
- IEEE TSE: https://ieeexplore.ieee.org/document/10103177/

What: extends HumanEval and MBPP to ~18 additional programming languages (JS, TS, Java, Rust, Go, PHP, Ruby, C++, etc.) via deterministic translation rules. Same source tasks → same contamination story as HumanEval/MBPP, but tells you cross-language transfer.

2026: Qwen3-235B-A22B-Instruct-2507 leads aggregator at 0.879. Not commonly cited in 2026 top-tier model launches — McEval (massively multilingual) and BigCodeBench instruct have largely supplanted it.

Use: ignore for our Python-first agent unless we add multi-language support.

## EvalPerf

Sources:
- Site: https://evalplus.github.io/evalperf.html
- Paper: https://arxiv.org/abs/2408.06450 (COLM 2024)
- OpenReview: https://openreview.net/forum?id=IBCBMeAhmC

What: efficiency benchmark, not just correctness. 121 stress-tested tasks. Uses Differential Performance Evaluation (DPE) — measures runtime of CORRECT solutions across categories (numerical, data structures, graph, DP, strings). Compound metric anchored in real execution cost.

2026: still active, used in code-optimization research. Niche compared to correctness benches.

Use: skip for v1. Revisit only if the agent ever does perf-critical code (it won't in our scope).

## CodeContests

Sources:
- DeepMind/AlphaCode origin: https://ar5iv.labs.arxiv.org/html/2203.07814
- CodeContests+ paper: https://arxiv.org/html/2506.05817v1
- CodeContests-O: https://github.com/cai-jianfeng/CodeContests-O

What: DeepMind's competitive-programming dataset (Codeforces, etc.) used to train/eval AlphaCode. Newer variants (+, -O) add verified test cases; CodeContests-O (Jan 2026) reports TPR=89.4%/TNR=90.9% — discriminates faulty solutions ~4-9pts better than original.

Status: training set is widely used (so the test set as eval is contamination-risky); LiveCodeBench has effectively replaced it for clean eval.

Use: don't run as eval. If we ever do reasoning RL, it's a candidate as a training source.

## APPS

Sources:
- Original paper (Hendrycks et al. 2021): https://arxiv.org/abs/2105.09938
- "Where Do LLMs Still Struggle?" (Nov 2025): https://arxiv.org/html/2511.04355v1
- AetherCode (Aug 2025): https://arxiv.org/html/2508.16402v1

What: 10,000 problems split 5k train / 5k test, three difficulty levels (Intro / Interview / Competition).

Status: explicitly excluded from recent rigorous eval papers — "widely used for training and would risk contamination" (AetherCode 2025). Considered obsolete as a clean eval signal in 2026.

Use: don't run.
