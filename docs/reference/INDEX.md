# Cached reference docs

Per AGENTS.md Rule B: when a non-trivial technology is introduced, its official docs are cached here.

Format: `<technology>: <URL>, downloaded YYYY-MM-DD, covers <topic>`

- Qwen3.6-27B: https://huggingface.co/Qwen/Qwen3.6-27B, downloaded 2026-05-17, covers architecture (64 layers, hybrid Gated DeltaNet + Gated Attention), tokenizer vocab 248,320, BF16 weights, 262K context → `qwen-3.6-27b/model-card-summary.md`
- vLLM parallelism + quantization: https://docs.vllm.ai/en/latest/serving/parallelism_scaling.html and https://docs.vllm.ai/en/latest/features/quantization/index.html, downloaded 2026-05-17, covers `--tensor-parallel-size` flag, NVLink guidance, supported quant methods (AWQ, GPTQ, FP8, INT4, ...) → `vllm/parallelism-and-quantization.md`
- FlashAttention: https://arxiv.org/abs/2307.08691 (v2 paper) + https://arxiv.org/abs/2205.14135 (v1), downloaded 2026-05-17, covers O(N) memory vs naive O(N²), block-wise tiling, 2-4× speedup → `flash-attention/key-claims.md`
- PagedAttention / vLLM paper: https://arxiv.org/abs/2309.06180, downloaded 2026-05-17, covers KV cache block management, 2-4× throughput over baseline serving systems → `paged-attention/key-claims.md`
- NVIDIA RTX A6000 spec: https://www.nvidia.com/en-us/design-visualization/rtx-a6000/, downloaded 2026-05-17, covers 48 GB GDDR6, 768 GB/s mem bw, 112 GB/s NVLink, Ampere (no native FP8) → `nvidia-a6000/specs-summary.md`
