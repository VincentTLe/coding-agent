# vLLM Chunked Prefill — Tuning Notes (cached)

Source: https://docs.vllm.ai/en/stable/configuration/optimization/ (fetched 2026-05-18)
Companion: https://docs.vllm.ai/en/v0.8.2/performance/optimization.html

## Default status (V1)
- "Chunked prefill is enabled by default whenever possible" in V1.
- Behavior: when a pending prefill cannot fit `max_num_batched_tokens`, vLLM chunks it and batches the chunks alongside running decodes.
- Goal: keep GPU saturated by mixing compute-bound (prefill) and memory-bound (decode) work in the same step.

## `max_num_batched_tokens` trade-off
| Value | Effect |
|---|---|
| Smaller (e.g. 2048) | Better **ITL** (decodes preempt less). Worse TTFT. |
| Larger (>8192, recommended) | Better **TTFT** + **throughput**. Worse ITL. |

Recommendation from docs: `max_num_batched_tokens > 8192`, especially for smaller models on large GPUs.

## Known interactions
- vLLM issue #8223: poor TTFT seen when `--enable-chunked-prefill` and `--enable-prefix-caching` combined naively in older versions. V1 schedulers reconcile this; verify with target release.
- vLLM issue #7714: **FP8 KV cache + chunked prefill is broken on Ampere (A6000, A100)** — `fp8e4nv data type not supported on CUDA arch < 89`. Closed not-planned.

## Example benchmark
- DeepSeek-R1-Distill-Llama-70B with `--enable-chunked-prefill`, `max_num_batched_tokens=98304`: mean TTFT 20543 ms, output 292 tok/s, total 998 tok/s.

## CPU provisioning (relevant when chunking many requests)
- Minimum physical cores = A + DP + N + (1 if DP > 1 else 0), where A=API servers, DP=data parallel, N=GPU count.
