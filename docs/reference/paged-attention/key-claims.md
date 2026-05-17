# PagedAttention / vLLM — Key Claims

Source: Kwon et al., "Efficient Memory Management for Large Language Model Serving with PagedAttention" (SOSP 2023)
URL: https://arxiv.org/abs/2309.06180
Accessed: 2026-05-17

Authors: Woosuk Kwon, Zhuohan Li, Siyuan Zhuang, Ying Sheng, Lianmin Zheng, Cody Hao Yu, Joseph E. Gonzalez, Hao Zhang, Ion Stoica.

## Core idea

KV cache memory grows and shrinks dynamically per request, causing fragmentation and duplication in naive contiguous allocators. PagedAttention treats KV cache like OS virtual memory:

- Fixed-size **blocks** (typical: 16 tokens / block).
- Per-request **block table** (indirection).
- Non-contiguous physical layout.
- Result: **near-zero waste in KV cache memory**.

Bonus: blocks can be **shared** across requests with common prefixes — supports prompt prefix caching for free.

## Reported numbers

- vLLM (built on PagedAttention) improves throughput **2–4×** over FasterTransformer and Orca, at comparable latency.
- Anyscale benchmarks combining PagedAttention + continuous batching report up to **23×** throughput over naive serving.

## Continuous batching (separate but combined)

- Introduced by Orca (Yu et al., OSDI 2022).
- Iteration-level scheduling: new requests can join the batch after every token step; completed ones leave.
- Selective batching for layers that can't be merged across requests.
- vLLM combines this with PagedAttention; both are on by default.

## Relevance to our project

vLLM uses PagedAttention by default. We benefit transparently — multi-request agent loops will batch and share prefixes (system prompt KV cache) automatically.
