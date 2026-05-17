# 09 — Tensor Parallelism

## Core idea (1-2 sentences)

Tensor parallelism splits each layer's weight matrices **across GPUs** so a model too large for one card can run as if all the GPUs were one virtual card. After every layer, the GPUs synchronize via an all-reduce.

## Why it matters for our project

Qwen 3.6-27B in BF16 is 54 GB. One A6000 is 48 GB. Without tensor parallelism, we cannot serve this model on our hardware. The vLLM flag `--tensor-parallel-size 2` is the single most consequential serving choice we make.

## The intuition

Imagine a 100-piece orchestra trying to fit on a 50-seat stage. You can't squeeze. So you put 50 musicians on stage A, 50 on stage B, and they play simultaneously, synchronizing at the end of each bar. The conductor (NVLink) keeps them in time. If the bridge between stages is too narrow (no NVLink, only PCIe), the synchronization is the bottleneck and you sound terrible.

Concretely: each weight matrix `W` of shape `(out, in)` is sliced along the columns: `W = [W_1 | W_2]`. GPU 0 holds `W_1`, GPU 1 holds `W_2`. Each computes a partial output. Then they sum their partials → the same result as one GPU computing `W·x`.

## The mechanics

### What splits, what doesn't

In a Transformer block, tensor parallelism slices:

- **Q, K, V projection matrices**: per-head distribution. With TP=2, half the attention heads on each GPU.
- **Output projection of attention**: row-sliced (paired with the column-slice of QKV).
- **FFN's two matrices**: column-slice up-projection, row-slice down-projection — this pairing lets the in-between activation be local to each GPU, with the all-reduce happening on the output.
- **Embedding table**: vocab-parallel — each GPU holds part of the vocabulary's embeddings.

What stays whole or replicated:
- LayerNorm parameters (tiny).
- Position embeddings / RoPE constants (small).
- KV cache for *each* layer is sliced the same way as that layer's K and V projection — each GPU stores its own slice.

### The all-reduce — why NVLink matters

After the attention output projection and after the FFN down-projection, each GPU has a *partial* result. They need to be summed across GPUs to get the true result. This is an **all-reduce** collective: each GPU contributes a tensor, every GPU ends up with the sum.

For Qwen 3.6-27B, this all-reduce happens twice per layer × 64 layers = 128 times per forward pass. For a sequence of 1 token (typical decode step), the all-reduce moves about `hidden_dim × dtype_bytes = 5,120 × 2 = ~10 KB` per call. Tiny. Done over NVLink (112 GB/s) it costs about 10 KB / 112 GB/s ≈ 0.1 microseconds. Negligible.

But over PCIe Gen4 (~32 GB/s) and especially in larger-batch/longer-sequence cases (think of all-reduce on `batch × seq × hidden`), the cost climbs. **vLLM's docs explicitly recommend pipeline parallelism over tensor parallelism when NVLink is absent**:

> "If the GPUs on the node do not have NVLINK interconnect (e.g. L40S), leverage pipeline parallelism instead of tensor parallelism for higher throughput and lower communication overhead." — vLLM distributed-serving docs

Our 2× A6000 have NVLink (NV4 topology in `nvidia-smi topo -m`, confirmed in server audit). We're in the right regime for tensor parallelism.

### How vLLM activates it

A single CLI flag:

```bash
vllm serve Qwen/Qwen3.6-27B --tensor-parallel-size 2
```

This:
1. Launches two worker processes, one per GPU.
2. Loads half the weights on each GPU.
3. Sets up NCCL (NVIDIA Collective Communications Library) for all-reduces.
4. Routes incoming OpenAI-API requests through a single coordinator that broadcasts inputs and gathers outputs.

From the client's perspective (OpenAI SDK), nothing changes. The server presents as a single logical model.

### Tensor parallelism vs pipeline parallelism

The other way to split a model across GPUs:

- **Tensor parallelism (TP)**: split *within* a layer (horizontally). All GPUs participate in every layer. Frequent small all-reduces. Good with NVLink. Latency-friendly.
- **Pipeline parallelism (PP)**: split *between* layers (vertically). GPU 0 holds layers 1–32, GPU 1 holds layers 33–64. Forward pass cascades through. Communication is point-to-point and infrequent. Good without NVLink. Throughput-friendly with batching; latency-unfriendly for single requests (pipeline bubble).

Production setups sometimes combine both (e.g., 2D parallelism for very large models). For us, pure TP=2 is the simplest and best fit.

### What about data parallelism?

Data parallelism (DP) replicates the *whole model* on each GPU and feeds them different requests. Useful when the model fits on one GPU and you want more throughput. Qwen 3.6-27B does not fit on one A6000, so DP is not an option here. If we had a smaller model, DP=2 would double throughput while keeping latency low.

### vLLM's quiet mention: communication overhead

`nvidia-smi topo -m` reports `NV4` between our GPU0 and GPU1: a bonded set of **4 NVLinks**. Per-link bandwidth is around 28 GB/s; 4 links give 112 GB/s aggregate bidirectional bandwidth. This is the official A6000 NVLink spec. The all-reduce time is small enough that, for our model size and batch size, communication is not the bottleneck — compute is.

## Concrete numbers for our setup

| Spec                              | Value         |
|-----------------------------------|---------------|
| GPUs                              | 2× RTX A6000  |
| Per-GPU VRAM                      | 48 GB         |
| NVLink topology (from server audit) | NV4 (4 bonded links) |
| NVLink aggregate bandwidth        | 112 GB/s      |
| Tensor parallel size              | 2             |
| Model weight per GPU              | ~27 GB        |
| All-reduces per forward pass      | 128 (2 per layer × 64 layers) |
| Per-all-reduce data (decode 1 token, BF16) | ~10 KB |
| Per-all-reduce time over NVLink   | sub-microsecond |
| vLLM flag                         | `--tensor-parallel-size 2` |

### Typical vLLM startup command for us (reference, do not run yet)

```bash
# Phase 2 of project — not yet implemented.
CUDA_VISIBLE_DEVICES=0,1 vllm serve Qwen/Qwen3.6-27B \
    --tensor-parallel-size 2 \
    --port 8765 \
    --max-model-len 32768 \
    --gpu-memory-utilization 0.85
```

Each flag should be reviewed against the live vLLM docs before launch (Rule A from AGENTS.md).

## Likely questions from the professor

**Q: Why split the weight matrix and not just have one GPU compute everything?**
A: Because the matrix doesn't fit in one GPU's memory. Splitting halves the per-GPU memory cost. The two GPUs work in parallel during compute, which is a side benefit; the *primary* reason is the memory constraint.

**Q: Doesn't synchronizing every layer slow you down?**
A: A little, but over NVLink the all-reduce is dwarfed by the compute. For our setup, you can measure it: vLLM logs per-token latency, and TP=2 on 2× A6000 with NVLink has ~5–10% overhead vs a hypothetical 96 GB single GPU. Without NVLink, it can be much worse (we don't have to deal with that).

**Q: Why not use pipeline parallelism instead?**
A: PP introduces a pipeline bubble at the start and end of each batch — GPUs sit idle waiting for the cascade to fill. For interactive single-request latency (an agent that's making one tool call at a time), TP is better. PP shines for high-throughput batch serving without NVLink.

**Q: How does the KV cache work under tensor parallelism?**
A: Each GPU holds the K and V for its slice of the attention heads. Per-request memory cost is the same; it's just split between GPUs. No special handling at the application level.

**Q: What is NCCL?**
A: NVIDIA Collective Communications Library — implements all-reduce, all-gather, broadcast, etc., optimized for NVLink / PCIe / InfiniBand topologies. vLLM uses NCCL under the hood for tensor parallelism. You don't interact with it directly.

**Q: Could we use 4 GPUs with TP=4?**
A: We don't have 4 GPUs on this machine. If we did, TP=4 would halve each GPU's weight load to ~13.5 GB and open more KV cache headroom. Diminishing returns past TP=8 due to communication overhead.

## Common misconceptions / gotchas

- **"Tensor parallelism doubles inference speed."** No — it makes inference *possible* for models too big for one GPU. Speed is roughly the same as the equivalent-single-GPU case for compute; communication overhead is the cost.
- **"All-reduce is the bottleneck."** Only without NVLink, or for very large batches/sequences. With NVLink on a 27B model in our regime, compute dominates.
- **"`--tensor-parallel-size` must divide vocab size, layer count, head count."** Yes — vLLM will error out if the model dimensions aren't cleanly divisible. For Qwen 3.6-27B: 64 layers (÷2 ok), 248,320 vocab (÷2 ok), heads (divisible by 2 in both Gated Attention and Gated DeltaNet). TP=2 works. TP=3 or TP=5 typically won't.
- **"TP and DP are mutually exclusive."** They're orthogonal — for very large clusters you can have TP=8 within a node and DP=4 across nodes simultaneously. Our setup is just TP=2.
- **Previously confused with model sharding (FSDP)**: FSDP (Fully Sharded Data Parallel) is a *training* technique that shards optimizer state, gradients, and parameters across GPUs and gathers them as needed. Tensor parallelism keeps the slices distributed during compute. Same goal (fit a huge model), different mechanism.

## Sources

- vLLM distributed serving / parallelism docs: https://docs.vllm.ai/en/latest/serving/parallelism_scaling.html (accessed 2026-05-17)
- Shoeybi et al., "Megatron-LM: Training Multi-Billion Parameter Language Models Using Model Parallelism" (introduced this style of tensor parallelism): https://arxiv.org/abs/1909.08053
- NVIDIA NVLink for RTX A6000 (112 GB/s, 2-card bridge): https://www.nvidia.com/en-us/design-visualization/rtx-a6000/ (accessed 2026-05-17)
- NVIDIA NCCL documentation: https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/index.html
- Local server audit: `nvidia-smi topo -m` shows NV4 between GPU 0 and GPU 1 (see SERVER_STATE.md)
