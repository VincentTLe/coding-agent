# vLLM Automatic Prefix Caching — Design Notes (cached)

Source: https://docs.vllm.ai/en/stable/design/prefix_caching/ (fetched 2026-05-18)
Companion source: https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/

## Default status (V1)
- Prefix caching is **enabled by default in vLLM V1**. Near-zero overhead: "<1% throughput decrease at 0% cache hit, multi-x improvement at high hit rate".

## How it works
- KV cache is split into fixed-size **Blocks** (each block = block_size tokens, configurable).
- Each block has a `block_hash` assigned once full. Hash combines: parent hash + exact block tokens + extra hashes (LoRA IDs, MM input hashes, `cache_salt`).
- Cache uses a global hash table mapping hash → physical block ID.
- New request's prefix is split into blocks; matching hashes are reused (skip prefill compute), only the suffix is computed.

## Hash algorithms (`prefix_caching_hash_algo`)
- `sha256` (default; collision-safe via Pickle serialization)
- `sha256_cbor` (reproducible, cross-language via canonical CBOR)
- `xxhash` (fastest, slightly higher collision risk)

## Eviction policy
- LRU eviction over free blocks (doubly-linked queue).
- "Touch" operations bump reference counts to protect actively-shared prefixes from premature eviction.
- Block tables are append-only; duplicate blocks collapse when requests finish.

## Cross-request sharing
- Multiple requests with the same prefix all reference the same physical block(s).
- `cache_salt` per request can isolate tenants for security/timing reasons.

## When it helps / doesn't
- Helps: long shared system prompts, multi-turn chat history, repeated long-document queries, agent loops that resend tool definitions every turn.
- Does NOT speed up decode — only prefill. If response is mostly generation, gains are smaller.
