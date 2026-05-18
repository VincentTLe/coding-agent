# C4 — Long-Context Evaluations in 2026

## TL;DR
Vanilla **NIAH is saturated** at 200K and no longer informative. The real
2026 bars are **RULER** (synthetic, 13 tasks, effective-length curve),
**LongBench v2** (hard MCQ reasoning, 8K–2M), and **InfiniteBench** (>100K
avg). Qwen has not published RULER/LongBench v2 numbers for 3.6-27B;
extrapolating from Qwen3-32B and independent evals, the model is
**competitive ≤128K, retrieval-only at 200K, scan-only at 1M**.
**Cap our coding agent's prompt at 128K.**

## Why this matters
The agent has 262K native context (Qwen 3.6-27B / vLLM). Knowing the real
quality cliff sets the prompt budget and decides between "big context" and
aggressive RAG.

## State of the art (May 2026)
- **HELM Long Context** (Stanford CRFM, Sep 2025): GPT-4.1 tops a composite
  of RULER SQuAD + HotpotQA, ∞Bench En.MC + En.Sum, OpenAI MRCR (mean 0.588,
  10 models, 300K–10M). [1]
- **RULER**: Qwen3-235B 90.6 / Qwen3-32B 85.6 @ 128K; Nemotron 3 Super
  120B-A12B tops llm-stats RULER at 0.917. [2][3]
- **LongBench v2**: Gemini 2.5 Pro 63.3, Qwen3-235B-Thinking-2507 60.6,
  human 53.7. Qwen3.5-397B-A17B 0.632 on the llm-stats leaderboard. [4][5]
- **NIAH**: saturated for every frontier model. Single-needle overstates
  production capability by 15–40 points vs multi-needle. [6]
- **MRCR v2 (8-needle, 1M)**: Claude Opus 4.6 76%, Gemini 3 Pro 26.3% —
  Anthropic clearly leads multi-needle reasoning at depth. [7]

## Most-used benchmarks

| Benchmark | What it tests |
|-----------|---------------|
| **RULER** | 13 synthetic tasks: multi-key/value/query NIAH, variable tracking, common/frequent words aggregation, distractor QA. Configurable to 1M. The standard quality-vs-length curve. |
| **NIAH** (vanilla) | Single needle at varying depth. Smoke test only. |
| **LongBench v2** | 503 hard MCQ, 8K–2M, 6 domains incl. code repo + structured data. The hardest realistic reasoning bar. |
| **InfiniteBench** | 12 tasks > 100K avg: novels, code, math, KV retrieval, dialog. EN/ZH. [11] |
| **LooGLE / LooGLE v2** | Real-world long-dep QA; v2 (Oct 2025) is 1,934 QA across law/finance/game/code, 16K–2M; best model 59.2%. [12] |
| **ZeroSCROLLS** | 10 zero-shot tasks incl. aggregation (BookSumSort, SpaceDigest). Older but still the zero-shot bar. [13] |

## Qwen 3.6-27B — what we know
Alibaba has not posted RULER/LongBench v2/NIAH numbers for the 27B-dense
3.6 release. Nearest-neighbor data:

| Length | RULER (Qwen3-32B proxy) | Expected for 3.6-27B |
|--------|--------------------------|----------------------|
| 32K   | 94.4 | strong, reliable |
| 64K   | 91.8 | strong |
| 128K  | 85.6 — right at "effective" floor | reasoning starts to fray |
| 200K  | not on table | retrieval OK, multi-hop unreliable [UNVERIFIED] |
| 256K  | not on table | Alibaba ran SWE-Bench at 200K and Terminal-Bench 2.0 at 256K [8] |
| 1M (YaRN factor 4) | n/a | scan-only; vLLM recipe warns short-ctx quality drops |

Independent eval places **Qwen 3 Max effective context at 64K–128K** [9].
ICLR 2025 flags the Qwen3 family: "competitive ≤128K, sharp degradation
beyond 256K despite dual chunk attention and attention temperature
scaling" [10].

## Comparison and verdict
- Usable at 200K? For *retrieval/scan* yes; for *multi-step reasoning over
  the full window* no. Quality drops past 128K; YaRN adds short-context
  regressions.
- **Practical cutoff for prompt budget**: **128K hard cap**, with a
  stretch to 200K for read-only one-shot tasks (whole-repo grep+answer).

## Recommendation
Adopt **RULER + LongBench v2 at 128K** as official quality bars.
- RULER 13-task at 32K/64K/128K → effective-length diagnostic.
- LongBench v2 (with CoT) → reasoning at depth.
- Track InfiniteBench En.MC + Retrieve.KV as smoke tests.
- Drop vanilla NIAH (replace with Sequential-NIAH or NoLiMa).
- Pin agent prompt budget so total context ≤128K in steady state.

## Next steps
1. Run Qwen 3.6-27B FP8 on RULER 32K/64K/128K against NVIDIA/RULER harness.
2. Run LongBench v2 (code repo + structured data subset) at 128K.
3. Measure KV-cache pressure at 128K vs 200K on 2× A6000, TP=2, FP8.
4. Add `MAX_CONTEXT_TOKENS=128000` config flag + log trims.

## Open questions
- Will Alibaba publish real RULER/LongBench v2 for 3.6-27B? The blog
  claims "no degradation at 256K" with no evidence. [UNVERIFIED]
- Does MRCR v2 (Anthropic-aligned) replace RULER as the 2026 de-facto bar?
- Should we use NoLiMa instead of RULER NIAH given the literal-match critique?

## Sources
1. HELM Long Context — https://crfm.stanford.edu/2025/09/29/helm-long-context.html
2. NVIDIA/RULER — https://github.com/NVIDIA/RULER
3. llm-stats RULER — https://llm-stats.com/benchmarks/ruler
4. LongBench v2 — https://longbench2.github.io/
5. llm-stats LongBench v2 — https://llm-stats.com/benchmarks/longbench-v2
6. Digital Applied, NIAH 2026 — https://www.digitalapplied.com/blog/long-context-retrieval-needle-in-haystack-2026
7. Awesome Agents long-context leaderboard — https://awesomeagents.ai/leaderboards/long-context-benchmarks-leaderboard/
8. Qwen3.6-27B model card — https://huggingface.co/Qwen/Qwen3.6-27B
9. nrehiew, long-context blog — https://nrehiew.github.io/blog/long_context/
10. ICLR 2025, "Bridging the Gap to Proprietary LLMs in Long Context" — https://proceedings.iclr.cc/paper_files/paper/2025/file/a7b562dac391e9c7af691e8ef886ad10-Paper-Conference.pdf
11. InfiniteBench, arXiv 2402.13718 — https://arxiv.org/abs/2402.13718
12. LooGLE v2, arXiv 2510.22548 — https://arxiv.org/abs/2510.22548
13. ZeroSCROLLS, arXiv 2305.14196 — https://arxiv.org/abs/2305.14196
14. vLLM Qwen3.5/3.6 recipe — https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3.5.html
