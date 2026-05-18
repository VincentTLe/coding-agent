# Qwen3.6-35B-A3B Model Card (cached)

Source: https://huggingface.co/Qwen/Qwen3.6-35B-A3B
Cached: 2026-05-18

## Specifications
- **Total Parameters**: 35B
- **Active Parameters**: 3B (MoE)
- **License**: Apache 2.0
- **Context Length**: 262,144 native; extensible to 1,010,000
- **Architecture**: Sparse MoE, 256 experts (8 routed + 1 shared); hidden 2048; 40 layers
- **Release Date**: April 16, 2026

## Benchmarks
- **SWE-bench Verified**: 73.4
- **SWE-bench Multilingual**: 67.2
- **SWE-bench Pro**: 49.5
- **LiveCodeBench v6**: 80.4
- **Terminal-Bench 2.0**: 51.5
- **AIME 2026**: 92.7
- **GPQA Diamond**: 86.0
- **MMLU-Pro**: 85.2

## Agent / Tool Use
- Agentic coding focus; tool calling and function support
- Thinking mode with `<think>` traces; thinking preservation
- Frameworks: SGLang 0.5.10+, vLLM 0.19.0+, KTransformers, HF Transformers
- Multimodal: text, image, video

## Hardware fit (2x A6000 96GB)
- 35B total + vision encoder is comfortable in BF16 (~70GB), fits with TP=2 and ample KV headroom
- MoE routing overhead is the dominant cost vs raw VRAM bandwidth
