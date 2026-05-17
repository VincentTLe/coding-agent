# 04 — Transformer Architecture

## Core idea (1-2 sentences)

A Transformer is a stack of identical blocks, where each block does two things: **attention** (mix information across positions) and a **feed-forward network** (refine each position independently). The whole model is just this stack applied many times.

## Why it matters for our project

We're not implementing a Transformer from scratch — that's a different project. But the agent's behavior is shaped by what each layer does: early layers handle syntax, mid layers handle entities, late layers handle reasoning. When the agent fails, knowing *where* in the stack a failure likely originates helps debugging (e.g., long-context failures often live in attention; instruction-following failures live in the FFN).

## The intuition

Picture a factory assembly line. A car enters at one end. Each station does two operations:

1. **Look around** (attention): "Compare myself to the other 200 things currently on the line, and absorb relevant info."
2. **Refine yourself** (FFN): "Apply my station's specialized transformation, just based on what I now know."

After 64 stations, the thing that exits is a fully transformed representation, ready to predict the next token. Every station has its own learned tools, but the *shape* of the work — look around, refine — is identical at every station.

## The mechanics

### One Transformer block, decoder-only variant (what GPT/Llama/Qwen use)

```text
Input: x  (sequence of 5,120-dim vectors, one per token)

x' = x + Attention(LayerNorm(x))         # mix across positions
x'' = x' + FFN(LayerNorm(x'))            # refine each position
```

Two residual connections (`+ x`, `+ x'`) — this is the "highway" that lets gradients flow through deep stacks and lets information skip layers if needed.

### Self-attention (the "look around")

Computed three times per block: Q, K, V. Multi-head means you run several smaller attention computations in parallel:

- 24 attention heads (in Qwen 3.6's Gated Attention layers, head_dim = 256)
- Each head looks at a different *aspect* of the sequence: one might track syntactic dependencies, another track entity coreference, another semantic similarity
- Outputs are concatenated and projected back to the model dimension

See [02-context-window-and-attention.md](02-context-window-and-attention.md) for the math.

### Feed-forward network (the "refine yourself")

For each position independently:

```text
FFN(x) = W_2 · activation(W_1 · x)
```

The "intermediate dimension" (FFN width) is typically 3–4× the model dim. For Qwen 3.6-27B: hidden_dim 5,120 → intermediate 17,408 → back to 5,120. SwiGLU activation (a gated variant) is standard in modern LLMs.

Most of the parameter count in a Transformer lives in the FFN, not attention. For Qwen 3.6-27B, the FFN per layer is `2 × 5,120 × 17,408 ≈ 178 M params/layer × 64 layers = 11.4 B params` — a big chunk of the 27B total.

### Layer norm — keeping numbers sane

Before attention and before FFN, the vectors are normalized (LayerNorm or RMSNorm) to keep activations from blowing up or vanishing across 64 deep layers. Without it, training a deep stack is numerically impossible.

### Position information

Plain attention is *permutation-invariant* — it has no notion of "earlier" or "later". So we inject position via:

- **Sinusoidal position embeddings** (original Transformer, 2017): add a fixed periodic function of position to each input embedding.
- **Rotary Position Embedding (RoPE)** (used by Llama, Qwen): rotate Q and K vectors by an angle proportional to position. Qwen 3.6-27B uses RoPE with rotary dim = 64.

### What makes Qwen 3.6-27B different from a textbook Transformer

This is important: **Qwen 3.6-27B is NOT a pure standard Transformer.** It uses a *hybrid attention architecture*:

```text
Hidden layout: 16 × [3 × (Gated DeltaNet → FFN) → 1 × (Gated Attention → FFN)]
Total: 64 layers
```

- **Gated DeltaNet**: a *linear attention* variant — O(n) in sequence length, not O(n²). Recurrent-state-style; tracks information with a learned forgetting mechanism. 48 V-heads, 16 QK-heads, head_dim 128.
- **Gated Attention**: standard softmax attention. 24 Q-heads, 4 KV-heads (Grouped-Query Attention), head_dim 256. Only every 4th layer.

Why this matters: this hybrid lets the model handle 262K tokens efficiently — the bulk of attention is linear-time, only 1-in-4 layers pay the quadratic cost. This is a 2025-2026 trend (Jamba, Mamba-based models, Falcon Mamba). Mention this in the presentation as a "modern architectural choice we use."

## Concrete numbers for our setup

| Spec                       | Qwen 3.6-27B |
|---------------------------|--------------|
| Total parameters          | 27 B         |
| Layers                    | 64           |
| Hidden dim                | 5,120        |
| FFN intermediate dim      | 17,408       |
| Native context            | 262,144      |
| Tokenizer vocab           | 248,320      |
| Weight dtype              | BF16         |
| Total weight size         | ~54 GB       |
| Standard attention layers | 16 (1 of every 4) |
| Linear-attention layers   | 48 (3 of every 4, Gated DeltaNet) |
| RoPE rotary dim           | 64           |

(All from the official Qwen 3.6-27B Hugging Face model card.)

## Likely questions from the professor

**Q: Why 64 layers and not 32 or 128?**
A: It's the depth that balanced quality and training compute for this parameter budget at Alibaba's training scale. Doubling depth halves the width for the same parameter count; the optimal aspect ratio is empirical and Qwen 3.6 chose this point.

**Q: Why does Qwen 3.6 use a hybrid linear-attention architecture?**
A: To scale to long context. Pure softmax attention costs O(n²) memory in KV cache; linear attention costs O(1) per token (constant-size hidden state). Mixing 3:1 keeps most of the long-context efficiency while preserving full attention's expressiveness for the layers that need it.

**Q: What does each layer "specialize" in?**
A: Empirically (from interpretability research): early layers — token-level / syntactic features; middle layers — entity, coreference, semantic features; late layers — task-specific reasoning, instruction-following. But this is a generalization; modern models don't draw clean boundaries.

**Q: What is a "head" doing exactly?**
A: Each head is an independent attention computation with its own Q, K, V projections. The intuition: different heads attend to different relationships. One head might track "next punctuation"; another "subject of the verb"; another "earlier mention of this entity". Empirically most heads are not so interpretable, but the math allows for this division of labor.

**Q: Is "decoder-only" the same as "GPT-style"?**
A: Yes — decoder-only refers to causal (left-to-right) attention. GPT-1 was the first major decoder-only LLM; the term is shorthand for that lineage. See [05-decoder-only-vs-encoder-decoder.md](05-decoder-only-vs-encoder-decoder.md).

## Common misconceptions / gotchas

- **"Transformer = LLM."** No. Transformer is the architecture. An LLM is a *trained* Transformer (or hybrid Transformer like Qwen 3.6) optimized on next-token prediction at scale. ViT, BERT, T5 are also Transformers but very different beasts.
- **"All layers are the same."** True for parameter count and structure; *false* for what they learn. They share architecture, not function.
- **"Attention is the only smart part; FFN is just a perceptron."** Misleading. Most parameters and most learned associations live in the FFN. Recent interpretability work treats FFN layers as key-value memories.
- **"Qwen 3.6 is a standard Transformer."** No — it's a *hybrid* with linear attention layers. This is a non-obvious detail that may come up in the presentation. The owner should be ready to explain Gated DeltaNet at a high level.
- **Previously confused with depth of training vs depth of model**: 64 layers is the *forward-pass depth*. Training compute (FLOPs) is depth × width × tokens, which is much larger.

## Sources

- Vaswani et al., "Attention Is All You Need" (original Transformer): https://arxiv.org/abs/1706.03762
- Qwen 3.6-27B model card (full architectural specs): https://huggingface.co/Qwen/Qwen3.6-27B (accessed 2026-05-17)
- Shazeer, "GLU Variants Improve Transformer" (SwiGLU activation): https://arxiv.org/abs/2002.05202
- Su et al., "RoFormer: Enhanced Transformer with Rotary Position Embedding" (RoPE): https://arxiv.org/abs/2104.09864
- Yang, Kautz, Hatamizadeh, "Gated Delta Networks: Improving Mamba2 with Delta Rule" (ICLR 2025) — the paper introducing the Gated DeltaNet mechanism used in Qwen 3.6: https://arxiv.org/abs/2412.06464 (accessed 2026-05-17). The Qwen 3.6 model card itself does not cite a paper but uses the same name and architecture from this work.
- Ainslie et al., "GQA: Training Generalized Multi-Query Transformer Models from Multi-Head Checkpoints" (Grouped-Query Attention, used in Qwen 3.6's Gated Attention layers): https://arxiv.org/abs/2305.13245
