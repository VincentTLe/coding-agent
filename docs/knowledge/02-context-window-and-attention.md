# 02 — Context Window and Attention

## Core idea (1-2 sentences)

The *context window* is the maximum number of tokens the model can attend to in a single forward pass. It is fixed at training time and bounded by attention's quadratic memory cost.

## Why it matters for our project

Our agent's loop accumulates history — user message, tool calls, tool results, model thoughts. If the loop runs long, the prompt grows. Once we exceed the model's context window, the call simply fails (or, with vLLM, gets truncated, which is worse — silent context loss leading to wrong behavior). We need to know the limit, what eats the budget, and how to budget agent turns.

## The intuition

Imagine a meeting room. The context window is how many people can fit. Everyone in the room hears everyone else (that's *attention*). If 8 people are in the room, that's 8×8=64 pairs of conversations happening simultaneously. With 100 people, it's 10,000 pairs — the room is paralyzed by chatter. This O(n²) cost is the fundamental reason context isn't free.

## The mechanics

### What attention actually computes

For each token i, attention asks: "for every other token j in the sequence, how much should I care about j when computing the next state of i?" That weighting is computed as:

```text
Attention(Q, K, V) = softmax(Q · K^T / sqrt(d_k)) · V
```

- Q (queries): what each token is "looking for"
- K (keys): what each token "advertises"
- V (values): what each token "delivers" if attended to
- d_k: head dimension (e.g., 128 in Qwen 3.6-27B Gated DeltaNet, 256 in its Gated Attention)

### Why it is O(n²)

The matrix `Q · K^T` has shape `(n, n)` for sequence length n. Building it costs n² multiplications and n² floats of memory. At n = 262,144 (Qwen 3.6's native context), the raw score matrix would be 262,144² ≈ 6.9 × 10¹⁰ entries per attention head per layer — clearly impossible to materialize in memory naively.

This is a problem in **both time and memory** for naive implementations.

### Flash Attention — making memory linear

Flash Attention (Tri Dao et al.) restructures the computation so the `n × n` matrix is **never materialized**. It computes attention in *blocks* using the GPU's SRAM (small but fast) instead of HBM (large but slow), streaming partial results. Memory drops from O(n²) to **O(n)**. Time complexity stays O(n²) — that math is unavoidable — but the wall-clock time drops 2–4× because the SRAM/HBM dance is dramatically more cache-friendly.

FlashAttention-2 adds better parallelism across thread blocks and reaches 50–73% of theoretical FLOPs on an A100 (around 225 TFLOPs/s).

### KV cache — making generation linear instead of quadratic

When generating one token at a time, the naive cost per token is O(n²) — re-running attention over the whole sequence-so-far. The trick: the K and V for previously generated tokens *do not change*. So you cache them and only compute Q for the new token, attending against the cached K/V. Per-token cost drops to O(n).

The cost is **memory**. The KV cache size in bytes is roughly:

```text
KV_cache_bytes = 2 × seq_len × num_layers × kv_heads × head_dim × dtype_bytes
```

(The `2` is one for K, one for V.) For Qwen 3.6-27B at 32K context using its Gated Attention layers alone, this is non-trivial. See [07-model-parameters-and-vram.md](07-model-parameters-and-vram.md) for the full VRAM budget.

vLLM's **PagedAttention** is specifically a smarter KV cache manager — see [10-vllm-vs-ollama.md](10-vllm-vs-ollama.md).

### Why context length is fixed at training time

Three reasons:
1. **Position embeddings** (RoPE, ALiBi, etc.) are learned/configured for a specific max length. Going beyond produces undefined positional encoding.
2. The model was never *asked* to attend to longer distances during training, so its weights don't know what to do with them.
3. Linear-attention components (like Gated DeltaNet in Qwen 3.6-27B) are trained with specific decay/state-tracking behaviour that may degrade at longer sequences.

Techniques like YaRN, position interpolation, and self-extend can stretch a model trained at e.g. 32K to longer windows, often at some quality cost. Qwen 3.6-27B uses YaRN to advertise extensibility up to ~1,010,000 tokens.

### What happens when context fills up

- **OpenAI-compatible API (vLLM, OpenAI)**: a request whose prompt + max_tokens exceeds context returns HTTP 400 / a context-length error. No silent truncation.
- **Ollama with default config**: may *silently* truncate (cut off oldest tokens). This is dangerous in an agent loop because the model loses its system prompt without warning.
- **Best practice in our agent**: track running token count, leave a buffer (e.g., 20%), and explicitly summarize older turns when nearing the limit.

## Concrete numbers for our setup

- Qwen 3.6-27B **native** context: **262,144 tokens**
- Qwen 3.6-27B **extended via YaRN**: up to **~1,010,000 tokens** (model-card claim; quality typically drops past 2-3× native)
- Practical for our agent: we'll cap at 32–64K to keep KV cache modest and latency low
- Naive attention memory at 32K: 32,768² × 2 bytes ≈ **2 GB per head per layer**. With ~64 layers and multiple heads, would explode. Flash Attention (which vLLM uses by default) reduces this dramatically.

## Likely questions from the professor

**Q: What is the bottleneck — attention's compute or its memory?**
A: For training: memory was the bottleneck before Flash Attention; now it's compute. For inference of long sequences: KV cache memory is usually the bottleneck. For short sequences: matmul throughput dominates.

**Q: If attention is O(n²), how does Qwen 3.6 advertise a 262K-token window?**
A: Two reasons. (1) Flash Attention makes the *memory* linear, so 262K is feasible on a single GPU. (2) Qwen 3.6-27B uses a hybrid architecture where 3 of every 4 attention layers are **linear attention** (Gated DeltaNet), which scales O(n) in both time and memory. Only every fourth layer uses standard softmax attention.

**Q: Why does my agent slow down after many turns?**
A: KV cache grows linearly with conversation length. Each generated token attends against all previous K/V. Per-token cost is O(n), so total generation cost is O(n²) over the conversation.

**Q: Can we just throw away old turns?**
A: Yes, but the model loses information. Practical strategies: sliding window (drop oldest N turns), summarization (LLM-generated summary of dropped turns), or hierarchical memory (recent verbatim, older summarized).

**Q: Why is the system prompt sent every turn?**
A: The API is stateless (see [06-stateless-api-and-chat-format.md](06-stateless-api-and-chat-format.md)). The server has no memory between requests. To get consistent behavior, the client must resend the system prompt every time.

## Common misconceptions / gotchas

- **"Flash Attention makes attention O(n) in compute."** No — it's still O(n²) in FLOPs. The improvement is wall-clock time (better memory hierarchy use) and peak memory.
- **"KV cache is part of the model weights."** No — KV cache is per-request and grows during generation. Weights are fixed and shared across requests.
- **"262K context means I can stuff anything in there for free."** False. KV cache memory grows linearly with sequence length. Filling Qwen 3.6-27B to 262K eats much of the 96 GB VRAM budget.
- **Previously confused with parameter count**: Context window is *runtime input length*. Parameter count is *number of weights in the model*. They're related (long context needs more KV memory) but distinct.

## Sources

- Dao et al., "FlashAttention-2: Faster Attention with Better Parallelism and Work Partitioning": https://arxiv.org/abs/2307.08691 (accessed 2026-05-17)
- Dao et al., "FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness": https://arxiv.org/abs/2205.14135
- Vaswani et al., "Attention Is All You Need": https://arxiv.org/abs/1706.03762
- Qwen 3.6-27B model card (262K native context, hybrid attention): https://huggingface.co/Qwen/Qwen3.6-27B (accessed 2026-05-17)
- vLLM PagedAttention paper (KV cache management): https://arxiv.org/abs/2309.06180
