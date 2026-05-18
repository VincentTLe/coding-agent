# C1 — Open-Weight Coding LLMs 2026: Qwen 3.6-27B vs Field

2026-05-18. 2 x RTX A6000 (96 GB, NVLink). Incumbent: Qwen 3.6-27B BF16 / vLLM TP=2.

## TL;DR
- Keep Qwen 3.6-27B BF16. Best dense open model fitting 96 GB at full precision: SWE-V 77.2, LCB v6 83.9.
- Pilot Qwen 3.6-35B-A3B (Apache 2.0, MoE 3B-active) for latency on agent loops; ~4 pts SWE-V lower.
- Skip Kimi K2.6, DeepSeek V3.2/V4, GLM-4.7, Llama 4 Maverick — exceed 96 GB at any usable precision.

## Why now
Five open releases (Kimi K2.6, DeepSeek V3.2, GLM-4.7, Qwen 3.6-35B-A3B, Qwen3-Coder-Next) landed in 30 days. Confirm 27B is still the backbone before scaffolding work.

## SOTA 2026 (open-weight SWE-bench Verified)
V4-Pro-Max 80.6 > Kimi K2.6 80.2 = MiniMax M2.5 80.2 > GLM-5 77.8 > **Qwen 3.6-27B 77.2** > GLM-4.7 73.8 > Qwen 3.6-35B-A3B 73.4 > DeepSeek V3.2 ~73 > Qwen3-Coder-Next 70.6. HumanEval/MBPP saturated (95%+); dropped as primary in 2026.

## Most used
Qwen 3.6 family dominates HF downloads in the 24-96 GB tier. DeepSeek V3.2/V4 lead *hosted* but not self-host on Ampere.

## Comparison (ranked by fit on 2x A6000)
| Model | Total/Active | License | Ctx | SWE-V | LCB v6 | Fits 96 GB? |
|---|---|---|---|---|---|---|
| **Qwen 3.6-27B** | 27B dense | Apache 2.0 | 262K | **77.2** | **83.9** | Yes, BF16 ~54 GB |
| Qwen 3.6-35B-A3B | 35B/3B MoE | Apache 2.0 | 262K | 73.4 | 80.4 | Yes, BF16 ~70 GB |
| Qwen3-Coder-Next | 80B/3B MoE | Apache 2.0 | 256K | 70.6 | strong | FP8 ~80 GB, tight |
| Llama 4 Scout | 109B/17B MoE | Llama 4 Community | 10M | 47.3 | 70.4 | INT4 only |
| GLM-4.6 | 355B/32B MoE | MIT | 200K | 68.0 | 82.8 | No |
| GLM-4.7 | ~360B MoE | MIT | 200K | 73.8 | n/a | No |
| DeepSeek V3.2 | 671B/37B MoE | MIT | 164K | ~73 | 83.3 | No |
| Kimi K2.6 | 1T MoE | Open Moonshot | 256K | 80.2 | n/a | No |
| V4-Pro-Max | 1.6T MoE | MIT | n/a | 80.6 | 93.5 | No |

VRAM: BF16=2 B/p, FP8=1, INT4=0.5; add ~5-15 GB KV.

## Recommendation
Stay on Qwen 3.6-27B BF16. (1) Best benchmark-per-GB in our class; no open model fits 96 GB at full precision and matches SWE-V 77.2 / LCB 83.9. (2) Apache 2.0 (no EU/MAU friction; Llama 4 has both). (3) Upstream `qwen3_coder` tool-call parser in vLLM. (4) 262K native context. (5) Swap to 35B-A3B is a config change, same parser.

## Next steps
1. In-repo multi-file SWE-style eval: 27B vs 35B-A3B.
2. Tok/s under TP=2 for 27B BF16 vs 35B-A3B BF16/FP8; if MoE wins on agent throughput and quality is within 5%, switch.
3. Pin model commit SHAs in the launcher.
4. Re-evaluate quarterly.

## Open questions
- 77.2 vs 73.4 SWE-V delta real on our repo or scaffold noise? [UNVERIFIED]
- 35B-A3B FP8 quality on long agent loops [UNVERIFIED]
- Qwen 3.6 training cutoff not published; LCB v6 implies 2026 [UNVERIFIED]

## Sources
- https://huggingface.co/Qwen/Qwen3.6-27B
- https://qwen.ai/blog?id=qwen3.6-27b
- https://huggingface.co/Qwen/Qwen3.6-35B-A3B
- https://huggingface.co/Qwen/Qwen3-Coder-Next
- https://huggingface.co/deepseek-ai/DeepSeek-V3.2
- https://arxiv.org/pdf/2512.02556
- https://huggingface.co/zai-org/GLM-4.6
- https://huggingface.co/zai-org/GLM-4.7
- https://ai.meta.com/blog/llama-4-multimodal-intelligence/
- https://huggingface.co/moonshotai/Kimi-K2.6
- https://llm-stats.com/benchmarks/swe-bench-verified
- https://www.cloudrift.ai/blog/optimizing-qwen3-coder-rtx5090-pro6000
