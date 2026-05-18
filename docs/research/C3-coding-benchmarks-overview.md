# C3 — Coding benchmarks overview, May 2026

## TL;DR

**Smoke-test stack: LiveCodeBench (time-windowed slice) + BigCodeBench-Hard, plus HumanEval+ as a 5-minute pipeline sanity check.** HumanEval/MBPP and EvalPlus variants are saturated + contaminated (frontier 95%+; "1-point gap is noise" — morphllm.com 2026). APPS and CodeContests are training data and treated as obsolete-for-eval in 2026 papers. MultiPL-E is fine but not Python-first. EvalPerf is niche. Qwen3.6-27B does NOT self-report any of these — its blog only covers SWE-bench/Terminal-Bench/SkillsBench — so any number is our own baseline.

## Why this matters

From-scratch coding agent on Qwen3.6-27B (vLLM, 2× A6000). C2 covers SWE-bench (slow, agentic). C3 covers lighter code-only benches for fast iteration loops. Wrong bench wastes GPU and misleads.

## SOTA (2026, open-weight focus)

- **HumanEval/+**: saturated. Kimi K2.5 ~99, DeepSeek R1 96.1, Claude Opus 4.6 ~95. Dead signal.
- **LiveCodeBench v6**: DeepSeek V4 Pro Max 93.5, V4 Flash Max 91.6, Kimi K2.6 ~89.6, GLM-4.7 Thinking "best OSS overall." Closed: Gemini 3.1 Pro 88.5, GPT-5.2 Codex 88.0. Qwen3.6 Plus (closed) 87.1. [UNVERIFIED — aggregators diverge.]
- **BigCodeBench-Hard**: 139+ models evaluated; view leaderboard directly.
- **MultiPL-E**: Qwen3-235B-A22B-Instruct-2507 leads at 0.879.
- **EvalPerf / CodeContests / APPS**: niche or contaminated, no current frontier ranking.

## Most-used in 2026

LiveCodeBench dominates 2026 launches (DeepSeek, Kimi, GLM, Gemini, GPT-5.2 all report). BigCodeBench-Hard is second for "realistic library use." HumanEval/MBPP increasingly skipped (Qwen3.6-27B blog skips them). APPS/CodeContests explicitly excluded as eval in 2025-26 papers (AetherCode; arXiv 2511.04355).

## Comparison table

| Benchmark | Tasks | Measures | Contamination | For us |
|---|---|---|---|---|
| HumanEval / + | 164 fns | Docstring → fn | None / same prompts | Sanity ping |
| MBPP / + | 974 short Py | Entry-level | None / same prompts | Skip |
| **LiveCodeBench v6** | 1,055 (or subsets ~175-454) | Competitive prog | Time-window post-cutoff = strong | **Primary** |
| LiveCodeBench Pro | 584 | Harder, no LeetCode | Strongest | Future |
| **BigCodeBench-Hard** | ~150 | Realistic Py + libs | Curated, OK | **Secondary** |
| BigCodeBench-Full | 1,140 | Same, full set | Same | Reference |
| MultiPL-E | HE/MBPP × 18 langs | Cross-lang | Same as source | Skip |
| EvalPerf | 121 | Runtime efficiency | Same source | Skip |
| CodeContests / APPS | ~10-13k | Competitive prog | In training corpora | Skip |

Qwen3.6-27B reports: SWE-bench Verified 77.2, SWE-bench Pro 53.5, Terminal-Bench 2.0 59.3, SkillsBench 48.2. NO official HumanEval/MBPP/LiveCodeBench/BigCodeBench/MultiPL-E.

## Recommendation

1. **Primary: LiveCodeBench v6**, filtered to problems released AFTER Qwen3.6-27B's cutoff. Run ~100-200 problems. Strongest contamination story.
2. **Secondary: BigCodeBench-Hard** (~150 tasks). Realistic Python+libraries — closest to what our agent will do.
3. **Pipeline sanity: HumanEval+ subset** (20-30 problems, <5 min). Confirms vLLM + prompt template + extraction work. Not a quality signal.
4. **Skip**: MBPP/MBPP+ (redundant), MultiPL-E (Python-first), EvalPerf (out of scope), CodeContests/APPS (contaminated).

~250-350 problems, ~1-2 hr on 2× A6000, two complementary axes (competitive prog + library use).

## Next steps

1. Verify Qwen3.6-27B's training cutoff from the HF card to set LiveCodeBench time-window.
2. Set up `evalplus`, LiveCodeBench, and BigCodeBench harnesses in a sandboxed exec env.
3. Run a raw-model baseline before any agent scaffolding for A/B comparison.
4. Capture seeds, vLLM version, sampling params — benches are sensitive to greedy/temperature and chat-template quirks.

## Open questions

- Is there a third-party Qwen3.6-27B LiveCodeBench/BigCodeBench score we missed? (EvalPlus issue #299 Apr 17 2026 for Qwen3.6 35B A3B suggests community runs exist.) [UNVERIFIED]
- Will LiveCodeBench Pro replace v6 as canonical by end of 2026?
- Does our scaffolding interact with HumanEval+ unit-test format (def-only vs full-file)?

## Sources

- EvalPlus: https://evalplus.github.io/leaderboard.html ; https://github.com/evalplus/evalplus
- LiveCodeBench: https://livecodebench.github.io/leaderboard.html ; https://github.com/livecodebench/livecodebench ; Pro https://openreview.net/pdf?id=U5RIVFtat1
- BigCodeBench: https://bigcode-bench.github.io/ ; https://arxiv.org/html/2406.15877v4
- MultiPL-E: https://github.com/nuprl/MultiPL-E
- EvalPerf: https://arxiv.org/abs/2408.06450
- CodeContests+: https://arxiv.org/html/2506.05817v1 ; AetherCode (APPS obsolete): https://arxiv.org/html/2508.16402v1
- 2026 surveys: https://www.morphllm.com/ai-coding-benchmarks-2026 ; https://benchlm.ai/coding
- Qwen3.6-27B: https://qwen.ai/blog?id=qwen3.6-27b ; https://huggingface.co/Qwen/Qwen3.6-27B ; review https://www.buildfastwithai.com/blogs/qwen3-6-27b-review-2026
