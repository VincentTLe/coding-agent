# EAGLE-3 and Alternatives — 2026 Landscape (cached 2026-05-18)

Sources:
- https://developers.redhat.com/articles/2025/07/01/fly-eagle3-fly-faster-inference-vllm-speculative-decoding
- https://developers.redhat.com/articles/2026/04/16/performance-improvements-speculative-decoding-vllm-gpt-oss
- https://aws.amazon.com/blogs/machine-learning/p-eagle-faster-llm-inference-with-parallel-speculative-decoding-in-vllm/
- https://github.com/vllm-project/vllm-project.github.io/blob/main/_posts/2026-03-13-p-eagle.md
- https://github.com/SafeAILab/EAGLE
- https://docs.vllm.ai/en/latest/features/speculative_decoding/n_gram/

## EAGLE-3

- Tri-layer feature fusion (early/middle/late).
- Paper: 4.1–6.5× speedup at T=0 on academic benchmarks.
- vLLM-measured on gpt-oss 120B (Red Hat 2026-04):
  - ShareGPT: +20.7 % throughput, –20.3 % latency
  - SWE-bench: +20.5 % throughput, –19.4 % $/Mtok, –17.5 % ITL
  - MLPerf summarization: +9.5–16 %
- Sweet spot: `num_speculative_tokens=3` (35.6 % accept) for throughput,
  =2 (45.4 % accept) for TTFT. `=4` regresses 8 %.
- Requires a pre-trained EAGLE head per target model.

## P-EAGLE (March 2026)

- Parallel draft generation in one forward pass.
- Up to 1.69× over vanilla EAGLE-3 on B200.
- +30 % HumanEval, +31 % SPEED-Bench at K=7.
- Pre-trained heads exist for gpt-oss 120B/20B, **Qwen3-Coder-30B** — NOT for
  Qwen3.6-27B as of 2026-05.

## Medusa

Still referenced in vLLM docs but lower adoption vs EAGLE-3 in 2026. Requires
training Medusa heads on the target model. No Qwen3.6 heads published.

## Lookahead Decoding

Not first-class in vLLM 2026. The `--num-lookahead-slots` engine arg is an
internal scheduler parameter used by spec-decode; it will be replaced by
`speculative_config`. Standalone Lookahead (Jacobi-style) is not a configurable
method in the latest docs.

## N-gram / Prompt-Lookup

```
{"method": "ngram", "num_speculative_tokens": 5,
 "prompt_lookup_min": 2, "prompt_lookup_max": 4}
```

Cheap (no draft model). Wins on summarization / QA / refactor where output
echoes input. On hybrid-attention Qwen3.6 it can show *negative* gain due to
rollback cost.

## Suffix Decoding

Dynamic-depth, no draft model, no extra weights. Worth testing on Qwen3.6
where MTP n>1 errors, but no public 27B benchmark yet.

## Speculative vs prefix caching

Orthogonal: prefix caching saves prefill, speculative saves decode.
vLLM keeps `--enable-prefix-caching` default-on under speculation.
Extra KV blocks (~num_speculative_tokens per sequence) reduce effective
batch — negligible at low concurrency (interactive agent), painful at >50 QPS.
