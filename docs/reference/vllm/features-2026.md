# vLLM 2026 features — cached reference

Cached extract from research conducted 2026-05-18. Source URLs in `docs/research/B1-vllm-2026-features.md`.

## Current stable version
- **v0.21.0** released **2026-05-15** (PyPI confirmed).
- Requires C++20 compiler; Transformers v4 formally deprecated (migrate to v5).
- ROCm 7.2.2 for AMD; default CUDA wheel uses CUDA 13.0.
- Python 3.10–3.14 supported.
- Recent cadence: v0.18 (2026-03-20), v0.19 (2026-04-03), v0.20 (2026-04-27), v0.21 (2026-05-15).

## V1 engine = current default
- V1 is the default execution engine and ships with **prefix caching, chunked prefill, async scheduler ON by default**.
- "Almost a free lunch" — <1% throughput hit at 0% cache hit; multi-x gains at high hit rate.
- V1 chunked prefill cannot be turned off via CLI; always on.

## Prefix caching (`--enable-prefix-caching`)
- **Default in V1.** Use `--no-enable-prefix-caching` to disable.
- Hashing: `--prefix-caching-hash-algo {sha256|sha256_cbor|xxhash|xxhash_cbor|builtin}`.
- Default became `sha256` since v0.11 to address collision risks.
- Block-level granularity; LRU eviction. Per-request `cache_salt` available for multi-tenant isolation.
- Biggest wins on: long-system-prompt agents, multi-turn chat, multi-doc RAG with shared prefixes.

## Chunked prefill (`--enable-chunked-prefill`)
- Always on in V1.
- Main knob: `--max-num-batched-tokens`.
  - **Smaller (≈2048)**: best inter-token latency (ITL), interactive workloads.
  - **Larger (≥8192)**: best time-to-first-token (TTFT) and throughput.
- Decode requests get priority; prefill is sliced and co-batched.

## Speculative decoding (`--speculative-config '<json>'`)
- Methods: `ngram`, `eagle`, `eagle3`, `medusa`, `mlpspeculator`, `mtp` (Qwen3.x multi-token prediction).
- v0.21 adds: respects reasoning/thinking budgets; independent drafter attention backend; basic multimodal support.
- N-gram JSON: `{"method":"ngram","num_speculative_tokens":5,"prompt_lookup_max":4}`.
- EAGLE3 JSON: `{"method":"eagle3","model":"<path>","draft_tensor_parallel_size":1,"num_speculative_tokens":2}`.
- MTP (Qwen3.x recipe): `{"method":"mtp","num_speculative_tokens":1}` for quantized; `2` for BF16.
- Code/agent SWE-bench saw 19.4% cost-per-1M-tokens reduction with spec decode.
- Known Qwen3 bug: ngram default `prompt_lookup_min=2` corrupts tool-call output → set `prompt_lookup_min=8`.

## Structured output (`--structured-outputs-config.backend`)
- Backends: `auto` (default), `xgrammar`, `guidance`, `outlines`, `lm-format-enforcer`.
- v0.21 ships XGrammar 0.2.0 — structural tags for strict tool calling + reasoning combined.
- Request fields: `choice`, `regex`, `json` (JSON Schema), `grammar` (EBNF), `structural_tag`.
- Deprecated `guided_*` fields removed in v0.12.0; use unified `structured_outputs={…}`.
- XGrammar wins on long generations / reused grammars thanks to caching.

## Multi-LoRA serving (`--enable-lora`)
- Required co-flags: `--max-loras N`, `--max-lora-rank R` (set to max rank in your adapters), `--max-cpu-loras M`, optional `--lora-target-modules`.
- Boot-time registration: `--lora-modules name=path` or JSON form.
- Dynamic add/remove: set env `VLLM_ALLOW_RUNTIME_LORA_UPDATING=True`, then `POST /v1/load_lora_adapter` / `POST /v1/unload_lora_adapter`.
- v0.21 adds initial expert-parallel LoRA support and a Qwen3.5 LoRA fusion fix.

## KV cache quantization (`--kv-cache-dtype`)
- Options: `auto` (default), `fp8`, `fp8_e4m3`, `fp8_e5m2`.
- **Architecture support** (CRITICAL for A6000):
  - Hopper / Ada / Blackwell / MI300: full FP8 (both e4m3 and e5m2). Recommended.
  - Ampere (A100, A6000, RTX 3090): community/triton can run `fp8_e5m2`; some report silent corruption with default scales; `fp8_e4m3` may fail with Inductor codegen errors. **Considered unsafe / unsupported officially on Ampere.**
- v0.21 FP8 KV cache blog (2026-04-22): on H100, ITL slope drops to ≈54% of BF16; 14.9% higher throughput; ≤2-point accuracy loss; break-even ≈7K tokens.
- `--kv-cache-dtype-skip-layers` for hybrid (e.g., keep small SWA layers BF16).
- INT8 KV cache is a feature request (#33480), not yet shipped.

## Tool calling
- Pair `--enable-auto-tool-choice` with `--tool-call-parser <name>`.
- Parsers (v0.21): `hermes`, `mistral`, `llama3_json`, `llama4_pythonic`, `granite`, `granite4`, `granite-20b-fc`, `internlm`, `jamba`, `xlam`, `minimax`, `deepseek_v3`, `deepseek_v31`, `openai`, `kimi_k2`, `hunyuan_a13b`, `cohere_command3`, `longcat`, `glm45`, `glm47`, `functiongemma`, `qwen3_xml`, `olmo3`, `gigachat3`, `pythonic`.
- **Qwen mapping**:
  - Qwen2.5 / QwQ-32B / standard Qwen3 dense → `hermes` (their tokenizer template emits `<tool_call>` tags natively).
  - Qwen3-Coder series → `qwen3_xml` (formerly named `qwen3_coder`) — XML `<tools>` format.
- `tool_choice="required"` (vLLM ≥0.8.3) is the only mode with strict schema enforcement; `auto` lacks it.
- Combine with `--reasoning-parser qwen3` (for Qwen3.x) or `deepseek_r1` (DeepSeek) to extract thinking into a separate `reasoning_content` field. Note: reasoning + tool calling on Qwen3 has had bugs (e.g., #19513) — confirm in your version.

## Hardware: Qwen 3.6-27B on 2× A6000 (96 GB total)
- BF16 weights: ~55 GB → fits across 2× A6000 with `--tensor-parallel-size 2`.
- Native context: 262,144 tokens; YaRN scaling can extend to 1M.
- Per-GPU after weights: ~48 − 27.5 = ~20 GB; with `--gpu-memory-utilization 0.92`, leaves ~14–17 GB per GPU for KV.
- KV at BF16 for Qwen3.6-27B (~64 layers, GQA): roughly 0.25–0.4 MB/token → 32K context ≈ 8–13 GB total KV. 64K is the tight ceiling for BF16 KV on this hardware.
- A6000 is Ampere → **FP8 KV cache is officially unsupported**; do not set `--kv-cache-dtype fp8*` for production. Stick with `auto` (BF16 KV).
- Other knobs that ship in the proven dual-GPU Qwen3.6-27B configs: `--enable-prefix-caching`, `--enable-chunked-prefill`, `--max-num-batched-tokens 4096–16384`, `--max-num-seqs 2–4`, `--block-size 16` (for hybrid Mamba/attention layers), `--disable-custom-all-reduce` on PCIe-only links.

## Recommended `vllm serve` (text-only coding agent, 32K–64K context)
```bash
vllm serve Qwen/Qwen3.6-27B \
  --tensor-parallel-size 2 \
  --max-model-len 65536 \
  --dtype bfloat16 \
  --gpu-memory-utilization 0.92 \
  --max-num-seqs 4 \
  --max-num-batched-tokens 8192 \
  --enable-prefix-caching \
  --reasoning-parser qwen3 \
  --enable-auto-tool-choice \
  --tool-call-parser hermes \
  --speculative-config '{"method":"ngram","num_speculative_tokens":4,"prompt_lookup_max":4,"prompt_lookup_min":8}' \
  --port 8000
```

Use `--max-model-len 32768` for safety headroom; bump to 65536 once memory profile is verified.

## Gotchas / open questions
- `--kv-cache-dtype fp8_e5m2` on A6000: may silently corrupt outputs on Qwen-VL family; unverified for Qwen3.6-27B text. **Do not use without dedicated A/B regression test.**
- ngram spec decode with `prompt_lookup_min=2` corrupts tool calls on Qwen3 (issue #40875) — must override to 8.
- Reasoning parser + tool calling on Qwen3 has historical bugs; verify on v0.21.0 before committing.
- NVLink between dual A6000 → keep custom all-reduce ENABLED (good); on PCIe-only setups, add `--disable-custom-all-reduce`.
