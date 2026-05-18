# HumanEval / HumanEval+ / MBPP / MBPP+ (EvalPlus) — cache May 2026

Sources:
- EvalPlus leaderboard: https://evalplus.github.io/leaderboard.html
- EvalPlus home: https://evalplus.github.io/
- GitHub: https://github.com/evalplus/evalplus
- Aggregator: https://llm-stats.com/benchmarks/humaneval+
- Aggregator: https://llm-stats.com/benchmarks/mbpp-evalplus

## What

- HumanEval (OpenAI, 2021): 164 stand-alone Python function tasks from docstrings; pass@1 with provided unit tests.
- MBPP (Google, 2021): 974 entry-level Python problems with 3 tests each.
- EvalPlus (NeurIPS 2023, COLM 2024) augments both: HumanEval+ adds ~80x more tests, MBPP+ adds ~35x more tests, catching wrong solutions the originals miss. EvalPlus uses HumanEval+ v0.1.10 and MBPP+ v0.2.0 (per leaderboard page).

## Freshness / contamination

- HumanEval is saturated and contaminated: every frontier model 95%+. "1-point gap is noise, not signal" (morphllm.com 2026 review).
- MBPP+ remains slightly more discriminating but is also exposed; both datasets have been in public training corpora for 4+ years.
- EvalPlus does NOT add new problems — only stronger tests. Same prompts, so prompt-level memorization still leaks.

## 2026 open-weight notes

- Kimi K2.5 reported ~99 on HumanEval (saturation).
- Recent active leaderboard submissions visible: Qwen3.6 35B A3B (Local Q4_K_M) submitted April 17, 2026 (issue #299 on evalplus/evalplus).
- Qwen3.6-27B does NOT report HumanEval/MBPP scores in its official blog — Qwen has shifted to SWE-bench/Terminal-Bench/SkillsBench.

## Use for our project

- Smoke-test only: a few HumanEval+ problems make a fast (~5 min on 2× A6000) pass@1 sanity check that vLLM serving + prompt template + extraction work end-to-end.
- Do NOT use as a quality signal vs. SOTA. Treat as "is the pipe alive" not "is the model good."
