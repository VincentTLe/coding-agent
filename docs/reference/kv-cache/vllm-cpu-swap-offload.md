# vLLM CPU Swap / KV Offload — Status (cached)

Sources:
- https://github.com/vllm-project/vllm/issues/16144 (RFC: Offload KV cache to CPU in V1)
- https://github.com/vllm-project/vllm/issues/19854 (RFC: KV cache offloading)
- https://discuss.vllm.ai/t/possible-to-offload-kv-cache-to-dram-or-nvme/1682
- https://docs.vllm.ai/en/stable/api/vllm/config/cache/
Fetched 2026-05-18.

## State of native CPU/disk offload (as of May 2026)
- "Currently, in vLLM v1 there is no in-house solution for offloading KV cache data from GPU memory to other media (in particular, CPU memory)."
- RFC #16144 + PRs #13377 and #17653 propose a lazy swap-in/swap-out design integrated into the scheduler step. **Not GA**.
- NVMe/disk offload: experimental, only via external connectors (e.g. LMCache); not a first-class vLLM flag.

## What `--swap-space` actually does
- The pre-V1 flag survives but is **largely unused in V1**. The RFC proposes repurposing it to set CPU cache block count.
- Default 0 (no offload). Unit: GiB per GPU.
- In V0 / older builds, it was used only as overflow on preemption, not transparent paging.

## Preemption (the real fallback today)
- When KV space runs out, vLLM **preempts** requests rather than swapping pages. Preempted requests are **recomputed** when capacity returns.
- Implication for our agent: under VRAM pressure, expect recompute spikes, not gentle slowdown. The cure is to prevent preemption, not to rely on swap.

## Practical mitigations available now
1. Quantize KV (`--kv-cache-dtype fp8` on Hopper+; not on Ampere).
2. Cap `--max-model-len` to actual needed context.
3. Tune `--gpu-memory-utilization` upward (e.g. 0.92).
4. Use prefix caching to avoid keeping duplicate KV across sessions.
5. External tiered cache (LMCache) for "huge context" workloads.
