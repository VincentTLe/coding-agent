# Qwen3.6-27B Model Card (cached)

Source: https://huggingface.co/Qwen/Qwen3.6-27B and https://qwen.ai/blog?id=qwen3.6-27b
Cached: 2026-05-18

## Specifications
- **Total Parameters**: 27B (27.8B per llm-stats); dense (no MoE)
- **License**: Apache 2.0
- **Context Length**: 262,144 tokens native; extensible to 1,010,000
- **Release Date**: April 21, 2026
- **Modality**: Vision-Language (multimodal)
- **Architecture**: Hybrid 16x (3 x Gated DeltaNet -> FFN, 1 x Gated Attention -> FFN); hidden 5120; FFN 17408

## Benchmarks
- **SWE-bench Verified**: 77.2
- **SWE-bench Pro**: 53.5
- **LiveCodeBench v6**: 83.9
- **Terminal-Bench 2.0**: 59.3
- **AIME 2026**: 94.1
- **GPQA Diamond**: 87.8
- **MMLU-Pro**: 86.2
- HumanEval / MBPP: Not reported (saturated; frontier ~95%+)

## Agent / Tool Use
- Native tool calling; Qwen-Agent and qwen-code (CLI agent) integrations
- vLLM serve example with `--reasoning-parser qwen3 --enable-auto-tool-choice --tool-call-parser qwen3_coder`
- Thinking mode default; `enable_thinking=False` for non-thinking
- "Thinking preservation" for iterative dev

## Training data freshness
- Not explicitly stated in card; LiveCodeBench v6 uses problems post-cutoff so the 83.9 implies a 2026 cutoff
