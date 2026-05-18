# B2: vLLM vs SGLang vs TensorRT-LLM in 2026 — when to choose which

Research date: 2026-05-18. Author: Claude research agent. For: Math/Stat 361 coding-agent capstone, advisor Prof. Andrew Leahy. Target serving stack: Qwen 3.6-27B BF16, tensor-parallel=2, 2× NVIDIA RTX A6000 (Ampere SM86, 48 GB each, NVLink 112 GB/s, 96 GB combined). Sibling report: B1 covers vLLM 2026 features in depth; this one positions vLLM against its two main rivals.

## TL;DR

For our 2× A6000 + Qwen 3.6-27B + coding-agent workload, **vLLM remains the right choice in 2026**, with SGLang as the credible Plan B if our agent loops generate large shared-prefix traffic and we are willing to absorb a smaller ecosystem. **TensorRT-LLM is the wrong choice for us**, for three independent reasons: (1) FP8, NVFP4 and most of its headline perf wins are gated to Hopper/Blackwell — Ampere SM86 cannot use them; (2) Qwen 3.6-27B with its dense Gated DeltaNet hybrid is not in the official support matrix (Qwen3-Next is beta; Qwen3.6 dense is not listed); (3) the 28-minute compile-per-config workflow is operationally hostile to a capstone where we iterate on serving config weekly. vLLM is the fastest path to a working OpenAI-compatible endpoint with full Qwen 3.6 Gated-DeltaNet kernels (v0.19+), full tool-call and reasoning parsers, and a recipe page we can copy. The realistic Plan-B switch to SGLang is one base-URL change in the OpenAI client; we should keep that option open. [UNVERIFIED] in this report flags claims I could not confirm in a primary source within the research window.

## Why this matters

Our coding agent makes 5–20 LLM calls per user query (planner, file-reader, editor, runner, reflector). Three engine properties dominate end-user experience:

1. **Throughput at moderate concurrency** — when the agent fans out tool calls in parallel, or when a teammate joins on the same server.
2. **Time-to-first-token (TTFT)** — visible whenever the user types and waits.
3. **Prefix-cache hit rate** — every multi-turn agent step re-sends the same system prompt, file context, and tool-schema; if KV state is recomputed each step we pay 4–10× more than we should.

The engine choice also gates non-perf properties we care about for a capstone:

- **Does it run Qwen 3.6's hybrid Gated DeltaNet kernels at all?** This is a hard yes/no, not a perf delta.
- **Can the owner read every line of how it works?** vLLM and SGLang are open Python+CUDA; TensorRT-LLM has closed kernel internals.
- **How fast can we iterate?** Capstone time budget is finite; a 28-minute compile-on-config-change wrecks the OODA loop.

A wrong choice here costs us either weeks of debugging (TensorRT-LLM on Ampere with unsupported model) or a sub-optimal 30% throughput hit (vLLM on an extreme prefix-heavy workload that SGLang would handle better).

## State of the art (2026)

### Three engines, three different theories

**vLLM** (v0.21.0, 2026-05-15). Best general-purpose open LLM server. V1 engine default, prefix caching on by default, chunked prefill always on, async scheduler, OpenAI server, broad tool-call parser catalog, broad quantization support, broad hardware support (NVIDIA Ampere through Blackwell, AMD ROCm, Intel Gaudi, AWS Neuron). Mature speculative decoding pipeline (ngram, EAGLE, EAGLE3, Medusa, MLP, MTP). Backed by an active community across UC Berkeley, RedHat, Anthropic. See B1 for full feature dive.

**SGLang** (v0.5.10+ for Qwen3.6). Pitched as the "structured-generation and prefix-heavy" specialist. Core differentiator is **RadixAttention** — a radix-tree (trie + LRU) of KV state shared across all concurrent requests, no manual prefix declaration. Claim: up to **6.4× throughput on RAG / multi-turn workloads vs naïve KV cache** (LMSYS / arXiv 2312.07104). Second differentiator: **compressed-FSM constrained decoding** — overlaps grammar-mask generation with the forward pass, ~3× faster guided JSON than baseline. Mamba Radix Cache extends RadixAttention to hybrid (Mamba / DeltaNet) models with a V1 (no-buffer) and V2 (extra-buffer + branching-point caching, NVIDIA-only FLA kernel) strategy.

**TensorRT-LLM** (v1.2.1, 2026-04-20). NVIDIA's stack. Closed-source kernels, open Python API. The throughput leader on H100/B200 by 13–30% in most benches, lowest TTFT, but pays for it with (a) a ~28-minute compile per model+precision+TP combination, (b) NVIDIA hardware lock-in, (c) FP8 / NVFP4 wins gated to SM89+ (Ada) and Blackwell respectively, (d) a smaller official model catalog than vLLM. Serving via `trtllm-serve` (OpenAI-compatible REST) or Triton Inference Server (production grid) or in-process LLM API (offline batch). AutoDeploy beta compiles arbitrary PyTorch graphs.

### Throughput benchmarks (H100 SXM5, Llama 3.3 70B FP8, Spheron 2026)

Numbers are output tok/s aggregate, 200 prompts of 512 in / 256 out, async aiohttp client, 60s warmup + 3min steady-state.

| Concurrency | vLLM | SGLang | TensorRT-LLM |
|---|---|---|---|
| 1 | 120 | 125 | 130 |
| 10 | 650 | 680 | 710 |
| 50 | 1,850 | 1,920 | 2,100 |
| 100 | 2,400 | 2,460 | 2,780 |

TRT-LLM leads at every level (8% at conc=1, 13–16% at conc=50–100). Same source: Clarifai bench on GPT-OSS-120B FP8 at conc=100 reports vLLM 4,741 tok/s; SGLang and TRT-LLM not directly comparable in that article. The Yotta production bench (mixed workloads, 70B+) reports the SGLang vs vLLM gap shrinking to 3–5%. **Important caveat: these are all H100, all FP8. None of these benchmarks generalize directly to Ampere A6000 BF16, where FP8 attention is unavailable.**

### Latency (TTFT) — same H100 bench

| Concurrency | vLLM p50 | vLLM p95 | SGLang p50 | SGLang p95 | TRT-LLM p50 | TRT-LLM p95 |
|---|---|---|---|---|---|---|
| 1 | 45 ms | 68 ms | 42 ms | 61 ms | 38 ms | 55 ms |
| 10 | 120 | 195 | 112 | 178 | 105 | 170 |
| 50 | 380 | 720 | 360 | 680 | 340 | 620 |
| 100 | 740 | 1,450 | 710 | 1,380 | 680 | 1,280 |

TRT-LLM ~10% better p95 TTFT at high concurrency. SGLang slightly better than vLLM (more so on shared-prefix workloads, see below).

### Cold start

- vLLM: ~62 s (load weights + warmup CUDA graphs).
- SGLang: ~58 s.
- TensorRT-LLM: **~28 min** for first build of a 70B-class model on H100. Subsequent restarts from a cached engine are fast (seconds). Every config change → recompile.

### Prefix-cache / shared-context workloads

The benchmark gap that matters most for an agent:

- **vLLM**: prefix caching on by default since v0.11, sha256 hashing, block-level LRU, optional per-request `cache_salt`. Works well; we expect 30–60% hit rates on multi-turn agent traffic.
- **SGLang RadixAttention**: radix-tree across *all* concurrent requests, no per-request setup. Reports +29% throughput vs vLLM on Llama-3.1-8B with shared prefixes; up to 6.4× on the original LMSYS RAG benchmark. On agent workloads with reused system prompt + tool schema, this is the most likely place SGLang opens daylight against vLLM.
- **TensorRT-LLM**: also supports prefix caching but its main story is raw throughput, not prefix reuse. No analog to RadixAttention.

### Constrained / structured output (tool calling, JSON schemas)

- **vLLM**: XGrammar (default), Outlines, Guidance, LM-Format-Enforcer. v0.21 ships XGrammar 0.2.0 with structural tags. Tool parsers: `hermes`, `qwen3_coder`, `llama3_json`, `mistral`, more.
- **SGLang**: compressed-FSM, ~3× faster than baseline guided decoding on JSON/regex. Tool parsers: `qwen3_coder`, `llama3_json`, etc. Speculative decoding integrated.
- **TensorRT-LLM**: structured output supported but smaller parser catalog and less battle-tested than the open stacks. [UNVERIFIED] specifics for TRT-LLM's structured-output overhead vs vLLM/SGLang as of 2026.

### Quantization support (relevant to our hardware)

| Format | vLLM | SGLang | TRT-LLM | Ampere A6000 usable? |
|---|---|---|---|---|
| BF16 / FP16 | Yes | Yes | Yes | **Yes** |
| INT8 SmoothQuant | Yes | Yes | Yes | **Yes** |
| INT4 AWQ (Marlin) | Yes | Yes | Yes | **Yes** |
| INT4 GPTQ | Yes | Yes | Yes | **Yes** |
| FP8 W8A8 (weights+activations) | Yes (Hopper+) | Yes (Hopper+ native; Marlin route on Ampere) | Yes (SM89+ only) | **No on A6000** |
| KV-cache FP8 | Yes (Hopper+) | Yes (Hopper+) | Yes (Hopper+) | **No on A6000** |
| KV-cache INT8 | Yes | Yes | Yes | Yes |
| NVFP4 | Limited | Limited | Yes (Blackwell native) | **No on A6000** |

The official TensorRT-LLM support matrix is explicit: "Ampere (SM80, SM86) — FP32, FP16, BF16, INT8, INT4." FP8 not implemented. NVFP4 not implemented. The same restriction in practice applies to vLLM and SGLang FP8 paths on Ampere (Marlin can simulate but loses the perf win).

**Implication:** our 96 GB of A6000 VRAM at BF16 is the binding constraint. Qwen 3.6-27B BF16 weights are ~54 GB; that leaves ~42 GB for KV cache + activations across two cards. That is tight but workable for tensor-parallel=2 at moderate context (~32–64K tokens). If we need more KV headroom we drop to AWQ INT4 (~19 GB weights) and gain ~75 GB for KV.

### Hardware and OpenAI-API compatibility

| Property | vLLM | SGLang | TRT-LLM |
|---|---|---|---|
| NVIDIA Ampere (A6000) | Yes, first-class | Yes, first-class | Yes (BF16/INT8/INT4 only) |
| NVIDIA Hopper / Blackwell | Yes | Yes | Yes (preferred target) |
| AMD ROCm (MI300) | Yes | Yes (Triton path) | No |
| Intel Gaudi | Yes | Limited | No |
| AWS Neuron / Trainium | Yes | Limited | No |
| Apple Silicon | No | No | No |
| `/v1/chat/completions` | Yes | Yes | Yes (`trtllm-serve`) |
| `/v1/completions` | Yes | Yes | Yes |
| `/v1/embeddings` | Yes | Yes | Limited |
| Tool-call parser catalog | Broadest | Broad | Smaller, newer |
| Reasoning parser | `qwen3`, others | `qwen3`, others | `qwen3` (recent) |

For our purpose, all three pass the "drop-in OpenAI SDK base-URL change" test, so swapping engines later is a 1-line edit, not a refactor.

### Multi-GPU and parallelism

- **vLLM**: `--tensor-parallel-size N` (TP), `--pipeline-parallel-size M` (PP). On 2× A6000 with NVLink, TP=2 is the canonical choice; PP=2 is supported but inferior with NVLink available.
- **SGLang**: `--tp N`, `--dp N`, `--ep N` (MoE expert-parallel). Pipeline-parallel less polished. For Qwen 3.6-27B dense, TP=2 is the move.
- **TensorRT-LLM**: TP and PP both supported. *Each* TP/PP combo needs its own compiled engine. So changing from `--tp 2` to `--tp 4` for testing means a fresh 28-minute build.

### Qwen 3.6-27B's Gated DeltaNet support — the load-bearing question

Qwen 3.6-27B is **dense, 27B parameters, 64 transformer layers, hybrid attention**: the repeating rhythm is 3×(Gated DeltaNet → FFN) + 1×(Gated Attention → FFN), so 75% of sub-layers use linear-attention Gated DeltaNet (48 V heads, 16 QK heads), 25% use conventional gated multi-head attention. 262K native context. MTP head for speculative decoding.

| Engine | Qwen 3.6-27B (dense + GDN) | Min version | Kernel approach |
|---|---|---|---|
| vLLM | **Yes** | **>=0.19.0** (recipe page minimum; v0.17 added GDN for Qwen3.5, v0.19 added Qwen3.6) | Triton kernels from Flash Linear Attention; hybrid KV cache manager tunes block sizes so linear-attention state and full-attention KV occupy the same physical memory; full CUDA graph mode on by default to amortize Triton kernel-launch CPU overhead. |
| SGLang | **Yes** | **>=0.5.10** | Mamba Radix Cache with V1 (no_buffer, default) and V2 (extra_buffer + branching-point caching, requires FLA kernel backend, NVIDIA-only). Triton-based `fused_recurrent_gated_delta_rule` kernel reused on ROCm. |
| TensorRT-LLM | **Not in official support matrix** | n/a | Beta Qwen3-Next path exists; Qwen3.6-27B dense Gated-DeltaNet not listed in v1.2.1 support matrix; recent attention/VisualGen runtime fixes referenced in changelog for Qwen3 hybrid models. **[UNVERIFIED]** whether Qwen3.6-27B specifically builds without patches as of 2026-05-18. |

This is the single biggest gating factor for our project. **TensorRT-LLM would require us to either wait for official Qwen 3.6 support or run beta paths designed for Qwen3-Next 80B-A3B (MoE) on our dense 27B model — both bad outcomes for a capstone.**

### Ease of deployment

- **vLLM**: `uv add vllm`, then `vllm serve Qwen/Qwen3.6-27B --tensor-parallel-size 2 ...`. Maybe one OOM-tune pass on `--gpu-memory-utilization` and `--max-model-len`. Time to first token: ~2 minutes from clean machine. Official recipe page at recipes.vllm.ai/Qwen/Qwen3.6-27B copy-pastes.
- **SGLang**: `pip install "sglang[all]>=0.5.10"`, then `python -m sglang.launch_server --model-path Qwen/Qwen3.6-27B --tp 2 --reasoning-parser qwen3 --tool-call-parser qwen3_coder ...`. Time to first token: ~2 minutes.
- **TensorRT-LLM**: install TRT-LLM 1.2.1 + matching CUDA/TRT versions; convert HF weights → TRT-LLM checkpoint (model-specific scripts); run `trtllm-build --tp_size 2 ...` (~28 min); launch with `trtllm-serve`. Time to first token: **30 minutes minimum**, and that assumes Qwen 3.6 build scripts exist.

## Most-used choice in production today

Across the 2026 third-party comparisons (Modal LLM Almanac, Spheron, Yotta Labs, LeetLLM, Particula, LearnOpenCV, Hivenet, Northflank), the rough split for open-weight self-hosted serving is:

1. **vLLM — dominant general-purpose default.** "When in doubt, start with vLLM" is the recurring recommendation. Broadest production install base in 2026.
2. **TensorRT-LLM — large-NVIDIA-fleet specialist.** Used at hyperscale where a model is fixed and throughput-per-dollar dominates. Less common in academic / capstone / startup settings.
3. **SGLang — specialist gaining ground.** xAI, Cursor, OpenAI Codex (sponsorship pool) use it. Strong on chatbots, RAG, agent loops, structured generation. Smaller install base than vLLM but growing fast.

Other engines mentioned in the same comparisons (TGI, llama.cpp, Ollama, LMDeploy) target different use-cases (TGI: HF inside-the-fence, llama.cpp/Ollama: laptop/local, LMDeploy: similar to SGLang). None compete with the three above on a 2× A6000 serving-Qwen-3.6 production deployment.

## Comparison table

| Dimension | vLLM (v0.21) | SGLang (v0.5.10) | TensorRT-LLM (v1.2.1) |
|---|---|---|---|
| Open source | Apache 2.0 | Apache 2.0 | NVIDIA OSL; kernels closed |
| Ampere SM86 (A6000) support | First-class | First-class | Yes but no FP8 / NVFP4 |
| Qwen 3.6-27B (dense + GDN) | Yes, v0.19+ recipe | Yes, v0.5.10+ cookbook | **Not in support matrix** |
| GDN kernel approach | Triton FLA + hybrid KV mgr | Mamba Radix Cache + FLA | Beta hybrid path |
| Tensor parallel for 2× A6000 | `--tensor-parallel-size 2` | `--tp 2` | `--tp_size 2` (recompile per change) |
| BF16 weight footprint of 27B | ~54 GB | ~54 GB | ~54 GB |
| AWQ INT4 footprint | ~19 GB | ~19 GB | ~19 GB |
| Cold start (clean) | ~62 s | ~58 s | **~28 min compile** |
| Throughput H100 70B FP8 conc=100 | 2,400 tok/s | 2,460 tok/s | 2,780 tok/s |
| p95 TTFT H100 70B FP8 conc=100 | 1,450 ms | 1,380 ms | 1,280 ms |
| Prefix-cache mechanism | Block-level LRU, sha256 | RadixAttention (trie + LRU) | Block-level |
| Best shared-prefix gain over vLLM | baseline | +29% (Llama-3.1-8B) to 6.4× (RAG) | smaller |
| Structured output | XGrammar 0.2.0 + 3 others | Compressed FSM (~3× baseline) | Smaller toolset |
| Tool-call parsers | Broadest | Broad | Smaller |
| Speculative decoding | ngram, EAGLE, EAGLE3, Medusa, MLP, MTP | EAGLE, MTP, others | EAGLE-3, MTP |
| OpenAI API | Yes | Yes | Yes (`trtllm-serve`) |
| AMD ROCm | Yes | Yes (Triton) | No |
| Multi-GPU | TP+PP, hot-reload | TP+DP+EP | TP+PP, recompile-per-change |
| Recipe / cookbook for Qwen 3.6 | Yes (recipes.vllm.ai) | Yes (cookbook.sglang.io) | No |
| Operational risk for our project | Low | Low–Medium (newer ecosystem) | **High** (model not officially supported on our hardware) |
| Owner-can-read-every-line | Yes | Yes | Partial (Python yes, CUDA kernels closed) |

## Recommendation for our setup

**Primary: vLLM v0.21.0 with the Qwen 3.6-27B recipe.**

Reasons, in order of importance:

1. **Qwen 3.6-27B with hybrid Gated DeltaNet is officially supported and recipe-documented** in vLLM >=0.19.0. Triton FLA kernels + hybrid KV cache manager are tuned for this model family. No other engine has this combination at recipe-page maturity for our exact model.
2. **Ampere SM86 is a first-class target.** Most 2026 perf knobs that aren't FP8/NVFP4 (prefix caching, chunked prefill, async scheduler, ngram spec decode, XGrammar, hybrid KV cache manager, CUDA graphs) work natively on A6000 with no Marlin-workaround penalty.
3. **OpenAI-SDK drop-in** with full Qwen tool-call (`qwen3_coder`) and reasoning (`qwen3`) parsers — our agent scaffold already uses the OpenAI Python SDK.
4. **Ecosystem and iteration speed.** Cold start is 62 s, not 28 minutes. Reconfiguring `--tensor-parallel-size`, `--max-model-len`, or speculative-decode params is a server restart, not a build.
5. **Owner-can-read-every-line** is meaningfully easier in a Python + Triton kernel stack than in a closed-kernel TensorRT-LLM build.
6. **Risk profile.** A known bug exists for spec-decode + structured output (vLLM #40875) with a known workaround (set `prompt_lookup_min=8`). Known known. Plays well against TRT-LLM's "model not in support matrix" unknown.

**Plan B: SGLang v0.5.10+ if agent traffic ends up dominated by shared prefixes and we measure vLLM's prefix-cache hit rate plateauing under load.** Concretely, if we see vLLM hit-rates above ~70% on system-prompt blocks but throughput still capped by KV-cache churn, RadixAttention's tree-shared structure could open daylight. Switch is one base-URL change.

**Plan C: stay on vLLM but route a separate worker to SGLang for the high-prefix slice.** Overkill for a capstone; revisit only if production scale demands it.

**TensorRT-LLM is not on our path for this project**, because:
- Qwen 3.6-27B is not officially supported (Qwen3-Next is beta, Qwen3.6 dense is absent from the v1.2.1 support matrix).
- We can't use FP8 / NVFP4 on Ampere SM86 anyway — most of its perf differentiator vanishes.
- The compile-per-config workflow is a poor fit for an iteration-heavy capstone.

## Concrete vLLM serve command (target for next sprint)

```bash
vllm serve Qwen/Qwen3.6-27B \
  --tensor-parallel-size 2 \
  --max-model-len 65536 \
  --gpu-memory-utilization 0.92 \
  --reasoning-parser qwen3 \
  --tool-call-parser hermes \
  --enable-auto-tool-choice \
  --speculative-config '{"method":"ngram","num_speculative_tokens":5,"prompt_lookup_max":4,"prompt_lookup_min":8}' \
  --kv-cache-dtype auto \
  --host 0.0.0.0 --port 8000
```

Notes:
- `--kv-cache-dtype auto` (not `fp8*`) — Ampere SM86 cannot use FP8 KV cache; see B1.
- `prompt_lookup_min=8` to avoid vLLM #40875 corruption with Qwen tool calls.
- `--max-model-len 65536` is a starting point that leaves KV headroom on 96 GB BF16. Raise to 128K only after measuring residual VRAM.
- If we hit OOM during prefill, drop to AWQ INT4 (`Qwen/Qwen3.6-27B-AWQ` or the cyankiwi mirror) and raise `--max-model-len` and concurrency.

## Concrete SGLang serve command (Plan B)

```bash
python -m sglang.launch_server \
  --model-path Qwen/Qwen3.6-27B \
  --tp 2 \
  --reasoning-parser qwen3 \
  --tool-call-parser qwen3_coder \
  --mem-fraction-static 0.85 \
  --mamba-scheduler-strategy v1 \
  --host 0.0.0.0 --port 8000
```

Notes:
- `--mamba-scheduler-strategy v2` enables overlap scheduling and branching-point caching but needs FLA kernel; measure whether it pays off before flipping it on.
- Same Qwen tool-call / reasoning parsers as vLLM.

## Next steps

1. Provision vLLM v0.21.0 on the 2× A6000 box and run the command above against `Qwen/Qwen3.6-27B`. Verify boot, OpenAI endpoint, basic chat completion, tool-call round-trip, structured-output round-trip.
2. Run a small bench script (256 prompts, 512 in / 256 out, 4 concurrency levels) on our hardware to get **A6000-native** numbers rather than transposing the H100 benches in this report.
3. Measure prefix-cache hit rate over a typical agent session (5–20 LLM calls per query). If hit rate trends >80% on system-prompt blocks, vLLM is comfortable; if it stalls <50% and throughput is the bottleneck, schedule a one-day SGLang comparison.
4. Keep an OpenAI-SDK client interface in our agent code so the engine swap is a base-URL env var.
5. **Do not** invest engineering time in TensorRT-LLM for this project; revisit only if/when we move to Hopper or Blackwell hardware AND target a stable production model.

## Open questions

1. **[UNVERIFIED] Does Qwen 3.6-27B build cleanly under TensorRT-LLM 1.2.1?** The support matrix lists `Qwen3ForCausalLM` and `Qwen3MoeForCausalLM` but does not enumerate Qwen 3.6 dense + hybrid GDN. Confirming this requires a build attempt or a maintainer statement. Low priority — we're not choosing TRT-LLM regardless.
2. **What is the A6000-native throughput delta between vLLM and SGLang for Qwen 3.6-27B?** All public 2026 benches are H100/H200/B200; Ampere is under-documented. Must bench on our own hardware.
3. **Does SGLang's Mamba Radix Cache V2 (extra_buffer + branching-point caching) help on dense Qwen 3.6 with 75% Gated DeltaNet layers, or is the benefit concentrated in MoE variants?** Worth ~1 day of A/B benching after we have a baseline.
4. **Does vLLM's `cache_salt` per-request feature combine usefully with our agent's per-tool sub-prompts** to maintain a separate trie subtree per tool, or is single-tenant fine? Open until we have a multi-user scenario.
5. **MTP (multi-token prediction) on Qwen 3.6's MTP head — vLLM recipe says `num_speculative_tokens: 2` for BF16. What does that look like on A6000 BF16 with 2× tensor parallel?** Open; expected to be a modest win.

## Sources

Primary / official:
- vLLM official blog "vLLM Now Supports Qwen3-Next: Hybrid Architecture with Extreme Efficiency", 2025-09-11 — https://vllm.ai/blog/2025-09-11-qwen3-next
- vLLM Recipes, Qwen/Qwen3.6-27B — https://recipes.vllm.ai/Qwen/Qwen3.6-27B
- vLLM Recipes, Qwen3.5 & Qwen3.6 usage guide — https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3.5.html
- vLLM v0.19.0 release notes — https://github.com/vllm-project/vllm/releases/tag/v0.19.0
- vLLM v0.21.0 release notes — https://github.com/vllm-project/vllm/releases/tag/v0.21.0
- vLLM quantization docs — https://docs.vllm.ai/en/latest/features/quantization/
- vLLM FP8 W8A8 docs — https://docs.vllm.ai/en/latest/features/quantization/fp8/
- SGLang documentation root — https://sgl-project.github.io/
- SGLang Qwen3.6 cookbook — https://docs.sglang.io/cookbook/autoregressive/Qwen/Qwen3.6
- SGLang Qwen3-Next cookbook — https://docs.sglang.io/cookbook/autoregressive/Qwen/Qwen3-Next
- SGLang Qwen3-Coder-Next cookbook — https://cookbook.sglang.io/autoregressive/Qwen/Qwen3-Coder-Next
- SGLang Qwen3.5 cookbook — https://cookbook.sglang.io/autoregressive/Qwen/Qwen3.5
- SGLang Release 25.11 (NVIDIA NGC) — https://docs.nvidia.com/deeplearning/frameworks/sglang-release-notes/rel-25-11.html
- SGLang issue 12887 (Ampere MoE FP8 W8A8 Marlin) — https://github.com/sgl-project/sglang/issues/12887
- RadixAttention paper, arXiv 2312.07104 — https://arxiv.org/pdf/2312.07104
- TensorRT-LLM docs root — https://nvidia.github.io/TensorRT-LLM/
- TensorRT-LLM support matrix — https://nvidia.github.io/TensorRT-LLM/reference/support-matrix.html
- TensorRT-LLM release notes — https://nvidia.github.io/TensorRT-LLM/release-notes.html
- TensorRT-LLM GitHub — https://github.com/NVIDIA/TensorRT-LLM
- TensorRT-LLM A6000 issue thread — https://github.com/NVIDIA/TensorRT-LLM/issues/1452
- TensorRT-LLM FP8 quantization guide — https://nvidia.github.io/TensorRT-LLM/performance/performance-tuning-guide/fp8-quantization.html
- TensorRT-LLM AutoDeploy blog — https://developer.nvidia.com/blog/automating-inference-optimizations-with-nvidia-tensorrt-llm-autodeploy/

Third-party benchmarks and analyses (2026, <6 months):
- Spheron, "vLLM vs TensorRT-LLM vs SGLang: H100 Benchmarks (2026)" — https://www.spheron.network/blog/vllm-vs-tensorrt-llm-vs-sglang-benchmarks/
- Spheron, "Deploy Qwen 3.5 on GPU Cloud: GDN Hybrid Architecture, 262K Context, and vLLM Setup (2026)" — https://www.spheron.network/blog/deploy-qwen-3-5-gpu-cloud/
- Spheron, "SGLang Production Deployment Guide (2026)" — https://www.spheron.network/blog/sglang-production-deployment-guide/
- Clarifai, "Comparing SGLANG, vLLM, and TensorRT-LLM with GPT-OSS-120B" — https://www.clarifai.com/blog/comparing-sglang-vllm-and-tensorrt-llm-with-gpt-oss-120b
- LeetLLM, "vLLM vs SGLang vs TensorRT-LLM vs Ollama: The 2026 Inference Engine Showdown" — https://leetllm.com/blog/llm-inference-engine-comparison-2026
- Particula, "SGLang vs vLLM in 2026: Benchmarks, Architecture, and When to Use Each" — https://particula.tech/blog/sglang-vs-vllm-inference-engine-comparison
- Yotta Labs, "Best LLM Inference Engines in 2026: vLLM, TensorRT-LLM, TGI, and SGLang Compared" — https://www.yottalabs.ai/post/best-llm-inference-engines-in-2026-vllm-tensorrt-llm-tgi-and-sglang-compared
- Yotta Labs, "TensorRT-LLM vs vLLM vs SGLang vs TGI: Which Inference Engine Actually Performs Best in Production?" — https://www.yottalabs.ai/post/tensorrt-llm-vs-vllm-vs-sglang-vs-tgi-which-inference-engine-actually-performs-best-in
- Northflank, "vLLM vs TensorRT-LLM: Key differences, performance, and how to run them" — https://northflank.com/blog/vllm-vs-tensorrt-llm-and-how-to-run-them
- GMI Cloud, "vLLM vs TensorRT-LLM vs Triton: The Runtime Decision That Shapes Your Inference Cost" — https://www.gmicloud.ai/en/blog/vllm-vs-tensorrt-llm-vs-triton
- Modal LLM Engineer's Almanac (2026) — https://modal.com/llm-almanac/advisor
- Spheron, "An Overnight Stack for Qwen3.6–27B" (RTX 3090 baseline) — https://medium.com/@fzbcwvv/an-overnight-stack-for-qwen3-6-27b-85-tps-125k-context-vision-on-one-rtx-3090-0d95c6291914
- Derek Armstrong, "Running Qwen3.6 27B Locally on Dual RTX 3090s with vLLM v0.19" — https://derekarmstrong.dev/blog/running-qwen36-27b-dual-rtx-3090-vllm-v019/
- LLMKube, "We ran Qwen3.6-27B on $800 of consumer GPUs, day one" — https://llmkube.com/blog/qwen3-6-27b-bakeoff
- Sai Dheeraj Gummadi, "vLLM x Qwen3-Next: Hybrid Attention, Multi-Token Prediction, and Thinking Controls" — https://medium.com/data-science-in-your-pocket/vllm-x-qwen3-next-hybrid-attention-multi-token-prediction-and-thinking-controls-for-a0f6b3dcc120

Cached reference notes under `docs/reference/inference-engines/`:
- `sglang-overview.md`
- `tensorrt-llm-overview.md`
- `comparison-benchmarks.md`
