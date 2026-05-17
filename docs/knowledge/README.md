# Knowledge Base — Personal Reference

This is the owner's personal knowledge base, captured during the build of `coding-agent` (Math/Stat 361 project, Knox College, advisor Prof. Andrew Leahy, demo May 29, 2026).

It is **not** a tutorial for others. It reflects what *I* (the owner) learned, in the order I learned it, with the analogies that clicked, and the specific numbers that apply to this project's hardware (2× A6000) and chosen model (Qwen 3.6-27B).

Goals when using this folder:

1. **Review before exams / advisor meetings** — read in numerical order.
2. **Look up during coding** — open the file matching what you're about to implement.
3. **Pull from for slides** — each file's "Likely questions from the professor" section ≈ slide bullets.

## Reading order (linear)

| #  | File | Reading time | Why first |
|----|------|-------------|-----------|
| 01 | [Tokens and Tokenization](01-tokens-and-tokenization.md) | 10 min | Nothing else makes sense without this |
| 02 | [Context Window and Attention](02-context-window-and-attention.md) | 15 min | The cost driver |
| 03 | [Embeddings and Vector Space](03-embeddings-and-vector-space.md) | 10 min | What tokens become |
| 04 | [Transformer Architecture](04-transformer-architecture.md) | 15 min | What stacks the embeddings |
| 05 | [Decoder-Only vs Encoder-Decoder](05-decoder-only-vs-encoder-decoder.md) | 10 min | Why modern LLMs look the way they do |
| 06 | [Stateless API and Chat Format](06-stateless-api-and-chat-format.md) | 12 min | The interface our agent code talks to |
| 07 | [Model Parameters and VRAM](07-model-parameters-and-vram.md) | 12 min | "Does it fit on our hardware?" |
| 08 | [Quantization](08-quantization.md) | 12 min | "Why aren't you quantizing?" — common question |
| 09 | [Tensor Parallelism](09-tensor-parallelism.md) | 12 min | How we actually run a 54 GB model on 48 GB cards |
| 10 | [vLLM vs Ollama](10-vllm-vs-ollama.md) | 12 min | Why we chose vLLM for the agent backend |
| —  | [Glossary](glossary.md) | as needed | Lookup, not linear reading |

Total linear read: ~2 hours.

## Quick reference: which file for which question

A lookup table for the "Likely questions from the professor" sections, since the demo presentation will probably get one or two of these:

| Probable question (paraphrased) | File |
|---------------------------------|------|
| "Why does Vietnamese cost more tokens than English?" | [01](01-tokens-and-tokenization.md) |
| "Why is attention O(n²)?" / "What is Flash Attention?" | [02](02-context-window-and-attention.md) |
| "What is an embedding?" / "How does the model 'understand' meaning?" | [03](03-embeddings-and-vector-space.md) |
| "How many layers in this model?" / "What is multi-head attention?" | [04](04-transformer-architecture.md) |
| "Why is GPT decoder-only?" / "What was the original Transformer for?" | [05](05-decoder-only-vs-encoder-decoder.md) |
| "How does the model remember previous turns?" | [06](06-stateless-api-and-chat-format.md) |
| "How big is the model?" / "Does it fit?" | [07](07-model-parameters-and-vram.md) |
| "Why didn't you quantize the model?" / "What is AWQ?" | [08](08-quantization.md) |
| "How does the model run across two GPUs?" / "What is `--tensor-parallel-size`?" | [09](09-tensor-parallelism.md) |
| "Why vLLM and not Ollama?" / "What is PagedAttention?" | [10](10-vllm-vs-ollama.md) |
| Any unfamiliar term | [glossary.md](glossary.md) |

## Rule of thumb when updating

Per `AGENTS.md` Rule A and Rule B:

- Every new technical claim added to these files needs an official source citation at the bottom.
- If a vLLM flag, model spec, or API field is referenced, verify it against current docs (re-fetch if the file's "accessed" date is > 30 days old).
- When introducing a new technology (e.g., adding RAG, fine-tuning, distillation), add a new `NN-topic.md` here, and append a row to `docs/reference/INDEX.md`.

## Verification status of previously flagged claims

All three claims from the first pass have been resolved (web-verified 2026-05-17):

- [01] **Vietnamese tokens-per-word**: the specific "~1.5–2.0" range was not found in a primary source. The table was rewritten to make a *qualified* claim (Vietnamese sits between English and CJK on Latin-script-with-diacritics tokenizers; Qwen 3.6's 248K vocab is favorable; exact fertility requires direct measurement). Petrov et al. (2023, arxiv 2305.15425) cited for the general cross-language disparity claim.
- [04] **Gated DeltaNet citation** confirmed: Yang, Kautz, Hatamizadeh, *"Gated Delta Networks: Improving Mamba2 with Delta Rule"*, ICLR 2025 (arxiv 2412.06464). The placeholder citation 2312.06635 was incorrect and has been replaced.
- [06] **`Qwen/Qwen3.6-27B-Instruct` confirmed not to exist.** The official Qwen namespace for this size publishes `Qwen/Qwen3.6-27B` (base, fused thinking + instruct) and `Qwen/Qwen3.6-27B-FP8` (FP8 quant). The repo name in `.env.example` was corrected from `Qwen/Qwen3.6-27B-Instruct` to `Qwen/Qwen3.6-27B`.

No remaining `[UNVERIFIED]` or `[PARTIALLY VERIFIED]` markers in this knowledge base.

## Vietnamese annotations [in brackets]

Where used in the body, brackets like `[bộ_xử_lý: processor]` translate tricky English math/CS terms inline. The main text is English (matches the lab notebook tradition and the demo presentation language).
