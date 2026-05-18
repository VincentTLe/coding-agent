# SGLang reference notes (cached 2026-05-18)

Source: scraped from sgl-project.github.io, docs.sglang.io, and 2026 third-party benchmarks.

## What it is
- High-throughput LLM/VLM serving framework. Open-source. Initially from LMSYS.
- Backed in production by xAI, NVIDIA, Cursor, OpenAI Codex sponsorship pool.
- Pitched as "production server for prefix-heavy and structured-output workloads."

## Core differentiators vs vLLM / TensorRT-LLM
1. **RadixAttention** — radix-tree (trie + LRU) KV-cache shared across *all* concurrent requests. Automatic prefix detection and reuse; no manual prefix declaration needed. Whitepaper (arXiv 2312.07104, LMSYS) reports up to 6.4× throughput vs naïve KV-cache on RAG / multi-turn workloads.
2. **Compressed-FSM constrained decoding** — overlaps grammar mask generation with the forward pass; ~3× faster than guided-decoding baselines on JSON/regex/EBNF schemas.
3. **Mamba Radix Cache** — extends RadixAttention to hybrid (Mamba/DeltaNet) models via two scheduling strategies:
   - V1 `no_buffer` (default, lower memory).
   - V2 `extra_buffer` (overlap scheduling + branching-point caching, requires FLA kernel backend; NVIDIA-only).
4. **Day-0 model support** — Qwen3.5 was supported on launch day; Qwen3.6 has an official cookbook recipe.

## OpenAI compatibility
- Exposes `/v1/chat/completions`, `/v1/completions`, `/v1/embeddings`.
- Drop-in switch from vLLM: only the base URL changes.
- Tool-call parsers: `qwen3_coder`, `llama3_json`, `mistral`, etc. selected via `--tool-call-parser`.
- Reasoning parser: `--reasoning-parser qwen3` for thinking-mode separation.

## Hardware
- NVIDIA Ampere (A100, A6000, RTX 3090) and newer. SM80, SM86 supported.
- ROCm support for MI300X (Triton-only path; FLA kernels work on ROCm).
- TPU/Ascend paths exist but are experimental.

## Quantization
- FP8 (weights + activations) — Hopper/Blackwell native; on Ampere requires Marlin kernel route (slower).
- AWQ (INT4) — supported.
- GPTQ (INT4) — supported.
- BF16/FP16 baseline.
- Open issue 12887: MoE FP8 W8A8 via Marlin on Ampere — partial support; not all MoE models work.

## Multi-GPU
- `--tp N` for tensor parallel.
- `--dp N` for data parallel.
- `--ep` for expert parallel (MoE).
- Pipeline parallel exists but is less polished than vLLM's PP path.

## Versioning anchors
- v0.5.10 — Qwen3.6 official support.
- v0.5.9 — Qwen3.6-coder agentic features.
- "SGLang Release 25.11" — NVIDIA-curated NGC container snapshot.

## Common SGLang flags for our setup
```
python -m sglang.launch_server \
  --model-path Qwen/Qwen3.6-27B \
  --tp 2 \
  --reasoning-parser qwen3 \
  --tool-call-parser qwen3_coder \
  --mem-fraction-static 0.8 \
  --host 0.0.0.0 --port 8000
```

## Bench numbers seen in the wild (H100 SXM5 80GB, Llama-3.3 70B FP8, Spheron 2026)
| Concurrency | tok/s |
|---|---|
| 1 | 125 |
| 10 | 680 |
| 50 | 1,920 |
| 100 | 2,460 |
- vs vLLM: +2–5% raw throughput on non-prefix-heavy workloads.
- vs vLLM: +29% on Llama-3.1-8B with shared prefixes; up to +6.4× on RAG / multi-turn.

## Limitations
- Smaller ecosystem than vLLM (fewer one-click recipes, fewer model families day-0).
- Newer; some sharp edges in MoE FP8 on Ampere.
- Smaller chat-completion plugin set than vLLM.
- Tool-call parsers cover the popular models but the catalog is smaller than vLLM's.

## Sources
- https://sgl-project.github.io/
- https://docs.sglang.io/cookbook/autoregressive/Qwen/Qwen3.6
- https://cookbook.sglang.io/autoregressive/Qwen/Qwen3-Coder-Next
- https://arxiv.org/pdf/2312.07104 (RadixAttention paper)
- https://github.com/sgl-project/sglang
- https://github.com/sgl-project/sglang/issues/12887 (Ampere MoE FP8)
- https://docs.nvidia.com/deeplearning/frameworks/sglang-release-notes/rel-25-11.html
