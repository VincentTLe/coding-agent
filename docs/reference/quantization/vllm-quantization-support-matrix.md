# vLLM Quantization Support Matrix (May 2026)

Cached extract from vLLM official docs and llm-compressor README for the B5 quantization
landscape report. Use this as the source-of-truth for "what runs on Ampere/A6000."

## Ampere (SM 8.0/8.6 - A100, A6000, RTX 3090) Compatibility

Source: https://docs.vllm.ai/en/v0.6.4/quantization/supported_hardware.html
+ https://docs.vllm.ai/en/latest/features/quantization/

| Method            | Ampere | Notes                                                   |
|-------------------|--------|----------------------------------------------------------|
| AWQ (W4A16)       | yes    | Default AWQ kernel; Marlin-AWQ available for higher BS  |
| GPTQ (W4A16)      | yes    | ExLlamaV2 default; Marlin/Machete for compressed-tensors |
| INT8 W8A8         | yes    | CUTLASS INT8 kernels                                     |
| FP8 W8A8          | NO     | Hopper / Ada only                                        |
| FP8 W8A16 (Marlin)| yes    | Weight-only dequant on Ampere via FP8 Marlin (PR #5975)  |
| INT4 W4A16        | yes    | Compute capability > 8.0 required                        |
| BitsAndBytes NF4  | yes    | Slow; deprecation proposed (RFC #39583)                  |
| GGUF              | yes    | Slow; deprecation proposed; out-of-tree plugin planned   |
| NVFP4 / MXFP4     | NO     | Blackwell native; emulation only on older HW             |

## Kernel Inventory (vLLM 0.10+ / latest)

- **Marlin** (Ampere+): mixed-precision FP16xINT4 GEMM. Near-ideal ~4x weight-only
  speedup at batch ≤ 16-32, decreasing to ~1.5x at batch 128 (compute-bound).
  arXiv 2408.11743.
- **Machete** (Hopper SM 9.0a only): successor to Marlin for H100 mixed-precision.
  NOT available on A6000.
- **CUTLASS FP8 W8A8** (Ada/Hopper): true W8A8 path for L40S/H100.
- **CUTLASS INT8 W8A8** (Ampere+): for INT8 SmoothQuant flows.
- **ExLlamaV2** (Ampere+): default GPTQ kernel; superseded by Marlin where supported.

## Tooling

- **llm-compressor v0.10.0.2** (vllm-project, 1 May 2026): one-stop calibration for
  GPTQ, AWQ, SmoothQuant, RTN, AutoRound, SpinQuant. Emits FP8/INT8/INT4/NVFP4/MXFP4/W4A8.
  Source: https://github.com/vllm-project/llm-compressor
- **AutoAWQ** (casper-hansen): archived May 2025. Replaced by AWQModifier in
  llm-compressor.
- **GPTQModel v7.0.0** (ModelCloud, 28 Apr 2026): active fork of AutoGPTQ;
  produces vLLM-compatible GPTQ checkpoints; adds Ascend NPU support.
- **BitsAndBytes** (>=0.49.2): NF4/FP4 in-flight; deprecation RFC #39583 filed.

## Hardware FP8 Reality Check on A6000

- A6000 = GA102, Ampere SM 8.6. NO native FP8 tensor cores (those start on Ada SM 8.9
  / Hopper SM 9.0).
- Loading `Qwen/Qwen3.6-27B-FP8` on A6000 works via **FP8 Marlin** weight-only path
  (W8A16): weights stay FP8 on disk/HBM, dequantized to BF16 in registers, GEMM in
  BF16. You get the **memory** win (~28 GB vs ~54 GB BF16) but a smaller compute win
  than on H100/L40S.
- Source: vLLM PR #5975 "Expand FP8 support to Ampere GPUs using FP8 Marlin"
  https://github.com/vllm-project/vllm/pull/5975

## Speedups Observed (vendor / paper numbers, [UNVERIFIED] on our hardware)

- Marlin W4A16 vs FP16: ~3.9x on A10 at BS<=32, ~1.5x at BS=128 (arXiv 2408.11743).
- Marlin-AWQ on Qwen 4-bit: ~741 tok/s vs ~712 tok/s Marlin-GPTQ, ~3x vs BF16 baseline
  (Jarvis Labs vLLM quant guide, 2026).
- FP8 W8A8 on Ada/Hopper: ~1.6x throughput, 2x memory (vLLM FP8 docs).
- AWQ accuracy retention: ~95-99% of base on MMLU/HellaSwag/ARC.
- GPTQ accuracy: ~1-3% drop vs AWQ at 4-bit on reasoning benchmarks.

## Existing Qwen 3.6-27B Quants on HuggingFace (sample, May 2026)

- `Qwen/Qwen3.6-27B-FP8` (official, 5.8M downloads) - fine-grained FP8, block=128
- `QuantTrio/Qwen3.6-27B-AWQ` - data-free AWQ, ~21 GiB on disk
- `QuantTrio/Qwen3.6-27B-AWQ-6Bit` - 6-bit AWQ
- `cyankiwi/Qwen3.6-27B-AWQ-INT4` (1.24M downloads)
- `Intel/Qwen3.6-27B-int4-AutoRound`
- `unsloth/Qwen3.6-27B-NVFP4` (Blackwell-only at inference compute)
- `bartowski/Qwen_Qwen3.6-27B-GGUF`
- 300+ community variants

## Sources
- https://docs.vllm.ai/en/latest/features/quantization/
- https://docs.vllm.ai/en/latest/features/quantization/fp8/
- https://docs.vllm.ai/en/latest/features/quantization/int4/
- https://docs.vllm.ai/en/stable/features/quantization/bnb/
- https://docs.vllm.ai/en/v0.6.4/quantization/supported_hardware.html
- https://github.com/vllm-project/llm-compressor
- https://github.com/vllm-project/vllm/pull/5975
- https://github.com/vllm-project/vllm/issues/39583
- https://arxiv.org/abs/2408.11743
- https://huggingface.co/Qwen/Qwen3.6-27B-FP8
- https://huggingface.co/QuantTrio/Qwen3.6-27B-AWQ
