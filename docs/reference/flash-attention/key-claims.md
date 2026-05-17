# FlashAttention — Key Claims

Source: Dao et al., "FlashAttention-2: Faster Attention with Better Parallelism and Work Partitioning"
URL: https://arxiv.org/abs/2307.08691
Accessed: 2026-05-17

Earlier paper: Dao et al., "FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness", https://arxiv.org/abs/2205.14135

## Core claim

- Memory complexity: **O(N)** vs standard attention's **O(N²)** — for memory specifically.
- Time complexity: still O(N²) in FLOPs, but wall-clock is reduced 2–4× by exploiting the GPU memory hierarchy (SRAM vs HBM).

## Mechanism

- "Exploits the asymmetric GPU memory hierarchy" through **block-wise tiling**.
- Attention is computed in tiles small enough to fit in fast SRAM; the full N×N attention matrix is never materialized.
- FlashAttention-2 improvements:
  - Reduces non-matrix-multiply operations
  - Parallelizes attention computation across thread blocks
  - Distributes work between warps to minimize shared-memory communication

## Reported numbers

- FlashAttention (v1): 2–4× speedup vs optimized baselines
- FlashAttention-2: ~2× speedup over v1; reaches 50–73% of theoretical FLOPs on A100
- End-to-end training: up to 225 TFLOPs/s on A100 (72% MFU)

## Relevance to our project

vLLM uses FlashAttention (v2 / v3) under the hood automatically. We don't import it directly. But: knowing that attention is *time*-O(N²) but *memory*-O(N) is essential for explaining why Qwen 3.6-27B can advertise 262K context without OOMing.
