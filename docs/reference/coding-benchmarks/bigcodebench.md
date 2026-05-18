# BigCodeBench — cache May 2026

Sources:
- Site/leaderboard: https://bigcode-bench.github.io/
- GitHub: https://github.com/bigcode-project/bigcodebench
- HF leaderboard: https://huggingface.co/spaces/bigcode/bigcodebench-leaderboard
- HF blog: https://huggingface.co/blog/leaderboard-bigcodebench
- Paper (ICLR'25): https://arxiv.org/html/2406.15877v4

## What

ICLR 2025. 1,140 practical, realistic programming tasks requiring diverse function calls (PyPI libraries) and complex multi-step instructions. Two modes:
- Complete: docstring → function body.
- Instruct: NL instruction → full program.

Subsets:
- Full: 1,140 tasks.
- Hard: ~150 user-facing, harder tasks — the headline number for capability ranking.

Metric: pass@1 greedy, sandboxed unit-test execution.

## Freshness / contamination

Authors curated to avoid mass GitHub-scrape contamination paths. Safer than HumanEval/MBPP, but tasks have been public for >1 year — frontier-model trainers may still have seen them. Better than HumanEval, weaker contamination story than LiveCodeBench's time-window.

## 2026 notes

- 139+ models evaluated on Hard.
- Open-weight markers on leaderboard: green heart = open weights + open data; blue heart = open weights + open SFT data.
- No public Qwen3.6-27B score on BigCodeBench-Hard from official Qwen comms as of May 2026 [UNVERIFIED — not in blog].

## Use for our project

Closest benchmark to "real Python with libraries" — important for an agent that will call pandas, numpy, requests, etc. Hard subset (~150 tasks) is feasible as a smoke run. Use as a quality signal complement to LiveCodeBench (which is competitive-programming-heavy).
