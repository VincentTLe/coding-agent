# Glossary

Terse definitions, cross-referenced to the numbered notes. Alphabetical.

---

**Activation** — The output of a layer (after attention or FFN) at a particular position. Transient; lives in GPU memory only during the forward pass. Different from a *weight*, which is permanent.

**All-reduce** — A collective communication operation where every GPU contributes a tensor and every GPU receives the sum of all contributions. Performed once per layer (twice, actually — after attention and after FFN) in tensor parallelism. See [09](09-tensor-parallelism.md).

**Attention** — The mechanism by which each token in a sequence computes a weighted sum over (representations of) all other tokens. Quadratic in sequence length naively; linearized in time via Flash Attention's memory tricks and in some architectures via linear attention (e.g., Gated DeltaNet). See [02](02-context-window-and-attention.md), [04](04-transformer-architecture.md).

**AWQ (Activation-aware Weight Quantization)** — A 4-bit weight quantization method that preserves precision for the channels with the largest activation magnitudes on a calibration dataset. Industry-standard INT4 method. See [08](08-quantization.md).

**Batching** — Running multiple requests through the model in one forward pass. *Static* batching waits for a fixed batch; *continuous* batching adds/removes requests at every iteration. See [10](10-vllm-vs-ollama.md).

**BF16 (bfloat16)** — 16-bit floating-point format with 8 exponent bits and 7 mantissa bits. Same dynamic range as FP32, less precision than FP16. Default training and inference precision for modern LLMs. 2 bytes per number. See [07](07-model-parameters-and-vram.md).

**Bias** — A constant added to a weighted sum inside a layer. One of the two types of trainable parameters (the other is weights). Usually has many fewer parameters than weight matrices.

**BPE (Byte-Pair Encoding)** — Subword tokenization algorithm that iteratively merges the most frequent adjacent symbol pairs. Used by Qwen, Llama, GPT. Byte-level BPE operates on raw bytes (handles any UTF-8 string). See [01](01-tokens-and-tokenization.md).

**Causal mask** — In decoder-only attention, the mask preventing each token from attending to future positions. Implemented as `-inf` scores for positions > current. The single structural difference between encoder-only and decoder-only Transformers. See [05](05-decoder-only-vs-encoder-decoder.md).

**Chat template** — The string format that wraps a list of messages into the single token stream the model was trained on. Includes special turn markers (e.g., `<|im_start|>user`). Stored per model in the tokenizer config. See [06](06-stateless-api-and-chat-format.md).

**Context window** — The maximum sequence length the model can process in one forward pass. Fixed at training time; can be stretched with techniques like YaRN. Qwen 3.6-27B: 262,144 native. See [02](02-context-window-and-attention.md).

**Continuous batching** — Iteration-level scheduling that adds requests to and removes from the batch at every token step. Introduced by Orca (OSDI 2022). vLLM uses it by default. See [10](10-vllm-vs-ollama.md).

**Cross-attention** — Attention where Q comes from one sequence and K, V come from another. Present in the original encoder-decoder Transformer (decoder attending to encoder output); absent in decoder-only models. See [05](05-decoder-only-vs-encoder-decoder.md).

**Decoder-only** — Architecture using only causal self-attention; no encoder, no cross-attention. The dominant LLM architecture (GPT, Llama, Qwen, Mistral). See [05](05-decoder-only-vs-encoder-decoder.md).

**Embedding** — A fixed-size vector (e.g., 5,120-dim for Qwen 3.6-27B) representing a token or, contextually, a position within a sequence. The input layer of a Transformer is a lookup table from token IDs to embeddings. See [03](03-embeddings-and-vector-space.md).

**Encoder-decoder** — Original Transformer architecture (Vaswani 2017): encoder processes source bidirectionally; decoder generates target with cross-attention to the encoder. Still used for some tasks (T5, BART). See [05](05-decoder-only-vs-encoder-decoder.md).

**Encoder-only** — Bidirectional Transformer used for understanding tasks (classification, NER, embedding). BERT-family. Cannot generate. See [05](05-decoder-only-vs-encoder-decoder.md).

**FFN (Feed-Forward Network)** — The position-wise dense transformation inside each Transformer block: typically two linear layers with a nonlinearity in between (and a gate, for SwiGLU). Contains the majority of a Transformer's parameters. See [04](04-transformer-architecture.md).

**Flash Attention** — A reformulation of attention that fuses operations and tiles them through fast GPU SRAM, reducing peak memory from O(n²) to O(n) without changing the result. FlashAttention-2 also improves parallelism across thread blocks. See [02](02-context-window-and-attention.md).

**FP8** — 8-bit floating-point format. Native on Hopper (H100) and newer; emulated on Ampere (A6000). 1 byte per number. Used for inference and increasingly training. See [08](08-quantization.md).

**FP16 (float16, IEEE binary16)** — 16-bit float with 5 exponent and 10 mantissa bits. Smaller dynamic range than BF16; more precise. 2 bytes. Native on most modern GPUs. See [07](07-model-parameters-and-vram.md).

**FP32** — 32-bit IEEE single-precision float. 4 bytes. Standard precision for non-NN compute. Models almost never stored in FP32 in 2026.

**Gated Attention** — In Qwen 3.6, the standard-attention variant (vs Gated DeltaNet). Uses Grouped-Query Attention (24 Q-heads, 4 KV-heads, head_dim 256). One in every four layers. See [04](04-transformer-architecture.md).

**Gated DeltaNet** — Qwen 3.6's linear-attention variant. Recurrent-state-style mechanism that scales O(n) in sequence length. Three in every four layers of Qwen 3.6-27B. See [04](04-transformer-architecture.md).

**GGUF** — A file format (used by llama.cpp / Ollama) that supports many quantization levels and stores all model metadata in one file. Not a quantization algorithm itself. See [08](08-quantization.md), [10](10-vllm-vs-ollama.md).

**GPTQ** — A 4-bit weight quantization method that iteratively minimizes layer-wise reconstruction error. Pre-AWQ industry standard; still widely used. See [08](08-quantization.md).

**Grouped-Query Attention (GQA)** — Attention variant where multiple Q-heads share the same K and V heads. Reduces KV cache memory at minimal quality cost. Used in Qwen 3.6's Gated Attention layers (24 Q-heads share 4 KV-heads).

**Head (attention head)** — One of the independent parallel attention computations within multi-head attention. Each head has its own Q, K, V projections. Different heads tend to specialize in different relationships. See [04](04-transformer-architecture.md).

**Head dimension (`head_dim`)** — Size of the Q/K/V vector *per head*. For Qwen 3.6: 128 in Gated DeltaNet, 256 in Gated Attention.

**Hidden dimension (`hidden_dim`, `d_model`)** — The size of the vector representation flowing between layers. For Qwen 3.6-27B: 5,120. See [04](04-transformer-architecture.md).

**INT4** — 4-bit integer storage for weights, with a per-block scale factor restoring approximate precision. Typically paired with AWQ or GPTQ algorithms. 0.5 bytes per parameter. See [08](08-quantization.md).

**INT8** — 8-bit integer with scale factors. 1 byte per parameter. Used for older quantization paths (SmoothQuant); FP8 is preferred where supported. See [08](08-quantization.md).

**Iteration-level scheduling** — The technical name for what continuous batching does: scheduling decisions made at every token step rather than every request. See [10](10-vllm-vs-ollama.md).

**KV cache** — The Key and Value tensors stored from previous forward passes during autoregressive generation, so they don't have to be recomputed. Scales linearly with sequence length and proportionally with model size. The main memory cost beyond model weights. See [02](02-context-window-and-attention.md), [07](07-model-parameters-and-vram.md).

**Layer** — In a Transformer, one block of (attention + FFN). The model is a stack of identical layers. Qwen 3.6-27B has 64 layers. See [04](04-transformer-architecture.md).

**LayerNorm / RMSNorm** — Per-position normalization applied before attention and before FFN, keeping activations numerically stable across deep stacks. RMSNorm (used in Llama, Qwen) is a cheaper variant of LayerNorm.

**Linear attention** — Attention computed in O(n) instead of O(n²) by reordering matrix products or using kernel approximations. Gated DeltaNet is a recent example. Sacrifices some expressiveness for scalability. See [04](04-transformer-architecture.md).

**Logit** — The raw, pre-softmax output score for a token. The model outputs one logit per vocabulary entry (248,320 for Qwen 3.6); softmax converts these to a probability distribution.

**NVLink** — NVIDIA's high-bandwidth GPU-to-GPU interconnect. RTX A6000 (Ampere) supports 3rd-gen NVLink at 112 GB/s aggregate when bridged in pairs. Critical for tensor parallelism's all-reduces. See [09](09-tensor-parallelism.md).

**OpenAI-compatible API** — An HTTP API matching OpenAI's `/v1/chat/completions` (and friends) schema. vLLM exposes one; client code can switch between OpenAI's servers, vLLM, and many others without changes. See [06](06-stateless-api-and-chat-format.md), [10](10-vllm-vs-ollama.md).

**PagedAttention** — vLLM's KV cache management technique, modeled on OS virtual memory: fixed-size blocks, indirection table per request, near-zero fragmentation. Introduced by Kwon et al., SOSP 2023. See [10](10-vllm-vs-ollama.md).

**Parameter** — A single trainable scalar in the model (a weight or a bias). Qwen 3.6-27B has 27 billion. Each takes 2 bytes in BF16. See [07](07-model-parameters-and-vram.md).

**Pipeline parallelism** — Splitting the model *across layers* across GPUs (vs tensor parallelism which splits *within* layers). Better when NVLink is absent; introduces a pipeline bubble at the start/end of batches. See [09](09-tensor-parallelism.md).

**Prefix caching** — Storing the KV cache for a frequently-reused prefix (e.g., the system prompt) so it doesn't have to be recomputed on every request. Supported by vLLM. See [06](06-stateless-api-and-chat-format.md), [10](10-vllm-vs-ollama.md).

**Quantization** — Replacing high-precision weights (BF16) with lower-precision approximations (FP8, INT4) to save memory and bandwidth, at some accuracy cost. See [08](08-quantization.md).

**RoPE (Rotary Position Embedding)** — A way of injecting position information by rotating Q and K vectors by angles proportional to position. Used by Llama, Qwen. Supports context extension via interpolation (e.g., YaRN).

**Speculative decoding** — Using a smaller, faster "draft" model to propose tokens and a larger "target" model to verify, speeding up generation. Supported by vLLM. Not used in our project initially.

**State / hidden state** — The internal representation flowing through the Transformer's layers. Hidden state at the input is the token embedding; at the output it's the logits projection.

**Stateless API** — An API design where the server holds no per-request memory across calls. Every call must include all needed context. OpenAI-compatible APIs (including vLLM's) are stateless. See [06](06-stateless-api-and-chat-format.md).

**System prompt** — The first message in a chat history, role=`system`, used to set the model's behavior, persona, available tools, and constraints. Resent every turn (stateless API). See [06](06-stateless-api-and-chat-format.md).

**Tensor parallelism** — Splitting each layer's weight matrices across multiple GPUs, with all-reduce synchronization between layers. vLLM flag: `--tensor-parallel-size N`. See [09](09-tensor-parallelism.md).

**Token** — The unit the model consumes. A subword chunk produced by the tokenizer (BPE or SentencePiece). Identified by an integer ID. See [01](01-tokens-and-tokenization.md).

**Tokenizer** — The deterministic preprocessor that maps text → integer token IDs. Trained once, frozen for the model's lifetime. See [01](01-tokens-and-tokenization.md).

**Tool calling / function calling** — The convention where the assistant outputs structured JSON describing a function call instead of (or alongside) natural language. The client executes the tool, appends the result as a `role: "tool"` message, and re-calls the model. Foundation of agent loops. See [06](06-stateless-api-and-chat-format.md).

**Transformer** — The deep-learning architecture from Vaswani et al. 2017, based on stacked attention + FFN blocks. The foundation of all current major LLMs. See [04](04-transformer-architecture.md).

**vLLM** — High-throughput LLM serving system from UC Berkeley, built around PagedAttention. The serving stack we chose for this project. See [10](10-vllm-vs-ollama.md).

**Vocabulary size** — Number of distinct tokens in a model's tokenizer. Qwen 3.6-27B: 248,320 (padded).

**Weight** — One of the two types of trainable parameters (the other is *bias*). An element of a matrix that multiplies an input. Most parameters in a Transformer are weights.

**YaRN** — A technique for extending a model's effective context beyond its trained context length via positional interpolation. Qwen 3.6-27B uses YaRN to go from 262K native to ~1M extended.
