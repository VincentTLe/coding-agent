# B5 - Quantization Landscape for LLM Inference (May 2026)

## TL;DR
Qwen 3.6-27B BF16 fits 2x A6000, so no quantization needed today. When pressure
arrives, the pick on Ampere is **AWQ W4A16 + Marlin**. True FP8 W8A8 needs
Ada/Hopper - off the table for A6000. AutoAWQ is archived; `llm-compressor`
v0.10 (May 2026) is now the canonical calibration tool.

## Why
Audiences see `Qwen/Qwen3.6-27B-FP8` and assume "FP8 = faster everywhere." On
Ampere it does NOT mean native W8A8 - it falls back to FP8 Marlin (W8A16
weight-only dequant). Useful framing for the talk.

## State of the art
Production stack: **calibrate with llm-compressor, serve with vLLM, accelerate
via Marlin (Ampere) or Machete (Hopper).**

- **AWQ W4A16** - activation-aware weight scaling. ~95-99% retention on MMLU.
- **GPTQ W4A16** - Hessian-based. Same target as AWQ, 1-3 pp lower on reasoning.
- **FP8 W8A8** - true 8-bit weight + activation. **Ada/Hopper only.** ~1.6x
  throughput, 2x memory, near-zero accuracy loss.
- **FP8 W8A16 Marlin** - how `Qwen/Qwen3.6-27B-FP8` actually runs on A6000:
  FP8 weights, BF16 GEMM. Memory win only.
- **INT4 W4A16** - vLLM's umbrella 4-bit format; AWQ and GPTQ both feed it.
- **BitsAndBytes NF4** - in-flight 4-bit, no calibration. Slow; deprecation
  proposed (RFC #39583, April 2026).
- **NVFP4 / MXFP4** - Blackwell-native; emulated elsewhere. Not for A6000.

## Most-used
HuggingFace downloads for Qwen 3.6-27B: official FP8 ~5.8M, GGUF >2M, AWQ INT4
~1.5M. In vLLM, AWQ + Marlin is the 4-bit default on Ampere; FP8 W8A8 on Hopper.

## Comparison

| Method | Bits | Acc. drop | Speedup vs BF16 | A6000 | Calib | vLLM |
|---|---|---|---|---|---|---|
| AWQ W4A16 | 4 | ~1-2% [UNVERIFIED on 27B] | ~3x Marlin BS<=32 | yes | ~128 samples | first-class |
| GPTQ W4A16 | 4 | ~2-3% [UNVERIFIED on 27B] | ~3x Marlin | yes | ~512 samples | first-class |
| FP8 W8A8 | 8 | <1% | ~1.6x | NO | none | Hopper/Ada only |
| FP8 W8A16 Marlin | 8w/16a | <1% | memory only | yes | none | first-class |
| INT4 W4A16 | 4 | ~1-3% | ~3x Marlin | yes | ~512 samples | first-class |
| BnB NF4 | 4 | ~3-5% | slow | yes | none | **deprecation proposed** |
| NVFP4 | 4 fp | <2% | Blackwell native | NO native | yes | emerging |

Sources: vLLM docs, llm-compressor README, arXiv 2408.11743, 2026 third-party
benchmarks. Drops on Qwen3.6-27B specifically are [UNVERIFIED].

## Recommendation
**Stay BF16.** Qwen 3.6-27B BF16 (~54 GB) fits 2x A6000 with 32k-context KV
budget. When pressure arrives, use `QuantTrio/Qwen3.6-27B-AWQ` (data-free,
~21 GiB, fits single A6000, Marlin throughput).

## Next steps
1. Smoke-test `QuantTrio/Qwen3.6-27B-AWQ` on one A6000; record tok/s and TTFT.
   Verify in browser, not just curl.
2. Look at quantized KV cache (FP8 KV via llm-compressor 0.9) before further
   weight quantization.
3. Skip BitsAndBytes (deprecation RFC). Skip NVFP4 (no Blackwell).

## Open questions
- Real Qwen3.6-27B AWQ accuracy on SWE-bench Verified / LiveCodeBench - not
  published; needs our own eval.
- Marlin-AWQ throughput at BS=1 (single-user agent), not the BS=16-32 numbers
  Marlin papers report.
- Whether Machete ever backports to Ampere (unlikely; uses Hopper TMA).

## Sources
- https://docs.vllm.ai/en/latest/features/quantization/
- https://docs.vllm.ai/en/latest/features/quantization/fp8/
- https://docs.vllm.ai/en/latest/features/quantization/int4/
- https://docs.vllm.ai/en/stable/features/quantization/bnb/
- https://docs.vllm.ai/en/v0.6.4/quantization/supported_hardware.html
- https://github.com/vllm-project/llm-compressor
- https://github.com/vllm-project/vllm/pull/5975 (FP8 Marlin on Ampere)
- https://github.com/vllm-project/vllm/issues/39583 (BnB/GGUF deprecation RFC)
- https://arxiv.org/abs/2408.11743 (MARLIN paper)
- https://huggingface.co/Qwen/Qwen3.6-27B-FP8
- https://huggingface.co/QuantTrio/Qwen3.6-27B-AWQ
- https://jarvislabs.ai/blog/vllm-quantization-complete-guide-benchmarks
- Cached: docs/reference/quantization/vllm-quantization-support-matrix.md
