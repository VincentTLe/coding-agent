# B4: KV Cache Optimizations in vLLM 2026

Date: 2026-05-18. Target: 2x A6000 (SM 8.6, 96 GB, NVLink) serving Qwen 3.6-27B BF16, TP=2.

## TL;DR
For an agent that resends a long system prompt every turn, the headline win is **prefix caching** — and on vLLM V1 it is **already on by default**. Combine with **chunked prefill** (also default-on) and `max_num_batched_tokens >= 8192`. **FP8 KV cache is NOT viable on A6000**: `fp8e4nv` needs CUDA arch >= 8.9, and FP8 KV + chunked prefill is documented broken on Ampere (vLLM #7714, closed not-planned). Native CPU/disk offload is RFC-only in V1; today's fallback is preemption + recompute.

## Why this matters
A coding agent reloads the same system prompt, tool defs, repo overview, and step history every ReAct turn. Agent input:output ratio commonly exceeds 100:1 ([llm-d]). Without prefix caching, each turn re-prefills tens of thousands of tokens it already processed.

## SOTA in vLLM 2026 (V1)
1. **Chunked prefill** (default ON). Splits long prefills into chunks batched with running decodes.
2. **Automatic prefix caching** (default ON). Block-level SHA-256 hash over KV cache; matching prefix blocks reused across requests. LRU eviction, ref-counted. `<1%` overhead at 0% hit; multi-x gains when hit rate is high.
3. **FP8 KV cache** (`--kv-cache-dtype fp8|fp8_e4m3|fp8_e5m2`). Cuts KV memory to ~54% of BF16. Hopper+ only in practice.
4. **Auto cross-request prefix sharing**. Falls out of (2) — same hashes are reused across concurrent sessions, no extra flag. [UNVERIFIED] `cache_salt` isolates tenants.
5. **CPU/disk swap-out**. `--swap-space` is largely unused in V1. RFC #16144 / #19854 propose lazy swap; not GA. External tiered caches (LMCache) cover huge-context offload today.

## Most-used (industry signal)
"Paged attention is the substrate, prefix caching is the high-leverage optimization, FP8 KV is the free 50% memory savings every team should already have on" ([digitalapplied]). Hopper deployments run all three; Ampere drops the FP8 leg.

## Comparison

| Optimization | Flag | Memory | Latency | A6000? | Agent fit |
|---|---|---|---|---|---|
| Chunked prefill | default; `--max-num-batched-tokens` | neutral | ITL better <8192, TTFT/throughput better >8192 | Yes | Yes |
| Prefix caching | default; `--enable-prefix-caching` | shared blocks | TTFT 4.3 s -> 0.6 s on 10k reuse ([llm-d]) | Yes | Critical |
| FP8 KV e4m3 | `--kv-cache-dtype fp8` | -46% KV ([vLLM blog]) | +14.9% throughput, -14.8% ITL on H100 | **NO** (SM<8.9) | N/A |
| FP8 KV e5m2 | `--kv-cache-dtype fp8_e5m2` | similar | similar | Broken w/ chunked prefill on Ampere | Avoid |
| Cross-request share | implicit | shared physical blocks | large gains multi-tenant | Yes | Yes |
| CPU/disk offload | `--swap-space N` | overflow only | recompute on return | Yes | No GA |

## Recommendation
```
vllm serve Qwen/Qwen3.6-27B \
  --tensor-parallel-size 2 \
  --enable-prefix-caching \
  --enable-chunked-prefill \
  --max-num-batched-tokens 8192 \
  --gpu-memory-utilization 0.92 \
  --max-model-len <agent ceiling>
```
Rationale: prefix caching is the dominant win — expected hit rates 60-85% on agent loops give 5-12x per-call cost reduction ([digitalapplied]). Chunked prefill stops long prompts from blocking in-flight decodes. Skip FP8 KV on A6000. Skip `--swap-space` — preemption + recompute is the real fallback; avoid VRAM pressure by capping `--max-model-len` instead.

## Next steps
1. Log `prefix_cache_hit_rate`, TTFT, ITL from vLLM metrics over 20 representative agent turns.
2. Confirm V1 is active (vLLM >= 0.8 line); print effective config at startup.
3. Concurrency-test multi-session sharing on identical system prompts.
4. Watch RFC #16144 + LMCache; revisit if context outgrows 96 GB BF16 KV.

## Open questions
- [UNVERIFIED] Real hit rate for our specific Qwen 3.6-27B prompt template — depends on block-alignment stability across turns.
- [UNVERIFIED] Does `--tokenizer-mode fastokens` compose cleanly with prefix-cache block hashing on our V1 build?
- [UNVERIFIED] Will INT8 KV cache (vLLM #33480) land to give Ampere a quantized-KV path?

## Sources
- vLLM Automatic Prefix Caching: https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/
- vLLM Prefix Caching Design (V1): https://docs.vllm.ai/en/stable/design/prefix_caching/
- vLLM Optimization and Tuning: https://docs.vllm.ai/en/stable/configuration/optimization/
- vLLM Quantized KV Cache: https://docs.vllm.ai/en/latest/features/quantization/quantized_kvcache/
- vLLM blog "State of FP8 KV-Cache" (2026-04-22): https://vllm-project.github.io/2026/04/22/fp8-kvcache.html
- vLLM Recipes Qwen3.6-27B: https://recipes.vllm.ai/Qwen/Qwen3.6-27B
- vLLM #7714 (FP8 KV + chunked prefill on Ampere): https://github.com/vllm-project/vllm/issues/7714
- vLLM RFC #16144 (CPU offload V1): https://github.com/vllm-project/vllm/issues/16144
- vLLM RFC #19854 (KV cache offloading): https://github.com/vllm-project/vllm/issues/19854
- llm-d "KV-Cache Wins You Can See": https://llm-d.ai/blog/kvcache-wins-you-can-see
- digitalapplied "KV Cache Optimization 2026": https://www.digitalapplied.com/blog/kv-cache-optimization-techniques-2026-engineering-guide
