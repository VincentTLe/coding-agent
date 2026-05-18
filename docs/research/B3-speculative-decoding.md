# B3 — Speculative Decoding in vLLM 2026

## TL;DR

For Qwen3.6-27B on 2× A6000 in an interactive coding agent, enable native
MTP (`--speculative-config '{"method":"mtp","num_speculative_tokens":1}'`)
and keep `--enable-prefix-caching` on. MTP is the only method that reliably
works with Qwen3.6's hybrid Gated DeltaNet + Gated Attention; ~1.5–2×
single-stream decode at ~85–95 % acceptance, zero training cost.

## Why

Agent loops are decode-bound (long prompts, ≤ 4 concurrent). Speculation
trades compute for memory reads — that regime. Prefix caching accelerates
prefill; speculation accelerates decode. Orthogonal.

## SOTA 2026

`--speculative-config` JSON accepts 8 methods: EAGLE, MTP, Draft Model,
PARD, MLP, N-Gram, Suffix, Custom. Pipeline-parallel incompatible
(≤ 0.15.0); draft-model needs ≥ 0.10.1.

- **EAGLE-3** — tri-layer fusion; paper 4.1–6.5×, vLLM on gpt-oss 120B:
  +20 % throughput, –20 % latency. Needs trained head.
- **P-EAGLE** (Mar 2026) — +1.69× over EAGLE-3 on B200. Heads for
  gpt-oss-20B/120B, Qwen3-Coder-30B; not 27B dense.
- **MTP** — natively trained into Qwen3.6-27B.
- **Medusa** — supported but ecosystem migrated to EAGLE-3.
- **Draft model** — hidden-dim mismatch blocks Qwen drafters.
- **N-gram** — free, negative speedup on hybrid Qwen.
- **Suffix** — no public Qwen3.6 numbers.
- **Lookahead** — not first-class in vLLM 2026.

## Most-used

EAGLE-3 for served foundation models. For Qwen3.6: MTP, head ships in
weights.

## Comparison — Qwen3.6-27B BF16 TP=2 on 2× A6000

| Method | Works? | Speedup | Setup |
|---|---|---|---|
| MTP n=1 | Yes (native) | ~1.5–1.7× decode | one flag |
| MTP n=2–3 | Partial (FP8 errors reported) | up to 2–2.24× | flag tweak |
| EAGLE-3 / P-EAGLE / Medusa | No head published | n/a | train head |
| Draft model | Dim mismatch | n/a | blocked |
| N-gram | Loads, slower | –4 to –12 % [UNVERIFIED on dense 27B; verified on 35B-A3B sibling] | free |
| Suffix | Likely loads | unknown | free |
| Prefix cache | Yes (orthogonal) | prefill-only | free |

## Recommendation

Enable MTP n=1 day one:

```
vllm serve Qwen/Qwen3.6-27B --tensor-parallel-size 2 \
  --enable-prefix-caching --reasoning-parser qwen3 \
  --max-model-len 65536 \
  --speculative-config '{"method":"mtp","num_speculative_tokens":1}'
```

One flag, zero training, ~1.5–2× decode. Worth the setup complexity (it is
trivial) — not the EAGLE-3 "train a speculator" path.

## Next steps

1. Wire flag into launch; benchmark TTFT/ITL vs. baseline.
2. Try `num_speculative_tokens: 2` on BF16; abort on error.
3. Confirm prefix-hit metric still logs (broken on 0.9.1).
4. Microbench `suffix` vs. MTP n=1.

## Open questions

- MTP n>1 on BF16 TP=2 — FP8-only error?
- EAGLE-3/P-EAGLE head for 27B dense — ETA?
- Suffix decoding on Gated DeltaNet?
- MTP + constrained decoding (tool calls)?

## Sources

1. [vLLM Speculative Decoding docs](https://docs.vllm.ai/en/latest/features/speculative_decoding/)
2. [vLLM Recipe — Qwen3.6-27B](https://recipes.vllm.ai/Qwen/Qwen3.6-27B)
3. [vLLM forum — Qwen3.5-27B-FP8 spec decode](https://discuss.vllm.ai/t/qwen3-5-27b-fp8-speculative-decoding/2447)
4. [Red Hat — spec decode for gpt-oss, 2026-04](https://developers.redhat.com/articles/2026/04/16/performance-improvements-speculative-decoding-vllm-gpt-oss)
5. [AWS — P-EAGLE in vLLM](https://aws.amazon.com/blogs/machine-learning/p-eagle-faster-llm-inference-with-parallel-speculative-decoding-in-vllm/)
6. [vLLM forum — spec + prefix caching](https://discuss.vllm.ai/t/can-speculative-decoding-and-prefix-caching-take-effect-simultaneously/1291)
7. [njannasch — Qwen3.6-27B dense spec-decode](https://njannasch.dev/blog/speculative-decoding-qwen-27b-dense-5060ti/)
8. [MTPLX — 2.24× MTP on Qwen3.6-27B](https://github.com/youssofal/MTPLX)
9. [thc1006 — Qwen3.6-35B-A3B spec-decode benchmark](https://github.com/thc1006/qwen3.6-speculative-decoding-rtx3090)
