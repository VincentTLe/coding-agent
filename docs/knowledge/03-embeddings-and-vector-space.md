# 03 — Embeddings and Vector Space

## Core idea (1-2 sentences)

An embedding maps each token ID to a fixed-size vector of real numbers. The geometry of these vectors — directions, distances, clusters — is where the model stores semantic meaning.

## Why it matters for our project

The agent's tools may include semantic search over a codebase or doc corpus (RAG). That's vector-space arithmetic. Even without RAG, understanding embeddings explains *why* the model can generalize ("write a fibonacci function" → it has never seen this exact request, but the request's vector lives near other code-generation requests).

## The intuition

Imagine a 5,120-dimensional warehouse where every word, code identifier, and concept gets placed at a specific address. Words that mean similar things end up near each other (`run`, `execute`, `invoke` cluster together). Relationships between words are *directions* in the warehouse: the direction from `man` to `king` is parallel to the direction from `woman` to `queen`. Adding vectors moves you along these directions. The model's whole job becomes: given a sequence of addresses, predict the next address.

## The mechanics

### Static embeddings (Word2Vec, 2013) — the historical starting point

Mikolov et al. trained shallow networks to predict context words from a target word (Skip-gram) or vice versa (CBOW). The training signal forced semantically related words to land near each other. The famous result:

```text
embedding("king") - embedding("man") + embedding("woman") ≈ embedding("queen")
```

**Caveat that matters**: in the original demonstration, the input words were *excluded* from the nearest-neighbor search. Without that exclusion, the closest vector to `king − man + woman` is often `king` itself, because the perturbation is small. The example is real but it's a constructed near-neighbor result, not arithmetic magic.

### Contextual embeddings (Transformer-era)

Word2Vec gives each word *one* fixed vector. The Transformer does something more powerful: every position's vector depends on its surroundings. The token `bank` has different vectors in "river bank" vs "investment bank". Concretely:

1. Token ID → static embedding lookup (one row from a 248,320 × 5,120 table for Qwen 3.6-27B).
2. Each layer rewrites that vector based on attention over the rest of the sequence.
3. After 64 layers, the final vector is a position-and-context-specific representation, much richer than Word2Vec ever produced.

So the *input embedding* is static, but the *internal representations* are contextual. When people say "the embedding of a sentence" today, they usually mean the contextual hidden state from some layer, not Word2Vec.

### Why multilingual works in one model

Modern tokenizers (byte-level BPE for Qwen, Llama) cover all UTF-8 byte sequences, so they handle every language. The model learns that, say, `chien` (French), `chó` (Vietnamese), `犬` (Japanese), and `dog` (English) co-occur with the same surrounding concepts during training, so they end up near each other in vector space. Translation, cross-lingual retrieval, and cross-lingual reasoning fall out naturally.

This is why a single Qwen 3.6-27B model speaks ~100 languages without per-language fine-tuning.

### Vector arithmetic and analogy

The most useful property for our project: **vector subtraction captures relationships**. If you embed "fix the bug" and "fix the typo", the difference vector roughly encodes "what is being fixed". This is the mechanism underneath:

- Semantic search (cosine similarity between query vector and document vectors)
- Few-shot prompting (the model finds the *pattern* across examples)
- Retrieval-augmented generation (RAG)

### Connection to vector databases (one paragraph)

If we later want our agent to search a large codebase, we precompute an embedding for each file (or chunk). At query time, embed the question and run nearest-neighbor search (FAISS, Qdrant, Milvus, pgvector). The retrieved chunks become context for the model. Embedding for retrieval is usually done by a *separate* dedicated embedding model (e.g., `bge-large`, `all-MiniLM-L6-v2`) — not the 27B generation model, which would be wasteful and slow. We have `sentence-transformers/all-MiniLM-L6-v2` in our HF cache already.

## Concrete numbers for our setup

- Qwen 3.6-27B input embedding dimension: **5,120**
- Vocabulary: **248,320 tokens** → embedding table = **248,320 × 5,120 = 1.27 billion parameters** (≈ 2.54 GB in BF16)
- Common retrieval embedding model (already cached on this server): `sentence-transformers/all-MiniLM-L6-v2` → **384-dimensional** vectors, ~22 MB model
- A 5,120-dim float32 vector is 20 KB. A million such vectors is 20 GB — not stored verbatim for RAG; you'd use a smaller dedicated embedding model and approximate-NN indices.

## Likely questions from the professor

**Q: Are embeddings the same thing as the hidden states inside the Transformer?**
A: Not quite. *Input embeddings* are the first step — pure lookup from the vocab table. *Hidden states* are what attention layers produce — contextual transformations of those input embeddings. People often use "embedding" loosely to mean either; be precise about which.

**Q: Why are these vectors 5,120-dimensional and not 50 or 5,000,000?**
A: It's a hyperparameter chosen at design time. Too small and the model can't represent enough distinctions; too large and you waste compute. The choice scales with model size — small models use 768 or 1,024, large frontier models use 8,192 or more. 5,120 is mid-range for a 27B model.

**Q: Can I compute "function − loop + recursion" and get something meaningful?**
A: Sometimes, with caveats. Vector arithmetic works best for *symmetric* relations (capital-of, gender, tense). Code concepts are noisier. The right thing for a coding agent is usually full sentence/file embedding + similarity search, not single-word arithmetic.

**Q: Why does our project use a smaller embedding model for RAG rather than Qwen 3.6-27B itself?**
A: Three reasons. (1) Speed — `all-MiniLM-L6-v2` embeds ~10,000 sentences/sec on one A6000, the 27B can't. (2) Cost — each retrieval embed of a long doc would cost as much as a model forward pass. (3) Specialization — embedding models are trained with a contrastive objective specifically for retrieval, which Qwen 3.6-27B is not.

**Q: Is the embedding "the meaning" of a word?**
A: It's a learned proxy for meaning that is good enough for the model's downstream task. It is not philosophical meaning; it is statistical co-occurrence compressed into 5,120 dimensions.

## Common misconceptions / gotchas

- **"Embeddings are unique per word."** True for Word2Vec; *false* for Transformer-internal representations. Contextual embeddings differ by position and surrounding tokens.
- **"king − man + woman = queen" is exact.** No — it's the *second* nearest neighbor (the first is usually `king` itself unless input words are excluded). The general claim "analogies are encoded as directions" is true; the specific arithmetic equality is a demonstration with caveats.
- **"All embeddings are interchangeable."** No. An embedding from Qwen 3.6-27B's layer 30 has no meaning in a Llama-3 model. Embeddings are model-specific.
- **Previously confused with token IDs**: Token = integer (e.g., 7234). Embedding = vector (e.g., 5,120 floats). The mapping is the first matrix in the model.

## Sources

- Mikolov et al., "Efficient Estimation of Word Representations in Vector Space" (Word2Vec architectures): https://arxiv.org/abs/1301.3781 (accessed 2026-05-17)
- Mikolov, Yih, Zweig, "Linguistic Regularities in Continuous Space Word Representations" (where the king-man+woman=queen demonstration is from): https://aclanthology.org/N13-1090/
- Plotly blog on the caveat that input words are excluded: https://medium.com/plotly/understanding-word-embedding-arithmetic-why-theres-no-single-answer-to-king-man-woman-cd2760e2cb7f (accessed 2026-05-17)
- Devlin et al., "BERT" (contextual embeddings): https://arxiv.org/abs/1810.04805
- Qwen 3.6-27B model card (hidden dim 5,120): https://huggingface.co/Qwen/Qwen3.6-27B (accessed 2026-05-17)
- Sentence-Transformers documentation (retrieval embedding models): https://www.sbert.net/
