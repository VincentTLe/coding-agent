# vLLM — Parallelism and Quantization (Summary)

Accessed: 2026-05-17

## Parallelism

Source: https://docs.vllm.ai/en/latest/serving/parallelism_scaling.html

### Tensor parallelism

- CLI flag: `--tensor-parallel-size N` (split each layer across N GPUs)
- Example: `vllm serve facebook/opt-13b --tensor-parallel-size 4`
- Use when "the model is too large for a single GPU but fits on a single node with multiple GPUs"
- NVLink note: "If the GPUs on the node do not have NVLINK interconnect (e.g. L40S), leverage pipeline parallelism instead of tensor parallelism for higher throughput and lower communication overhead."

### Pipeline parallelism

- Splits the model along layers, vertically.
- Supports uneven splits (useful when GPU count doesn't evenly divide model size).
- Preferred over tensor parallelism when NVLink is absent.

### For our 2× A6000 (with NVLink NV4)

```bash
vllm serve Qwen/Qwen3.6-27B --tensor-parallel-size 2 --port 8765
```

## Quantization

Source: https://docs.vllm.ai/en/latest/features/quantization/index.html

Supported methods (verbatim list from docs index):

1. AutoAWQ — INT4 weight-only, activation-aware
2. BitsAndBytes — multi-bit (NF4, FP4, INT8)
3. GGUF — llama.cpp file format with embedded quants
4. GPTQModel — GPTQ INT4
5. Intel Neural Compressor
6. INT4 W4A16 — 4-bit weight, 16-bit activation
7. INT8 W8A8 — 8-bit weight and activation
8. FP8 W8A8 — FP8 weight and activation (Hopper+ hardware needed)
9. NVIDIA Model Optimizer
10. Online Quantization — dynamic at inference
11. AMD Quark
12. Quantized KV Cache
13. TorchAO
14. FP8 ViT Encoder Attention

Hardware notes:
- FP8 requires Ada / Hopper / newer (not A6000).
- INT4 (AWQ, GPTQ) works on Ampere (A6000) via int8 cores + dequant.

For our project we do **not** quantize: 54 GB BF16 fits in 96 GB combined VRAM under TP=2.
