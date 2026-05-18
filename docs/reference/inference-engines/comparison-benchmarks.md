# Inference engine comparison: cached benchmark numbers (2026-05-18)

Snapshot of the most-cited 2026 head-to-head benchmarks. **Caveats:**
- All numbers below are H100 / H200 / B200 — not RTX A6000.
- Throughput on A6000 will be ~3–5× slower per GPU (FP8 unavailable, Ampere bandwidth).
- Workload mix matters more than the engine choice in most cases.

## Spheron bench (H100 SXM5 80GB, Llama 3.3 70B FP8, 2026)

200 prompts, 512 in / 256 out, async aiohttp client, 60s warmup + 3min steady-state.

Throughput, output tok/s:

| Concurrency | vLLM | SGLang | TensorRT-LLM |
|---|---|---|---|
| 1 | 120 | 125 | 130 |
| 10 | 650 | 680 | 710 |
| 50 | 1,850 | 1,920 | 2,100 |
| 100 | 2,400 | 2,460 | 2,780 |

p50 TTFT, ms:

| Concurrency | vLLM | SGLang | TRT-LLM |
|---|---|---|---|
| 1 | 45 | 42 | 38 |
| 10 | 120 | 112 | 105 |
| 50 | 380 | 360 | 340 |
| 100 | 740 | 710 | 680 |

p95 TTFT, ms:

| Concurrency | vLLM | SGLang | TRT-LLM |
|---|---|---|---|
| 1 | 68 | 61 | 55 |
| 10 | 195 | 178 | 170 |
| 50 | 720 | 680 | 620 |
| 100 | 1,450 | 1,380 | 1,280 |

Cold-start time:
- vLLM: ~62 s
- SGLang: ~58 s
- TensorRT-LLM: **~28 min** (engine compile)

## Clarifai bench (H100, GPT-OSS-120B FP8, 2026)

Peak throughput at 100 concurrent requests:
- vLLM: 4,741 tok/s
- (SGLang and TRT-LLM numbers not directly comparable in same article)

## LMSYS / 2026 RadixAttention bench (multi-turn / RAG)

Llama-3.1-8B, prefix-heavy workload:
- vLLM: 12,500 tok/s
- SGLang: 16,200 tok/s (+29%)

RAG with shared prefixes:
- SGLang up to 6.4× over no-prefix-cache baseline (original RadixAttention paper number, still echoed in 2026 benches with cleaner methodology).

## Yotta Labs production bench (2026)

70B+ models, mixed workloads:
- SGLang vs vLLM gap narrows to 3–5%.
- TensorRT-LLM 15–30% above vLLM on H100, but only after warmed-up compile.

## Adjustment factors for our 2× A6000 setup

The A6000 lacks:
- FP8 tensor cores → can't use the headline FP8 KV-cache or attention-in-FP8 wins.
- HBM3e bandwidth → ~3.4 TB/s on H100 vs ~768 GB/s per A6000.
- The 5th-gen Transformer Engine (sparse).

What translates well anyway:
- Prefix caching (vLLM + SGLang): pure algorithmic win, no hardware dependency.
- Chunked prefill (vLLM + SGLang): scheduling, hardware-agnostic.
- Speculative decoding (all three): hardware-agnostic.
- RadixAttention (SGLang): hardware-agnostic.

What does NOT translate:
- FP8 attention quantization (vLLM, SGLang, TRT-LLM): Hopper+ only.
- NVFP4 (TRT-LLM): Blackwell only.
- FP4 MoE kernels: Blackwell.

## Quantization support matrix (2026)

| Quant | vLLM | SGLang | TRT-LLM |
|---|---|---|---|
| BF16/FP16 | Yes | Yes | Yes |
| INT8 SmoothQuant | Yes | Yes | Yes |
| INT4 AWQ | Yes (Marlin kernel) | Yes | Yes |
| INT4 GPTQ | Yes (ExLlamaV2 kernel) | Yes | Yes |
| FP8 W8A8 | Yes (Hopper+) | Yes (Hopper+ native; Marlin on Ampere) | Yes (SM89+ only) |
| NVFP4 | Limited | Limited | Yes (Blackwell) |
| KV-cache FP8 | Yes (Hopper+) | Yes (Hopper+) | Yes (Hopper+) |
| KV-cache INT8 | Yes | Yes | Yes |

## Model coverage (Qwen 3.x family)

| Model | vLLM | SGLang | TRT-LLM |
|---|---|---|---|
| Qwen2 | Yes | Yes | Yes |
| Qwen3 dense | Yes | Yes | Yes |
| Qwen3 MoE | Yes | Yes | Yes |
| Qwen3-Next 80B (hybrid GDN) | Yes (v0.18+; nightly initially) | Yes (v0.5.0+) | Beta (v1.x) |
| Qwen3.5 (hybrid GDN MoE) | Yes (v0.17+) | Yes (v0.5.8+) | Beta |
| **Qwen3.6-27B (dense + GDN)** | **Yes (v0.19+)** | **Yes (v0.5.10+)** | **Not listed in support matrix** |

## OpenAI API compatibility

All three expose `/v1/chat/completions` and `/v1/completions`. Drop-in swap is mostly painless. Differences:
- vLLM: most polished, broad tool-call parser catalog, structured output via XGrammar/Outlines/Guidance/LM-Format-Enforcer.
- SGLang: compressed-FSM constrained decoding (3× faster guided JSON), tool parsers for popular models.
- TensorRT-LLM `trtllm-serve`: newest of the three; smaller parser catalog; less battle-tested than the others.

## Sources
- https://www.spheron.network/blog/vllm-vs-tensorrt-llm-vs-sglang-benchmarks/
- https://www.clarifai.com/blog/comparing-sglang-vllm-and-tensorrt-llm-with-gpt-oss-120b
- https://www.yottalabs.ai/post/tensorrt-llm-vs-vllm-vs-sglang-vs-tgi-which-inference-engine-actually-performs-best-in
- https://www.yottalabs.ai/post/best-llm-inference-engines-in-2026-vllm-tensorrt-llm-tgi-and-sglang-compared
- https://leetllm.com/blog/llm-inference-engine-comparison-2026
- https://particula.tech/blog/sglang-vs-vllm-inference-engine-comparison
- https://arxiv.org/pdf/2312.07104 (RadixAttention paper)
