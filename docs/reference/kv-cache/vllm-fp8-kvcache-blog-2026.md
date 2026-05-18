# vLLM FP8 KV-Cache Blog (April 2026) — cached numbers

Source: https://vllm-project.github.io/2026/04/22/fp8-kvcache.html (fetched 2026-05-18)
Mirror: https://github.com/vllm-project/vllm-project.github.io/blob/main/_posts/2026-04-22-fp8-kvcache.md

## Memory savings
- "Per-token cost of the KV cache can be reduced to **54% of its BF16 counterpart** in the best cases." Effectively ~halves storage; ~2x concurrency at the same VRAM.

## Throughput / latency (H100, concurrency 8, ~20k input tokens)
| Model | Output throughput | Total runtime | Median ITL |
|---|---|---|---|
| Llama-3.1-8B | **+14.9%** | **-13.0%** | **-14.8%** |
| gpt-oss-20b (skip sliding-window) | +4.8% | -4.6% | -4.8% |

For Llama-3.1-8B, FP8 nearly halves decode ITL slope vs BF16. Decode break-even ~7k tokens. TTFT similar.

## Accuracy impact (uncalibrated worst case)
- Reasoning (Qwen3-30B): "at most 1-2 points of accuracy degradation".
- Long context (Llama-3.3-70B): "recovers 97-98% of baseline AUC".
- 1M-token regime (Qwen3.5-27B): "fully recovers aggregated AUC@1M metric".

## Supported hardware / formats
- **GPUs**: H100 (Hopper), H200, B200 (Blackwell). Evaluations use **e4m3**.
- **Backends**: Flash Attention 3 (H100), FlashInfer (B200).
- **Ampere (A6000, A100, SM 8.0–8.6)**: NOT validated; `fp8e4nv` is not supported on CUDA arch < 8.9. Only `fp8_e5m2` plausibly runs via Triton on SM 8.6, and `--enable-chunked-prefill + fp8 kv cache` is documented broken on Ampere (vLLM issue #7714, closed not-planned).

## Recommended flags
```
--kv-cache-dtype fp8                                 # e4m3 default, Hopper+
--kv-cache-dtype-skip-layers sliding_window          # hybrid-attention models
```

## Caveats
- Hybrid-attention models with small sliding-window layers: skip those layers.
- Large-head-dim (head_dim = 256) models: prefill can regress.
