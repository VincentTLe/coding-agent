# TensorRT-LLM reference notes (cached 2026-05-18)

Source: NVIDIA TensorRT-LLM official docs (nvidia.github.io/TensorRT-LLM), GitHub releases, support matrix.

## What it is
- NVIDIA's production LLM serving stack. Closed-source kernels + open Python API.
- Latest release: **v1.2.1 (2026-04-20)**.
- Replaces FasterTransformer for LLM inference on NVIDIA GPUs.

## Serving paths
1. **`trtllm-serve`** — OpenAI-compatible REST server bundled since 2025. Exposes `/v1/chat/completions`, `/v1/completions`. Tool calling supported via parsers.
2. **Triton Inference Server + TensorRT-LLM backend** — production grid path. Triton wraps TensorRT-LLM, vLLM, ONNX backends behind one HTTP/gRPC interface.
3. **Python LLM API** — direct in-process inference, useful for batch/offline jobs.
4. **AutoDeploy (beta)** — compiles off-the-shelf PyTorch graph → optimized TensorRT-LLM graph; reduces boilerplate.

## Hardware support matrix (per official docs)
| Architecture | SM | FP32/FP16/BF16 | INT8/INT4 | FP8 | NVFP4 |
|---|---|---|---|---|---|
| Ampere (A100, A6000) | 80, 86 | Yes | Yes (model-dependent) | **No** | No |
| Ada (RTX 4090, L40S) | 89 | Yes | Yes | Yes | No |
| Hopper (H100, H200) | 90 | Yes | Yes | Yes | Yes (limited) |
| Blackwell (B100, B200, GB200) | 100, 120 | Yes | Yes | Yes | **Yes (native)** |

Critical: **FP8 quantization is not implemented on Ampere SM86.** Best Ampere path is INT8 SmoothQuant or INT4 AWQ.

## Compile-time engine
- Every model+precision+TP combo requires a one-shot engine build.
- Build time on a single GPU: ~15–30 min for a 70B model; ~28 min observed for Llama-3.3-70B FP8 on H100 SXM5.
- Engine is hardware-specific (recompile when GPU changes).
- Model weight or config change → rebuild.
- Engines are sharded by TP rank — different `--tp 2` engine than `--tp 4`.

## Quantization
- FP8 (E4M3, E5M2) — Hopper/Blackwell only.
- NVFP4 — Blackwell native; flagged on Hopper.
- INT8 SmoothQuant — Ampere/Ada/Hopper.
- INT4 AWQ — broad; best for small-batch (<=4) memory-bound scenarios.
- INT4 GPTQ — supported.
- KV cache quantization — optional; risks accuracy on aggressive settings.

## Supported models (Qwen family, per support matrix)
- `Qwen2ForCausalLM` (Qwen2, QwQ)
- `Qwen3ForCausalLM` (Qwen3 base)
- `Qwen3MoeForCausalLM` (Qwen3 MoE)
- **Qwen3-Next (hybrid Gated DeltaNet)** — beta as of TensorRT-LLM 1.x; attention/VisualGen runtime fixes in recent releases.
- **Qwen3.6-27B (dense, hybrid Gated DeltaNet + Gated Attention)** — NOT explicitly listed in current support matrix. Some community PRs reference it. Treat as unverified.

## Performance characteristics (H100 SXM5, Llama-3.3-70B FP8, Spheron 2026 bench)
| Concurrency | tok/s | p50 TTFT (ms) | p95 TTFT (ms) |
|---|---|---|---|
| 1 | 130 | 38 | 55 |
| 10 | 710 | 105 | 170 |
| 50 | 2,100 | 340 | 620 |
| 100 | 2,780 | 680 | 1,280 |
- Throughput lead: +13–16% vs vLLM on H100.
- TTFT lead: +6–12% vs vLLM.
- Cold start including compile: **~28 minutes** vs vLLM's 62 seconds.

## When TensorRT-LLM is the right call
- Single model, long-term production, fleet of H100s/B200s.
- Throughput per dollar is the dominant cost driver.
- Operations team is happy to manage a compile-cache pipeline.
- Not iterating on the model file weekly.

## When TensorRT-LLM is the wrong call
- Iterating on model architecture (each rebuild costs 30 min on H100, more on smaller GPUs).
- Targeting Ampere/A6000 — you lose FP8 (the headline TensorRT-LLM perf knob) AND the official model coverage for Qwen3.6 is thin.
- Multi-model or LoRA-style multitenancy.
- Small team without TRT-LLM operational expertise.
- Non-NVIDIA hardware (no AMD/Apple path).

## Sources
- https://nvidia.github.io/TensorRT-LLM/
- https://nvidia.github.io/TensorRT-LLM/reference/support-matrix.html
- https://nvidia.github.io/TensorRT-LLM/release-notes.html
- https://github.com/NVIDIA/TensorRT-LLM
- https://nvidia.github.io/TensorRT-LLM/performance/performance-tuning-guide/fp8-quantization.html
- https://developer.nvidia.com/blog/automating-inference-optimizations-with-nvidia-tensorrt-llm-autodeploy/
- https://github.com/NVIDIA/TensorRT-LLM/issues/1452 (A6000 thread)
