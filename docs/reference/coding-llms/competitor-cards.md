# Competitor Open-Weight Coding Models 2026 (cached)

Cached: 2026-05-18

## DeepSeek-V3.2
Source: https://huggingface.co/deepseek-ai/DeepSeek-V3.2, arXiv 2512.02556
- **Total / Active Params**: 671B / 37B (MoE)
- **License**: MIT
- **Context Length**: 163,840 tokens
- **Training Corpus**: 14.8T tokens
- **Benchmarks**: SWE-bench Verified 72-74 (range across scaffolds); LiveCodeBench 83.3
- **Fit on 2x A6000 (96GB)**: NO — 671B at any reasonable precision exceeds 96GB. INT4 ~336GB; not feasible.

## DeepSeek-Coder-V3 (the original V3, released 2024)
- Superseded by V3.2 (Dec 2025) and V4 series (2026). "DeepSeek-Coder-V3" as a separate model line does not exist in 2026 — DeepSeek has folded coding into the V3.x/V4.x main releases. The V4-Pro variant is 1.6T MoE with SWE-bench Verified 80.6, also too large for 2x A6000.

## Llama 4 Scout / Maverick
Source: https://ai.meta.com/blog/llama-4-multimodal-intelligence, https://huggingface.co/blog/llama4-release
- **Scout**: 109B total, 17B active, 16 experts, 10M context window
- **Maverick**: ~400B total, 17B active, 128 experts, 1M context
- **License**: Llama 4 Community License (not Apache; EU restrictions; >700M MAU requires special license)
- **Benchmarks**: Scout LiveCodeBench 70.4; SWE-bench Verified 47.3 (Scout). Llama 4 is not a top-tier coding pick in 2026.
- **Fit on 2x A6000 (96GB)**: Scout in BF16 ~218GB; FP8 ~109GB still over budget. INT4 ~55GB fits but quality drops. Maverick does not fit.

## GLM-4.6
Source: https://huggingface.co/zai-org/GLM-4.6
- **Total / Active**: 355B / 32B (MoE)
- **License**: MIT (open-weight)
- **Context Length**: 200K
- **Benchmarks**: SWE-bench Verified 68.0; LiveCodeBench v6 82.8
- **Fit on 2x A6000**: NO at BF16; INT4 marginal. GLM-4.7 (~360B) and GLM-5 (744B) larger still.

## Kimi K2.6 (Moonshot)
Source: https://huggingface.co/moonshotai/Kimi-K2.6, https://www.kimi.com/blog/kimi-k2-6
- **Total Params**: 1T (MoE)
- **License**: Open-weight (modified MIT-like Moonshot license)
- **Context Length**: 256K
- **Benchmarks**: SWE-bench Verified 80.2; SWE-bench Pro 58.6 (ties GPT-5.5); Terminal-Bench 2.0 66.7; AIME 2026 96.4
- **Fit on 2x A6000**: NO. 1T MoE requires hundreds of GB even at FP8.

## Qwen3-Coder-Next (Qwen3-Next-80B-A3B-based)
Source: https://huggingface.co/Qwen/Qwen3-Coder-Next, https://qwen.ai/blog?id=qwen3-coder-next
- **Total / Active**: 80B / 3B (MoE)
- **License**: Apache 2.0
- **Context Length**: 256K
- **Benchmarks**: SWE-bench Verified ~70.6 (3B active); strong CRUXEval, LiveCodeBench v6
- **Fit on 2x A6000**: Yes at FP8 (~80GB) tight; INT8/FP8 with TP=2 works. BF16 ~160GB does not fit. Q8_0 GGUF 80.1GB fits PRO 6000 96GB; on 2x A6000 with TP=2, FP8 fits with headroom.

## MiniMax M2 / M2.5
Source: SWE-Bench Verified leaderboard llm-stats.com
- M2.5: SWE-bench Verified 80.2 (top open-weight tier)
- Likely too large for 2x A6000 (similar scale to Kimi/DeepSeek). Not pursued.

## Gemma 4 26B-A4B MoE (Google)
- 26B total, 4B active. Competes in local-coding seat. Apache-style permissive license. Benchmark scores trail Qwen3.6 family on coding. Detailed comparable scores not surfaced; not a leader for our use case.
