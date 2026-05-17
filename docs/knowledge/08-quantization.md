# 08 — Quantization

## Core idea (1-2 sentences)

Quantization replaces each weight's high-precision floating-point number with a lower-precision approximation (FP8 → 1 byte, INT4 → 0.5 byte). The model shrinks; quality degrades by a small, sometimes-imperceptible amount.

## Why it matters for our project

We don't *need* to quantize Qwen 3.6-27B for our hardware (it fits in BF16 across 2× A6000). But the professor will likely ask: "Why didn't you use a smaller quantized model? Why didn't you use a larger quantized model?" We should know the trade-offs and be able to articulate the choice.

## The intuition

A painter's palette analogy. The model is a painting. Each weight is a pixel.

- **BF16** is a 65,536-color palette — every pixel can be one of 65K shades.
- **FP8** is a 256-color palette — like an early Macintosh image. Most paintings look fine. Subtle gradients lose detail.
- **INT4** is a 16-color palette — like Pictionary on a chalkboard. The painting is *recognizable* but lots of subtlety is gone.

When you reduce the palette, you don't just lose color — you also have to decide *how* to map the original to the new palette (quantization scheme). Different schemes preserve different things. AWQ preserves the most-used "colors" (activation-aware); GPTQ tries to minimize total reconstruction error.

## The mechanics

### What's actually being quantized

In a Transformer, the *weights* (matrices in attention and FFN) are typically what get quantized. Activations and KV cache may or may not be quantized depending on the scheme:

- **W4A16** — weights are 4-bit, activations stay 16-bit. Most weight-only schemes.
- **W8A8** — both weights and activations are 8-bit. Useful for fully-quantized inference on H100/B100 with FP8 hardware support.
- **W4A4** — extreme; usually only for research.
- **KV cache quantization** — separately, you can quantize the KV cache (e.g., to FP8) to fit more concurrent users.

### Major quantization methods (verified from vLLM docs)

| Method | What it does | When to use |
|--------|--------------|-------------|
| **AWQ** (Activation-aware Weight Quantization) | INT4 weights; preserves the channels with highest activation magnitudes. Industry-standard 4-bit. | Best for INT4 inference on most GPUs. |
| **GPTQ** | INT4 weights; iteratively minimizes output error layer-by-layer. | Solid INT4 alternative; sometimes slightly worse than AWQ on modern models. |
| **FP8 (W8A8)** | 8-bit floating point for both weights and activations. Hardware-supported on H100, MI300X. | Best quality at 8-bit; nearly lossless vs BF16. |
| **INT8 (W8A8)** | 8-bit integer scheme (SmoothQuant style). | Older path; FP8 is usually preferred when hardware supports it. |
| **BitsAndBytes (NF4 / FP4)** | Hugging Face-friendly on-the-fly quantization. | Easy single-line conversion; slightly lower quality than AWQ/GPTQ for inference. |
| **GGUF** | A file format (used by llama.cpp / Ollama) supporting many quant levels (Q4_K_M, Q5_K_M, Q6_K, Q8_0, ...). | Required if serving via llama.cpp / Ollama. |

The first five are all supported in vLLM. GGUF is for the llama.cpp ecosystem (Ollama).

### Quality impact — what gets hurt

Empirically, in order of how much each capability suffers as you compress from BF16 → INT4:

1. **Hardest hit**: multi-step reasoning, code generation accuracy on hard problems, math, long-context comprehension. The places where the model is already near its limit.
2. **Medium impact**: instruction-following nuance, factual recall on rare facts.
3. **Smallest impact**: everyday conversation, common-knowledge QA, fluency.

Roughly: INT4 (well-quantized with AWQ) can be 1–3 percentage points lower on hard benchmarks vs BF16. INT8/FP8 is often within 0.5%.

### Hardware support matters

- **FP8** requires Hopper (H100) or newer / NVIDIA Blackwell / AMD MI300X / etc. **Ampere (A6000) does NOT have native FP8 tensor core support** — so FP8 on our hardware would be emulated and slower.
- **INT4** (AWQ, GPTQ) works on Ampere via int8 tensor cores with dequant-on-the-fly. Fully supported on A6000.
- **BF16/FP16** is native on A6000 (third-gen Tensor Cores).

So if we *did* want to shrink the model for our hardware, INT4 (AWQ) is the right choice — not FP8.

### Why we chose BF16 for this project

1. Quality matters most for the demo — agent reasoning failures are the worst kind of demo failure.
2. The model fits in BF16 on 2× A6000 (54 GB / 96 GB) → no reason to quantize.
3. Simpler dependency story — vLLM serves BF16 cleanly without extra config.
4. Reproducibility — quantization adds another step (the quant calibration data), and reproducibility matters for a course project.

If we *had* only one A6000, the decision would flip: AWQ Q4 fits in 13.5 GB and is well-supported.

### Quantization vs compression

Worth being precise: quantization is *lossy*. Some bits of every weight are thrown away. You cannot recover BF16 from INT4. Compare to gzip on weights, which is lossless and irrelevant for inference (you'd decompress to BF16 anyway). Don't confuse the two.

## Concrete numbers for our setup

| Precision | Qwen 3.6-27B size | Fits 1×A6000 (48 GB)? | Fits 2×A6000 (96 GB)? | Our choice? |
|-----------|-------------------|----------------------|----------------------|-------------|
| FP32      | 108 GB            | No                   | No                   | No          |
| BF16      | 54 GB             | No (1 GPU)           | Yes (TP=2)           | **YES**     |
| FP8       | 27 GB             | Yes                  | Yes                  | No (no native A6000 support) |
| INT4 AWQ  | ~13.5 GB          | Yes                  | Yes                  | No (overkill for our setup) |

Existing community quants for Qwen 3.6-27B observed on Hugging Face (from search results): `QuantTrio/Qwen3.6-27B-AWQ`, `unsloth/Qwen3.6-27B-MTP-GGUF`, `unsloth/Qwen3.6-27B-MLX-8bit`. These exist; we are not using them.

The owner's Ollama already has `qwen3.6:27b` at 17 GB on disk — that's a GGUF quantization (likely Q4_K_M or similar). Useful for casual chat through Open WebUI; not what we serve from vLLM for the demo.

## Likely questions from the professor

**Q: Why didn't you quantize to fit on one GPU?**
A: Two reasons. (1) We have two A6000s with NVLink, so quantization is not required to run BF16. (2) For our use case — an agent doing multi-step reasoning and code generation — BF16 quality is worth the second GPU. We have the hardware budget; spending it on precision is the right call.

**Q: What's the difference between AWQ and GPTQ?**
A: Both produce INT4 weights. AWQ asks "which channels have the largest activations on calibration data?" and protects those by scaling weights before quantizing. GPTQ asks "what's the optimal per-layer quantization that minimizes output error?" and uses an approximate second-order method to solve it. Both are good; AWQ is more popular in 2025-2026.

**Q: Why does INT4 not destroy the model?**
A: Modern quantization is *group-wise*: weights are quantized in small blocks (e.g., 128 weights per block), each block with its own scale factor. So the dynamic range is preserved locally. Plus, neural networks are remarkably robust to small per-weight noise.

**Q: Does quantization slow inference or speed it up?**
A: Speeds it up, usually. Smaller weights mean less memory bandwidth, which is the bottleneck on inference. A well-implemented AWQ kernel can be 1.5–2× faster than BF16 on the same GPU, even though the math is more complex (because dequant + matmul fits in less memory traffic).

**Q: What about KV cache quantization?**
A: Different from weight quantization. You can store K and V tensors at FP8 to fit more context / concurrent requests. vLLM supports this. We don't enable it because our context demand is modest and quality matters.

## Common misconceptions / gotchas

- **"Quantization makes the model dumber across the board."** Not uniformly — easy tasks barely move; hard reasoning tasks suffer more.
- **"FP8 is always available."** No, hardware-dependent. A6000 does not have native FP8 tensor cores.
- **"Q4 in GGUF is the same as INT4 in AWQ."** Different file formats and quantization algorithms. GGUF Q4_K_M is a llama.cpp-specific scheme using mixed bit-widths in different parts of the weight; AWQ is a uniform 4-bit-per-weight scheme with activation-aware scales. Quality is comparable on most models, but they are not interchangeable.
- **"Lower bits = always faster."** False past a point. Below INT4, dequant overhead and accuracy drops typically outweigh the memory savings. INT4 is the current sweet spot.
- **Previously confused with distillation**: Quantization shrinks numerical precision of existing weights. Distillation trains a *smaller* model to mimic a larger one. Completely different techniques.

## Sources

- vLLM quantization overview (supported methods): https://docs.vllm.ai/en/latest/features/quantization/index.html (accessed 2026-05-17)
- Lin et al., "AWQ: Activation-aware Weight Quantization for LLM Compression and Acceleration": https://arxiv.org/abs/2306.00978
- Frantar et al., "GPTQ: Accurate Post-Training Quantization for Generative Pre-trained Transformers": https://arxiv.org/abs/2210.17323
- NVIDIA RTX A6000 Ampere arch (BF16/FP16 tensor cores; no native FP8): https://www.nvidia.com/en-us/design-visualization/rtx-a6000/ (accessed 2026-05-17)
- Hugging Face community quantizations for Qwen 3.6-27B: search results 2026-05-17 (`QuantTrio/Qwen3.6-27B-AWQ`, `unsloth/Qwen3.6-27B-MTP-GGUF`)
