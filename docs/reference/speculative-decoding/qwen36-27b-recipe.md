# Qwen3.6-27B Speculative Decoding — vLLM Recipe + Field Reports (cached 2026-05-18)

Sources:
- https://recipes.vllm.ai/Qwen/Qwen3.6-27B
- https://discuss.vllm.ai/t/qwen3-5-27b-fp8-speculative-decoding/2447
- https://njannasch.dev/blog/speculative-decoding-qwen-27b-dense-5060ti/
- https://medium.com/@fzbcwvv/an-overnight-stack-for-qwen3-6-27b-85-tps-125k-context-vision-on-one-rtx-3090-0d95c6291914
- https://github.com/youssofal/MTPLX

## Architecture

64 layers; 3-of-4 sublayers use Gated DeltaNet (linear attention, recurrent state),
1-of-4 uses Gated Attention. MTP head trained natively. 262 144 context.

## Official recipe (vLLM)

```
--speculative-config '{"method": "mtp", "num_speculative_tokens": 1}'
--reasoning-parser qwen3
--max-model-len 262144
--tensor-parallel-size 2
--enable-prefix-caching
```

(`--language-model-only` if text-only.)

## What works

- **MTP** (`method: "mtp"`, n=1–3) — only reliably functional method.
  - Forum: 16 % throughput gain (120 → 140 req/min) on FP8.
  - RTX 3090 single-stream: 85 TPS sustained / 106 peak with n=3, accept 91–97 %.
  - RTX 5090 single-stream: ~2× decode (32 → ~64 tok/s) with ~85 % accept.
  - Apple Silicon (MTPLX): 2.24× decode at temp 0.6.

## What fails

- **Draft-model** (Qwen-4B / Qwen-9B as drafter): tensor-dim mismatches
  (5 120 vs 4 096); architecture-incompatible.
- **EAGLE / EAGLE-3**: no Qwen3.6-27B EAGLE heads on HuggingFace as of 2026-05.
- **N-gram on hybrid Qwen**: bimodal degradation; 100 % accept rate can still
  *lose* tok/s because Gated DeltaNet state cannot be partially rolled back.
- **MTP num_speculative_tokens=2** on some FP8 builds: hard error (forum report).

## Root cause for non-MTP failures

Quote (Jianhua-Cui, vLLM forum): "Qwen3.5 uses hybrid linear attention
throughout. Its `conv_states` and `recurrent_states` do not have a
`sequence_length` dimension, so they cannot be selectively accepted the way a
traditional KV cache can." Same applies to Qwen3.6-27B.

## Prefix caching interaction

`--enable-prefix-caching` stays on with MTP; orthogonal benefit. Stats logging
broken in 0.9.1 when both are active. Speculative tokens consume extra KV
blocks → effective batch shrinks under concurrency, but interactive (≤ 4
concurrent) workloads unaffected.

## Variants

- `z-lab/Qwen3.6-27B-DFlash` — block-diffusion drafter; experimental.
- `sakamakismile/Qwen3.6-27B-Text-NVFP4-MTP` — pre-baked MTP weights.
