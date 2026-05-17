# Qwen3.6-27B Model Card (Summary)

Source: https://huggingface.co/Qwen/Qwen3.6-27B
Accessed: 2026-05-17
Released: 2026-04-22 (per coverage of the release; see https://www.marktechpost.com/2026/04/22/alibaba-qwen-team-releases-qwen3-6-27b...)

## Identity

- Family: Qwen3.6 (Alibaba)
- Repo: `Qwen/Qwen3.6-27B` (canonical — **no `-Instruct` suffix exists**; the fused checkpoint covers both thinking and non-thinking modes, selectable via prompt convention). The only Qwen-published sibling is `Qwen/Qwen3.6-27B-FP8` (FP8 quantization). Confirmed via HuggingFace search 2026-05-17.
- License: Apache 2.0 (per coverage of the series)

## Architecture

- Total parameters: **27 billion**
- Layers: **64**
- Hidden dim: **5,120**
- FFN intermediate dim: **17,408**
- Tokenizer vocab: **248,320** (padded)
- Weight dtype: **BF16**
- Context: **262,144 tokens native**, extensible up to **1,010,000** via YaRN

### Hybrid attention layout

```
Hidden layout: 16 × [3 × (Gated DeltaNet → FFN) → 1 × (Gated Attention → FFN)]
```

- **Gated DeltaNet** (linear attention, 48 layers / 3 of every 4):
  - V heads: 48
  - QK heads: 16
  - Head dim: 128
- **Gated Attention** (standard softmax attention with GQA, 16 layers / 1 of every 4):
  - Q heads: 24
  - KV heads: 4 (Grouped-Query Attention)
  - Head dim: 256
- RoPE rotary dim: 64

## Modes

- Thinking mode (default): generates reasoning before responses
- Non-thinking / instruct mode: direct responses without reasoning
- Both modes share the same checkpoint; selection is via prompt convention.

## Known community quantizations (HuggingFace)

- `QuantTrio/Qwen3.6-27B-AWQ` (INT4 AWQ)
- `unsloth/Qwen3.6-27B-MTP-GGUF` (GGUF, llama.cpp / Ollama)
- `unsloth/Qwen3.6-27B-MLX-8bit` (Apple MLX)
- `batiai/Qwen3.6-27B-GGUF` (GGUF community quant)

For our project: we use the upstream BF16 checkpoint via vLLM with `--tensor-parallel-size 2`.

## Notes

- The `Qwen/Qwen3.6-27B-Instruct` URL (with `-Instruct` suffix) **does not exist as a published repo**. A direct fetch returned HTTP 401 on 2026-05-17; follow-up HuggingFace search lists only `Qwen/Qwen3.6-27B` (base) and `Qwen/Qwen3.6-27B-FP8` (FP8 quant) under the official `Qwen/` namespace for this size. The fused thinking/non-thinking checkpoint at `Qwen/Qwen3.6-27B` is the canonical source for our project.
- Disk size for BF16 safetensors: **~54 GB** (= 27B × 2 bytes).
