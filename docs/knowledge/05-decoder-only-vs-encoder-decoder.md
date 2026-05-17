# 05 — Decoder-Only vs Encoder-Decoder

## Core idea (1-2 sentences)

The 2017 Transformer had two halves: an *encoder* that read the source and a *decoder* that wrote the target. Modern LLMs throw away the encoder entirely and use a single decoder that reads its own input and writes its continuation. Both input and output are one unified token stream.

## Why it matters for our project

Our agent's protocol is "send a list of messages, get a continuation". That's a decoder-only assumption — the model treats everything (system prompt, user turn, tool result, prior reasoning) as one stream of tokens to be continued. Understanding *why* that works tells us why we don't need a separate encoder pass, why few-shot prompting works, and why instruction tuning is "just more next-token training."

## The intuition

- **Encoder-decoder** is a translator working from notes. They read the whole source paragraph (encoder), then write the translation from scratch (decoder), able to glance back at the notes.
- **Decoder-only** is someone writing a story. They look at what's been written so far — by themselves or by someone else — and write the next sentence. There's no "source" vs "target". It's all one document.

The decoder-only insight: if your model is *good enough* at predicting the next token, "translation", "summarization", "tool calling", and "coding" all become continuations of an appropriately prefixed stream.

## The mechanics

### The original 2017 architecture — encoder + decoder

Designed for machine translation (English → German).

- **Encoder** (6 stacked blocks): self-attention only (every source token attends to every other source token, bidirectionally). Output: contextual embeddings of the source.
- **Decoder** (6 stacked blocks): each block has **three** sub-layers:
  1. *Masked* self-attention: each target token attends to earlier target tokens only (causal mask)
  2. Cross-attention: each target token attends to **all encoder outputs** (this is the "glance back at notes")
  3. Feed-forward network

The decoder produces the target sequence one token at a time. Cross-attention is the bridge from source to target.

### BERT (2018) — encoder-only

Devlin et al. realized the encoder half is great for *understanding* tasks. They:
- Threw out the decoder
- Trained the encoder with masked language modeling (predict a hidden word from its surroundings)
- Got SOTA on classification, NER, question answering

But BERT cannot *generate*: it has no causal mask and no autoregressive head.

### GPT (2018, OpenAI) — decoder-only

Radford et al. went the other way:
- Threw out the encoder
- Trained only the decoder
- Removed cross-attention (no encoder to cross-attend to)
- Pre-trained on next-token prediction over a huge text corpus

The result was a generator, and it generalized to a *staggering* range of tasks just by prefixing the right context. "Translate to French: Hello world →" produces French output, even though the model was never explicitly trained on translation.

### Why decoder-only won for general LLMs

By ~2020 the field converged on decoder-only for LLMs (GPT-3, PaLM, Llama, Qwen). Reasons:

1. **Unified interface**: input and output are the same token stream. No separate "source" and "target" formats. Easier to do few-shot prompting, instruction following, multi-turn chat.
2. **Better scaling**: at the same parameter count, decoder-only trained on next-token prediction beats encoder-decoder on most generative tasks, empirically. Some papers debate the exact margin but the consensus held.
3. **Simpler training data**: any text corpus works. No need for source-target pairs (translation datasets).
4. **Tool use, agents, code**: all naturally fit the "continue this stream" framing.

### What remains encoder-only or encoder-decoder

- **Sentence embedding models** (BERT, all-MiniLM): encoder-only. Used for retrieval (see [03-embeddings-and-vector-space.md](03-embeddings-and-vector-space.md)).
- **T5, BART, Flan-T5**: encoder-decoder. Still used for structured generation tasks.
- **Vision-language models**: often have an image encoder (ViT) + text decoder (LLM). The "encoder" here processes images, not text.

### Causal mask — the one thing that makes decoder-only "decoder-only"

In a decoder, the attention computation is masked so token at position i can only attend to positions ≤ i. This is the *only* structural difference from a bidirectional encoder. Everything else (FFN, residuals, layer norm) is identical.

```text
attention_score[i, j] = -infinity   if j > i
attention_score[i, j] = Q_i · K_j   otherwise
```

After softmax, the future is masked to zero. This enables training in parallel (compute the loss for all positions in one forward pass) while still respecting "you only know the past" at inference.

## Concrete numbers for our setup

- Qwen 3.6-27B: **decoder-only** (causal attention). Standard for the Llama/Qwen/GPT lineage.
- We do not separately encode user input vs assistant output — both flow through the same 64 layers as one stream.
- The chat template (special tokens like `<|im_start|>system`, `<|im_end|>`) is what tells the model "this part is the system role, this is user, this is assistant". See [06-stateless-api-and-chat-format.md](06-stateless-api-and-chat-format.md).

## Likely questions from the professor

**Q: Why don't modern LLMs use an encoder for the user's prompt and a decoder for the response?**
A: They could, but decoder-only is simpler and trains on any text. Empirically, with enough scale, the gap between decoder-only and encoder-decoder for generation tasks closed and then reversed in decoder-only's favor.

**Q: How does a decoder-only model "understand" the input if it never has bidirectional attention on it?**
A: The input tokens are processed by the same causal layers. Each input token can attend to all earlier input tokens. Information flows forward through the sequence. The model has effectively *summarized* the input by the time it gets to the position where it must generate. Empirically this works extremely well at scale.

**Q: Why is the original Transformer paper still cited if nobody uses encoder-decoder for LLMs?**
A: The paper introduced (a) self-attention, (b) multi-head attention, (c) positional encoding, (d) the layer/residual structure — all of which are *still* the foundation of modern decoder-only models. The architectural simplification (drop the encoder) is independent of those contributions.

**Q: Could you use BERT as a coding agent's brain?**
A: Not directly — BERT can't generate. You'd need to bolt a decoder on top, which is essentially T5. For our project a decoder-only LLM is the right choice.

**Q: Does Qwen 3.6's hybrid Gated DeltaNet architecture change the encoder vs decoder picture?**
A: No. Gated DeltaNet is still causal (left-to-right). It's a different *implementation* of attention but preserves the decoder-only structure. See [04-transformer-architecture.md](04-transformer-architecture.md).

## Common misconceptions / gotchas

- **"Decoder-only means the model only generates and doesn't read."** Wrong. Decoder-only models read AND generate; "decoder" refers to the *type of attention masking* (causal), not whether the model handles input.
- **"GPT was the first decoder-only model."** GPT-1 popularized it for LLMs but the technique existed before (e.g., neural language models predating Transformer). What GPT did was scale it.
- **"Encoder-decoder is obsolete."** Not in all domains — T5-family models are still useful for highly structured tasks. The dominance of decoder-only is specifically for *general-purpose* LLMs.
- **Previously confused with autoregressive vs autoencoding**: Autoregressive = predict next token (GPT-style, decoder-only). Autoencoding = predict masked tokens from surroundings (BERT-style, encoder-only). The two characterize the *training objective*; decoder-only / encoder-only characterize the *architecture*. They go together: autoregressive ⇔ decoder-only; autoencoding ⇔ encoder-only.

## Sources

- Vaswani et al., "Attention Is All You Need" (original encoder-decoder Transformer, 2017): https://arxiv.org/abs/1706.03762
- Devlin et al., "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding" (encoder-only, 2018): https://arxiv.org/abs/1810.04805
- Radford et al., "Improving Language Understanding by Generative Pre-Training" (GPT-1, decoder-only, 2018): https://cdn.openai.com/research-covers/language-unsupervised/language_understanding_paper.pdf
- Raffel et al., "Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer" (T5, encoder-decoder): https://arxiv.org/abs/1910.10683
- Wang et al., "What Language Model Architecture and Pretraining Objective Work Best for Zero-Shot Generalization?" (comparison study): https://arxiv.org/abs/2204.05832
