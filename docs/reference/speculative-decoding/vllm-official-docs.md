# vLLM Speculative Decoding — Official Docs (cached 2026-05-18)

Source: https://docs.vllm.ai/en/latest/features/speculative_decoding/

## Supported methods (8)

1. EAGLE — model-based, strong gain at low QPS
2. MTP (Multi-Token Prediction) — best when target model has native MTP
3. Draft Model — separate small draft model
4. PARD (Parallel Draft Model) — low draft latency
5. MLP — medium/high gain when speculator available
6. N-Gram — lightweight, low/medium gain
7. Suffix Decoding — dynamic depth, no draft model
8. Custom Proposer (experimental)

## Primary config flag

CLI: `--speculative-config '{...}'`
Python: `LLM(..., speculative_config={...})`

Common keys: `method`, `model`, `num_speculative_tokens`, `rejection_sample_method` (strict/probabilistic/synthetic), `draft_tensor_parallel_size`.

Method-specific:
- N-gram: `prompt_lookup_min`, `prompt_lookup_max`
- Suffix: `suffix_decoding_max_tree_depth`, `suffix_decoding_min_token_prob`
- EAGLE-3: `method: "eagle3"`

## Compatibility caveats

- Pipeline parallelism NOT composable with speculative decoding (vllm ≤ 0.15.0).
- Draft-model method requires vLLM 0.10.1+.
- EAGLE speculators are model-specific (trained per target).
- Hybrid attention models (linear/recurrent state) lack per-token rollback of `conv_states`/`recurrent_states`, blocking general speculation.
