# B1: vLLM 2026 Features Deep-Dive

Research date: 2026-05-18. Author: Claude research agent. For: Math/Stat 361 coding-agent capstone, advisor Prof. Andrew Leahy. Target serving stack: vLLM serving Qwen 3.6-27B BF16, `--tensor-parallel-size 2`, 2× NVIDIA RTX A6000 (Ampere, 48 GB each, NVLink 112 GB/s, 96 GB combined).

## TL;DR

vLLM **v0.21.0** (released 2026-05-15) is the current stable. The V1 engine is the default and already turns on the two biggest free-lunches: **prefix caching** and **chunked prefill**. For a Qwen 3.6-27B BF16 deployment on 2× A6000, the recommended `vllm serve` enables prefix caching, tensor parallelism, ngram speculative decoding tuned to avoid the known Qwen tool-call bug, the `hermes` tool parser, and the `qwen3` reasoning parser; it caps `--max-model-len` at 32K–64K to leave KV headroom because A6000 is Ampere and therefore cannot safely use FP8 KV cache. KV cache quantization, the obvious next memory win, is hardware-gated to Ada/Hopper/Blackwell — **using `--kv-cache-dtype fp8*` on A6000 is unsupported and known to silently corrupt outputs on some models.** Stick to BF16 KV.

## Why this matters

Our coding agent's value depends on (a) latency to first token when the user asks a question, (b) throughput when the agent loops through tool calls and partial files, and (c) the ability to keep a long working context — repo snippets, scratchpad, tool outputs — without rebuilding state every turn. vLLM's 2026 V1 engine reshapes all three:

- Prefix caching turns multi-turn agent loops from "re-prefill the whole conversation each step" into "re-use everything up to the new tail." For an agent that does 5–20 LLM calls per user query, this is the single largest source of free latency improvement.
- Chunked prefill lets long context (`<file>...</file>` blobs) interleave with decode of other in-flight requests, so prefill-blocking no longer stalls everything.
- Structured output and tool-calling parsers eliminate brittle regex parsing in our scaffold and give us deterministic JSON for the OpenAI SDK client we already use.
- Speculative decoding (especially ngram) gives 1.2–2× decode speedup at near-zero extra VRAM, which matters when we're running BF16 weights with limited KV headroom.

These choices have to fit Ampere hardware. The cleanest research finding here is the negative one: **FP8 KV cache, the most widely-promoted vLLM perf knob in 2026, does not work on A6000.** Knowing that ahead of time saves a day of debugging.

## State of the art (2026)

### Release timeline (verified on PyPI)

| Version | Date | Highlights |
|---|---|---|
| v0.18.0 | 2026-03-20 | gRPC serving (`--grpc`), GPU NGram spec decode, FlexKV KV-offload backend |
| v0.19.0 | 2026-04-03 | Day-0 Gemma 4 support, async scheduler ON by default, Model Runner V2 |
| v0.20.0 | 2026-04-27 | Maturation of MRv2; multimodal embeddings; ViT full CUDA graphs |
| v0.20.2 | 2026-05-10 | Patch |
| **v0.21.0** | **2026-05-15** | **Stable. KV-Offload + Hybrid Memory Allocator. Spec decode respects thinking budgets. XGrammar 0.2.0. Initial expert-parallel LoRA. C++20 build requirement. Transformers v4 deprecated.** |

### Engine defaults that already exist in V1
- Prefix caching: **on by default**, hash algo `sha256` since v0.11. <1% throughput cost at 0% hit rate.
- Chunked prefill: **always on in V1**; CLI flag is a no-op for disabling.
- Async scheduler: **on by default** since v0.19 (zero-bubble scheduling with spec decode support).

### Prefix caching deep dive
- Block-level KV reuse with LRU eviction.
- Hash hierarchy: `parent_block_hash → block_tokens → extras (LoRA id, image hash, salt)`.
- Hash algo options: `sha256` (default), `sha256_cbor` (reproducible cross-version), `xxhash`/`xxhash_cbor` (faster, non-crypto), `builtin` (legacy).
- Per-request `cache_salt` for multi-tenant prefix isolation — relevant if our agent later serves multiple users with different system prompts.
- Best workloads: shared system prompt + few-shot demos, multi-turn chat, repeated RAG over the same docs.

### Chunked prefill knobs
- Tune `--max-num-batched-tokens`:
  - 2048 — best inter-token latency (single-user interactive).
  - 8192–16384 — best throughput / TTFT under concurrency. Recommended ≥ 8192 on large GPUs.
- Must exceed `max_model_len` when chunked prefill is *off* (irrelevant on V1).

### Speculative decoding
- Methods supported: `ngram`, `eagle`, `eagle3`, `medusa`, `mlpspeculator`, `mtp` (Qwen3.x multi-token prediction).
- v0.21 additions: respects reasoning/thinking budgets (so reasoning models don't burn spec budget on hidden chain-of-thought); independent drafter attention backend; multimodal model warning.
- N-gram is "free" — no extra weights:
  ```json
  {"method": "ngram", "num_speculative_tokens": 5, "prompt_lookup_max": 4, "prompt_lookup_min": 8}
  ```
- EAGLE / EAGLE3 require a separately trained head; `draft_tensor_parallel_size: 1` always.
- MTP is Qwen3.x-native. Recipe page recommends `num_speculative_tokens: 2` BF16, `1` quantized.
- **Known critical bug (vLLM #40875):** with Qwen3 + structured output, the default `prompt_lookup_min=2` corrupts tool-call output. **Override to 8.**
- SWE-bench code workloads show ~19.4% cost-per-1M-token reduction with spec decode enabled.

### Structured output (guided JSON, regex, grammar)
- Backends: `auto` (default selector), `xgrammar`, `guidance`, `outlines`, `lm-format-enforcer`.
- v0.21 ships **XGrammar 0.2.0**, adding structural tags so strict tool-calling and reasoning can coexist in a single grammar.
- Request fields: `choice`, `regex`, `json` (JSON Schema), `grammar` (EBNF), `structural_tag`.
- Legacy `guided_json`, `guided_regex`, etc. were removed in v0.12.0 — use the unified `structured_outputs={…}` block.
- XGrammar is the right default for our agent: low time-per-output-token, near-zero overhead vs unconstrained, and effective caching for repeated grammars (e.g., the same tool schema across many calls).

### Multi-LoRA serving
- Required flags: `--enable-lora`, `--max-loras N` (concurrency cap), `--max-lora-rank R`, `--max-cpu-loras M`, optional `--lora-target-modules`.
- Boot-time registration: `--lora-modules name=path/to/adapter` (multi-arg or JSON form).
- Runtime add/remove: set env `VLLM_ALLOW_RUNTIME_LORA_UPDATING=True`, then `POST /v1/load_lora_adapter` and `POST /v1/unload_lora_adapter`.
- v0.21: initial expert-parallel LoRA support; Qwen3.5 LoRA fusion fix.
- For this capstone we're not using LoRAs — base Qwen 3.6-27B is sufficient — but the path is open if we want a project-specific adapter.

### KV cache quantization — the Ampere catch
- Options: `--kv-cache-dtype {auto, fp8, fp8_e4m3, fp8_e5m2}`.
- The vLLM 2026-04-22 official blog ("The State of FP8 KV-Cache and Attention Quantization in vLLM") quantifies the win **on Hopper / Blackwell only**:
  - 14.9% higher throughput, ITL slope reduced to ~54% of BF16, ≤1–2 point accuracy hit, break-even ≈7K tokens.
- **A6000 is Ampere (SM 8.6)** — vLLM forum and bug tracker agree:
  - `fp8_e4m3` fails with Inductor codegen `ValueError` on Ampere — hardware limitation.
  - `fp8_e5m2` *can* technically run via Triton on SM 8.6 but multiple recent reports describe **silent output corruption** with default scaling (issue #41343 on Qwen-VL). The vLLM forum staff response is unambiguous: "FP8 KV cache is only supported on newer architectures (Hopper, Ada, H100, RTX 4090/6000 Ada) and AMD MI300, not on Ampere GPUs."
- INT8 KV cache is a 2026 feature request (#33480) — not shipped.
- **Decision: keep `--kv-cache-dtype auto` (= BF16 KV) on A6000. Do not chase FP8 KV.**

### Tool calling
- Two flags: `--enable-auto-tool-choice` + `--tool-call-parser <name>`. Optional `--chat-template <path>` if your model's tokenizer doesn't ship a tool template.
- v0.21 parser set (24 supported): `hermes`, `mistral`, `llama3_json`, `llama4_pythonic`, `granite`, `granite4`, `granite-20b-fc`, `internlm`, `jamba`, `xlam`, `minimax`, `deepseek_v3`, `deepseek_v31`, `openai`, `kimi_k2`, `hunyuan_a13b`, `cohere_command3`, `longcat`, `glm45`, `glm47`, `functiongemma`, `qwen3_xml`, `olmo3`, `gigachat3`, `pythonic`.
- For **standard Qwen 3 / Qwen 3.6 dense models (not Coder)** the tokenizer chat template emits Hermes-style `<tool_call>…</tool_call>` tags — use `--tool-call-parser hermes`.
- For Qwen3-Coder use `--tool-call-parser qwen3_xml` (XML `<tools>` block format).
- `tool_choice="required"` (vLLM ≥0.8.3) is the only mode that strictly enforces the tool schema; `auto` does not.
- Pair with `--reasoning-parser qwen3` to route the model's `<think>...</think>` content into a separate `reasoning_content` field on the response, so your agent loop sees only the user-visible content.

## Most widely used (in real-world 2026 deployments)

Reviewing public dual-GPU Qwen 3.6-27B deployments (LLMKube bake-off, derekarmstrong.dev, dzombak.com Docker-compose), the consensus flag set is:

- `--tensor-parallel-size 2` — required to fit BF16 weights across two cards.
- `--enable-prefix-caching` — kept on explicitly even though V1 defaults it on, for clarity.
- `--enable-chunked-prefill` + `--max-num-batched-tokens 4096–16384`.
- `--reasoning-parser qwen3` + `--enable-auto-tool-choice` + `--tool-call-parser hermes` (or `qwen3_xml` for Coder variant).
- `--gpu-memory-utilization 0.85–0.98` (consumer 24 GB rigs push 0.98; we should run lower for safety).
- Speculative decoding via `--speculative-config '{"method":"mtp","num_speculative_tokens":1-2}'` on production rigs with FP8 KV. We will use **ngram** instead because we cannot run FP8 KV and ngram has zero weight overhead.
- Two of the three reference deployments do use `--kv-cache-dtype fp8`, but **only on Ada/Blackwell hardware**, not Ampere — confirming that for A6000 we omit it.

## Comparison table — features vs A6000 viability

| Feature | Flag | Default in V1 | Works on A6000 | Recommended for our agent |
|---|---|---|---|---|
| Prefix caching | `--enable-prefix-caching` | ON | Yes | YES, keep explicit |
| Chunked prefill | (always on V1) | ON | Yes | YES |
| Async scheduler | (env / default) | ON since 0.19 | Yes | YES |
| Spec decode (ngram) | `--speculative-config` | OFF | Yes | YES, with `prompt_lookup_min=8` |
| Spec decode (EAGLE3) | `--speculative-config` | OFF | Yes | Maybe — extra weights, not worth complexity now |
| Spec decode (MTP) | `--speculative-config` | OFF | Yes (Qwen3.x supports it) | Optional alternative to ngram |
| Structured output (XGrammar) | `--structured-outputs-config.backend xgrammar` | `auto` selects | Yes | YES for JSON tool args |
| Tool calling | `--enable-auto-tool-choice` + `--tool-call-parser hermes` | OFF | Yes | YES |
| Reasoning parser | `--reasoning-parser qwen3` | OFF | Yes | YES |
| Multi-LoRA | `--enable-lora` | OFF | Yes | NO for capstone (no adapters) |
| FP8 KV cache | `--kv-cache-dtype fp8` | OFF | **NO — Ampere unsupported** | NO |
| FP8 weight quant (W8A8) | model checkpoint | n/a | Limited (W8A16 only, via Marlin) | NO — we have enough VRAM for BF16 |
| gRPC serving | `--grpc` | OFF | Yes | NO — keep OpenAI HTTP API |
| `--api-server-count N` | (scaling tokenizer) | 1 | Yes | NO until we hit tokenizer bottleneck |

## Feature-by-feature deep dive (continued)

### Engine internals worth knowing for the demo
The V1 engine introduced piecewise CUDA graph compilation (`-O2` default, which is currently equivalent to `-O3`). Cold start on Qwen 3.6-27B will spend ~50 seconds in torch.compile and another ~80 seconds in prefill profiling before CUDA graph capture — plan for a ~4 minute server warmup before the demo. After warm-up, CUDA graphs make per-step decode near deterministic in latency.

Preemption mode in V1 defaults to `RECOMPUTE` (drop and re-prefill a request when KV pressure spikes) rather than `SWAP` (move KV to CPU). RECOMPUTE has lower overhead but means a preempted request will re-pay its prefill cost. Keep `--max-num-seqs` low (≤4 for the demo) to avoid triggering preemption at all.

### Memory accounting for our hardware
Per-A6000 budget at `--gpu-memory-utilization 0.92`: 44.16 GB usable. Qwen 3.6-27B BF16 weights sharded TP=2: ~27.5 GB per card. That leaves ~16 GB per card after weights, of which CUDA graphs / activations take a few GB and the rest (~12–14 GB) is KV cache. At a conservative ~0.4 MB/token KV (BF16), 32K context across 4 concurrent sequences needs ~13 GB per card — tight but viable. Going to 64K context at the same concurrency would need ~26 GB per card, infeasible — so 64K context requires reducing `--max-num-seqs` to 2.

### When to consider FP8 weight quantization (not just KV)
Distinct from KV-cache quantization, vLLM also supports `--quantization fp8` for model weights. On Ampere this falls back to W8A16 with Marlin kernels (weight-only, BF16 activations) — supported but lower performance ceiling than native W8A8. For Qwen 3.6-27B BF16 weights at ~55 GB, going to FP8 weights would free ~27 GB total VRAM, which would let us scale `--max-num-seqs` higher or stretch context to 64K. Trade-off: small accuracy hit (1–2 points typically) plus added complexity. **Defer until after demo;** BF16 baseline first.

### Async scheduler / zero-bubble scheduling
Since v0.19 (April 2026), the async scheduler is on by default. It overlaps scheduling decisions with model execution, recovering the per-step gap that earlier vLLM versions had between batches. Combined with spec decode, this is "zero-bubble" scheduling and is meaningfully faster than v0.18. No flag required.

### Observability and benchmarking
vLLM ships a benchmark CLI: `vllm bench`. Useful subcommands:
- `vllm bench latency` — pure decode latency per token across batch sizes.
- `vllm bench throughput` — multi-request throughput.
- `vllm bench serve` — round-trip OpenAI-API benchmark against a running server.

Prometheus metrics at `/metrics`. Key ones to watch on our deployment:
- `vllm:num_requests_waiting` — if non-zero steady-state, we're queueing → raise concurrency or reduce context.
- `vllm:gpu_cache_usage_perc` — KV cache utilization. If consistently >0.9, expect preemptions.
- `vllm:spec_decode_draft_acceptance_rate` — for ngram spec decode, aim above 0.55; below that, disable.
- `vllm:prefix_cache_hits` / `vllm:prefix_cache_queries` — hit rate ≥0.5 is a normal target for agent loops.

## Recommendation

Stay on **vLLM v0.21.0** with V1 engine defaults. Adopt the seven flags below explicitly so the team can reason about them line-by-line for the demo. Skip FP8 KV cache (Ampere). Skip LoRAs (not needed). Use ngram spec decode with the `prompt_lookup_min=8` fix.

`--max-model-len 32768` is the safe initial choice; once we've measured KV usage we can extend to 65536. The 262K native context Qwen advertises is not realistic on 2× 48 GB.

## Concrete next steps — the actual `vllm serve` command

Verify the install:
```bash
cd /home/tle/code/coding-agent
uv pip install 'vllm==0.21.0'
python -c "import vllm; print(vllm.__version__)"
```

Launch (Phase 1, conservative 32K context):
```bash
vllm serve Qwen/Qwen3.6-27B \
  --tensor-parallel-size 2 \
  --max-model-len 32768 \
  --dtype bfloat16 \
  --gpu-memory-utilization 0.92 \
  --max-num-seqs 4 \
  --max-num-batched-tokens 8192 \
  --enable-prefix-caching \
  --reasoning-parser qwen3 \
  --enable-auto-tool-choice \
  --tool-call-parser hermes \
  --speculative-config '{"method":"ngram","num_speculative_tokens":4,"prompt_lookup_max":4,"prompt_lookup_min":8}' \
  --host 0.0.0.0 \
  --port 8000
```

Why each flag:
- `--tensor-parallel-size 2` — model weights split across both A6000s over NVLink.
- `--max-model-len 32768` — leaves ~14 GB/GPU for KV after BF16 weights at 0.92 utilization. Bump to 65536 once measured.
- `--dtype bfloat16` — explicit; matches A6000 native compute.
- `--gpu-memory-utilization 0.92` — headroom for activations, CUDA graphs, fragmentation. Push to 0.95 only after stability proven.
- `--max-num-seqs 4` — 4 concurrent requests is plenty for a demo and keeps per-request KV high.
- `--max-num-batched-tokens 8192` — balanced TTFT/throughput.
- `--enable-prefix-caching` — explicit even though V1 default; required for any agent loop that resends conversation history.
- `--reasoning-parser qwen3` — routes `<think>…</think>` into `reasoning_content` so our scaffold sees clean assistant text.
- `--enable-auto-tool-choice --tool-call-parser hermes` — turns model's Hermes-style tags into OpenAI-format `tool_calls` arrays.
- `--speculative-config '{…ngram…}'` — free decode speedup, with the `prompt_lookup_min=8` override that avoids the Qwen3 tool-call corruption bug.

Phase 2 (after measurement), expand:
- `--max-model-len 65536` if free KV ≥ 12 GB/GPU at steady-state.
- Consider switching speculative method to `mtp` if Qwen3.6-27B's MTP head benchmark beats ngram on our workload.
- Add `--structured-outputs-config.backend xgrammar` if `auto` ever picks a slower backend.

What to **not** do:
- Don't add `--kv-cache-dtype fp8*` (Ampere).
- Don't add `--quantization fp8*` for the model weights (not needed; risks W8A8 incompatibility on Ampere).
- Don't add `--enforce-eager` unless debugging — costs ~10–15% throughput.
- Don't enable `tool_choice="auto"` if downstream code expects a schema — use `"required"`.

Sanity test once running:
```bash
curl -s http://localhost:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "Qwen/Qwen3.6-27B",
    "messages": [{"role":"user","content":"List 3 prime numbers as JSON {\"primes\":[...]}."}],
    "response_format": {"type":"json_object"},
    "max_tokens": 64
  }'
```

## Open questions

1. **MTP vs ngram speedup on our specific workload.** Public numbers favor MTP for Qwen3.x, but ngram is simpler and avoids spec head latency. Benchmark both on our agent traces once we have ~50 representative prompts.
2. **Stability of `--reasoning-parser qwen3` + `--tool-call-parser hermes` together on v0.21.** Multiple 2025 GitHub issues reported this combo breaking; v0.21 changelog claims it works but we should regression-test before demo day.
3. **YaRN-extended context.** The recipe page hints at 524K and 1M via YaRN, but we have no VRAM for it — skip unless we move to FP8 hardware.
4. **Effective TTFT / throughput on 2× A6000 NVLink.** No published numbers exactly match our hardware. The Derek Armstrong dual-3090 benchmark (~120 tok/s combined at TP2) is a reasonable lower bound; A6000 is slightly faster per-GPU.
5. **Whether to enable `xxhash_cbor` prefix hash for reproducibility across vLLM upgrades.** Default `sha256` is fine for the demo; only matters if we share KV cache snapshots.

## Sources

- [vLLM PyPI release listing](https://pypi.org/project/vllm/) — 2026-05-18 — confirmed v0.21.0 released 2026-05-15; release dates for v0.18 through v0.21.
- [vLLM GitHub releases (v0.21.0 tag)](https://github.com/vllm-project/vllm/releases/tag/v0.21.0) — 2026-05-18 — v0.21 feature list: KV offload + HMA, spec decode thinking budgets, TOKENSPEED_MLA, XGrammar 0.2.0, EP LoRA, C++20 requirement, Transformers v4 deprecation.
- [Automatic Prefix Caching (vLLM docs)](https://docs.vllm.ai/en/stable/design/prefix_caching/) — 2026-05-18 — hash algos, block-level eviction, default `sha256` since v0.11.
- [vLLM V1 user guide / blog](https://news.ycombinator.com/item?id=44405139) — 2026-05-18 — prefix caching on by default in V1 with <1% throughput hit.
- [Optimization and Tuning (vLLM stable docs)](https://docs.vllm.ai/en/stable/configuration/optimization/) — 2026-05-18 — chunked prefill always on in V1; `max_num_batched_tokens` tuning rules; preemption defaults.
- [Speculative Decoding (vLLM latest docs)](https://docs.vllm.ai/en/latest/features/speculative_decoding/) — 2026-05-18 — supported methods, JSON configs, EAGLE / ngram / MTP.
- [N-Gram Speculation (vLLM)](https://docs.vllm.ai/en/latest/features/speculative_decoding/n_gram/) — 2026-05-18 — `prompt_lookup_max`, `num_speculative_tokens` syntax.
- [Issue #40875 — ngram prompt_lookup_min corrupts Qwen3 tool calls](https://github.com/vllm-project/vllm/issues/40875) — 2026-05-18 — fix is `prompt_lookup_min=8`.
- [Structured Outputs (vLLM)](https://docs.vllm.ai/en/latest/features/structured_outputs/) — 2026-05-18 — XGrammar 0.2.0, backends, deprecated `guided_*` fields, `structural_tag`.
- [LoRA Adapters (vLLM stable)](https://docs.vllm.ai/en/stable/features/lora/) — 2026-05-18 — `--enable-lora`, `--max-loras`, `--max-lora-rank`, runtime add/remove API.
- [Tool Calling (vLLM stable)](https://docs.vllm.ai/en/stable/features/tool_calling/) — 2026-05-18 — full parser list including `qwen3_xml`, `hermes`, Qwen2.5/QwQ recommended `hermes`.
- [Quantized KV Cache (vLLM)](https://docs.vllm.ai/en/latest/features/quantization/quantized_kvcache/) — 2026-05-18 — `--kv-cache-dtype` options, calibration methods, `--kv-cache-dtype-skip-layers`.
- [The State of FP8 KV-Cache and Attention Quantization in vLLM (official blog)](https://vllm.ai/blog/2026-04-22-fp8-kvcache) — 2026-04-22 — 14.9% throughput gain, 54% ITL slope, ≤2-point accuracy hit; Hopper/Blackwell focus.
- [vLLM Forum: KV Cache quantizing? — staff reply](https://discuss.vllm.ai/t/kv-cache-quantizing/749) — 2026-05-18 — explicit statement: FP8 KV not supported on Ampere; supported on Hopper/Ada/MI300.
- [Issue #41343 — fp8_e5m2 silently corrupts Qwen-VL outputs](https://github.com/vllm-project/vllm/issues/41343) — 2026-05-18 — workaround `calculate_kv_scales=True`; documents Ampere instability.
- [Issue #33480 — Add INT8 KV cache support request](https://github.com/vllm-project/vllm/issues/33480) — 2026-05-18 — confirms INT8 is not shipped as of v0.21.
- [Qwen 3.6-27B vLLM recipe](https://recipes.vllm.ai/Qwen/Qwen3.6-27B) — 2026-05-18 — BF16 fits 1× H200 or 2× H100; native 262K context; recommends `--reasoning-parser qwen3`, optional `--language-model-only`, `--enable-prefix-caching`, MTP spec config.
- [Qwen3.5 & Qwen3.6 vLLM Usage Guide](https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3.5.html) — 2026-05-18 — recommended flags incl. `--speculative-config '{"method":"mtp","num_speculative_tokens":1-2}'`.
- [Qwen vLLM deployment docs (qwen.readthedocs.io)](https://qwen.readthedocs.io/en/latest/deployment/vllm.html) — 2026-05-18 — canonical example: `vllm serve … --reasoning-parser qwen3 --enable-auto-tool-choice --tool-call-parser hermes`.
- [Derek Armstrong: Running Qwen 3.6 27B on dual RTX 3090s with vLLM 0.19](https://derekarmstrong.dev/blog/running-qwen36-27b-dual-rtx-3090-vllm-v019/) — 2026-04 — real-world flag set, 160K context with FP8 KV (Ampere 3090 — but author uses FP8 anyway; demonstrates risk); MTP spec config; `--disable-custom-all-reduce` for PCIe.
- [Dzombak: vLLM Docker Compose for Qwen 3.6 27B on dual 3090s](https://www.dzombak.com/blog/2026/04/a-vllm-docker-compose-recipe-for-running-qwen-3-6-27b-on-dual-rtx-3090s-opencode-configuration/) — 2026-04 — full command including `--tool-call-parser qwen3_coder` and `--reasoning-parser qwen3`.
- [LLMKube: Qwen 3.6-27B bake-off](https://llmkube.com/blog/qwen3-6-27b-bakeoff) — 2026-05 — consumer-GPU benchmark; 16K context required by VRAM; TP=2; throughput numbers; `--enforce-eager` cost.
- [Red Hat: Speculative decoding performance improvements for gpt-oss in vLLM](https://developers.redhat.com/articles/2026/04/16/performance-improvements-speculative-decoding-vllm-gpt-oss) — 2026-04-16 — SWE-bench 19.4% cost reduction; ngram acceptance characteristics.
- [vLLM Production Deployment Complete 2026 Guide (SitePoint)](https://www.sitepoint.com/vllm-production-deployment-guide-2026/) — 2026 — third-party tuning recipes; corroborates flag set.
- [Knightli: Qwen 3.6 VRAM table](https://www.knightli.com/en/2026/05/01/qwen3-6-local-vram-quantization-table/) — 2026-05-01 — BF16 GGUF 53.8 GB; min/safe VRAM per quant level.

Sources marked [UNVERIFIED] where the claim couldn't be triple-confirmed:
- [UNVERIFIED] Exact tok/s number for 2× A6000 BF16 — extrapolated from dual-3090 (Derek Armstrong) and 4× A6000 (DatabaseMart) benchmarks; not measured directly.
- [UNVERIFIED] Qwen 3.6-27B layer/head dimensions used in KV-per-token estimate — used 64-layer GQA assumption from Qwen3.x family; not directly cited from a Qwen 3.6-27B-specific config card in this research pass.
