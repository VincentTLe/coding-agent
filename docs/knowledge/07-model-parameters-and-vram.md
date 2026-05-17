# 07 — Model Parameters and VRAM

## Core idea (1-2 sentences)

Every model weight occupies a fixed number of bytes (2 bytes for FP16/BF16). To run a model, that many bytes must fit in GPU memory, plus headroom for activations, KV cache, and serving framework overhead.

## Why it matters for our project

Whether Qwen 3.6-27B even *fits* on our hardware is a byte-math question we need to be able to answer at the whiteboard. The professor will ask. The answer determines our serving strategy (single GPU? two with tensor parallelism? quantize?). Get this wrong and the demo OOMs.

## The intuition

Each parameter is one number — a single dial the model can tune during training. A 27 billion parameter model has 27 billion such dials. Each dial is stored as a 2-byte floating-point number (BF16). That's 54 GB of dials sitting in VRAM, even before you've processed a single token. On top of that, you need scratch space (activations during a forward pass), a notepad (KV cache for each request), and overhead from the serving framework.

## The mechanics

### What "parameter" means

A parameter is a single trainable scalar — usually either a **weight** (an element of a matrix that multiplies an input) or a **bias** (a constant added afterwards). In a Transformer:

- Embedding matrix: `vocab_size × hidden_dim` — large but learned. For Qwen 3.6-27B: `248,320 × 5,120 ≈ 1.27 B` parameters.
- Each layer has:
  - QKV projection matrices, output projection — attention parameters
  - Two FFN matrices (up-projection, down-projection) — typically 60–70% of layer parameters
  - LayerNorm scale parameters (small)
- Final output projection (often tied to embedding matrix to save params).

Total for Qwen 3.6-27B: **27 billion**, give or take embedding-tying detail.

### Byte math by precision

| Precision | Bytes per parameter | 27 B model weight size |
|-----------|--------------------|------------------------|
| FP32      | 4                  | 108 GB                 |
| FP16      | 2                  | 54 GB                  |
| BF16      | 2                  | 54 GB                  |
| FP8       | 1                  | 27 GB                  |
| INT4      | 0.5                | 13.5 GB                |

**Qwen 3.6-27B ships in BF16** (per model card: "Tensor type: BF16"). So model weights are **54 GB** in the published format.

### What else lives in VRAM during inference

A serving stack (vLLM) holds the following simultaneously:

1. **Model weights**: 54 GB (Qwen 3.6-27B BF16). Constant per model load.
2. **KV cache**: scales with `(num_active_tokens × num_layers × kv_heads × head_dim × 2 × dtype_bytes)`. For Qwen 3.6-27B at 32K tokens of context (per request) — substantial. With multiple concurrent requests, KV cache can easily reach 10-30 GB.
3. **Activations**: per-request scratch space during the forward pass. Smaller than KV cache for inference. Single-digit GB.
4. **CUDA workspace / framework overhead**: vLLM allocates ~10% slack for fragmentation, optimizer-free buffers, communication buffers. Order of 2-4 GB.
5. **Other process VRAM**: anything else running on the GPU (other users on this shared machine; see SERVER_STATE.md).

### Why 54 GB doesn't fit on one A6000

| GPU            | VRAM | Fits 54 GB model? |
|----------------|------|-------------------|
| A6000          | 48   | No                |
| A6000 × 2 (NVLink) | 96 logical | Yes, via tensor parallelism |
| H100 80GB      | 80   | Yes, single GPU   |
| A100 80GB      | 80   | Yes, single GPU   |

48 < 54 → won't fit. We **must** use tensor parallelism (see [09-tensor-parallelism.md](09-tensor-parallelism.md)) to split the model across both A6000s, giving us 96 GB total to play with.

### The usable-context formula

After loading the model, the remaining VRAM is the budget for KV cache + activations + overhead. A rough formula:

```text
KV_cache_budget = total_VRAM − model_weights − 10% overhead

For 2× A6000:
  KV_cache_budget ≈ 96 − 54 − 10 ≈ 32 GB
```

The number of tokens we can fit in KV cache depends on layer count, head count, head_dim, and precision. vLLM auto-computes this and reports it at startup. For Qwen 3.6-27B's hybrid arch (mostly linear attention, light KV demands), we should get tens of thousands of tokens of concurrent context across batched requests — *more* than for a pure-softmax 27B model.

### What if we quantize?

Drop to FP8 weights → 27 GB → fits on one A6000 with room to spare, KV budget jumps. INT4 → 13.5 GB → comfortable on a single A6000. The trade-off is precision loss, which mostly hurts reasoning and code generation in subtle ways. See [08-quantization.md](08-quantization.md).

For our project, BF16 fits on the 2-GPU setup with room. **We do not need to quantize.** Mention this in the presentation as a deliberate choice — we trade VRAM for quality.

## Concrete numbers for our setup

| Item                       | Value                |
|---------------------------|----------------------|
| Hardware                  | 2× NVIDIA RTX A6000  |
| Per-GPU VRAM              | 48 GB GDDR6          |
| Combined VRAM             | 96 GB                |
| NVLink                    | 3rd gen, 112 GB/s    |
| Model                     | Qwen/Qwen3.6-27B (BF16) |
| Model weight size         | ~54 GB               |
| Tensor parallelism flag   | `--tensor-parallel-size 2` |
| Per-GPU model weight (TP=2) | ~27 GB              |
| Remaining per-GPU         | ~21 GB for KV cache + activations + overhead |
| Other users on GPU0 (from server audit) | several JupyterHub Python procs + one ollama-new (foreign user) consuming ~6 GB |
| Recommended GPU for us    | Prefer GPU1 if running single-GPU experiments; for vLLM TP=2 we need both |

## Likely questions from the professor

**Q: How did you calculate the 54 GB figure?**
A: 27 billion parameters × 2 bytes per parameter (BF16) = 54 GB. The "billion" and the "bytes per parameter" are both exact. Embedding tying and small auxiliary tensors can shift it by a percent or two but the figure is reliable.

**Q: Why BF16 and not FP16?**
A: BF16 (bfloat16) and FP16 (half-precision float) both use 2 bytes, but BF16 has the *same exponent range* as FP32 (8 bits) and only 7 mantissa bits, vs FP16's 5 exponent and 10 mantissa. BF16 is more numerically stable for training (no underflow during gradient descent), and inference quality is essentially identical. NVIDIA Ampere (A6000) and newer GPUs support both natively. Qwen ships in BF16; we just use what they shipped.

**Q: Can we run two model instances on the 2 GPUs to serve more requests in parallel?**
A: With Qwen 3.6-27B at 54 GB, no — one model occupies effectively all 48 GB on each of two GPUs (with TP=2). To run two instances we'd need to quantize or use a smaller model.

**Q: What is "KV cache" and how big does it get?**
A: See [02-context-window-and-attention.md](02-context-window-and-attention.md). For our hybrid model and a reasonable max-context cap (say 32K), KV cache for a few concurrent requests is in the single-digit-GB range, well within budget.

**Q: What about the other users on this server — does that affect us?**
A: Yes — see SERVER_STATE.md. Other users have JupyterHub processes and another Ollama instance on GPU0 occupying ~6 GB total. With Qwen 3.6-27B at 27 GB per GPU under TP=2, we have a comfortable margin on GPU0 (48 − 27 − 6 ≈ 15 GB free) and lots of room on GPU1 (48 − 27 ≈ 21 GB free). If their usage spikes, we may need to coordinate.

**Q: Why don't model weights live in CPU RAM and stream to GPU?**
A: Because each forward pass touches *all* weights. PCIe is too slow (~32 GB/s) compared to GPU memory bandwidth (~768 GB/s on A6000). Streaming would tank inference throughput by 20–30×.

## Common misconceptions / gotchas

- **"More parameters always means better."** Quality scales with parameters, training data, and training compute *together*. A well-trained 27B can outperform a poorly-trained 70B. Don't equate "27B" with capability.
- **"FP16 and BF16 are the same."** Same size (2 bytes); different numerical properties. BF16 is preferred for inference of modern LLMs.
- **"Once the model is loaded I can use 100% of remaining VRAM for KV cache."** No — leave headroom for activations, communication buffers, and framework overhead. vLLM defaults to using ~90% of free memory as the KV cache pool.
- **Previously confused with model size on disk vs in memory**: Disk weight files (safetensors / GGUF) are roughly the same byte count as in-memory weights, sometimes slightly larger due to metadata. The 54 GB figure applies to both — but only the VRAM number matters for "does it fit".

## Sources

- Qwen 3.6-27B model card (parameter count, BF16 precision): https://huggingface.co/Qwen/Qwen3.6-27B (accessed 2026-05-17)
- NVIDIA RTX A6000 official spec page (48 GB GDDR6, NVLink 112 GB/s): https://www.nvidia.com/en-us/design-visualization/rtx-a6000/ (accessed 2026-05-17)
- Local audit: `nvidia-smi` output from this server, 2026-05-17 (see SERVER_STATE.md)
- vLLM memory management guide: https://docs.vllm.ai/en/latest/serving/optimization.html
- IEEE 754 binary16 / Google bfloat16 specifications (precision bytes math)
