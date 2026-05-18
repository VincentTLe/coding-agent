# llm-d "KV-Cache Wins You Can See" — cached numbers

Source: https://llm-d.ai/blog/kvcache-wins-you-can-see (fetched 2026-05-18)

## Single-instance prefix caching
- **TTFT: 4.3 s → 0.6 s** when reusing a ~10,000-token prompt (single vLLM instance).

## Distributed deployment (8 vLLM pods, 16 H100 GPUs)
- **TTFT P90 with precise prefix scheduling: 0.542 s** vs 31.083 s approximate.
- **57x faster** than approximate scheduling, **170x faster** than random.
- Throughput: **8,730 output tok/s**; **+25%** vs approximate, **2x** vs cache-blind.

## Cost framing
- "Cost for cached tokens is **10x lower** than uncached ($0.30 vs $3.00 per M tokens)."

## Agent workloads
- "Most extreme case of prefix dominance — input:output ratio exceeds 100:1."
- Agent loops keep static context (tools + step history) as cached prefixes; only new observations/actions need compute.
- Cache-aware routing matters at fleet scale: naive load balancers scatter related requests and destroy hit rate.

## Practical hit-rate ranges (digitalapplied / community)
- Agent loops, multi-tenant SaaS, repo Q&A, long-doc workflows: **60–85% hit rate**, "5–12x" cost reduction per call.
- "85–95% cost savings on cache hits."
