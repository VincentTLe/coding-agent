# 01 — Tokens and Tokenization

## Core idea (1-2 sentences)

A *token* is the chunk a language model actually consumes. Tokenization is the deterministic mapping `text ↔ integer IDs` performed before the model sees anything; the model itself never sees raw characters.

## Why it matters for our project

The agent's prompt budget, latency, and cost (when later compared to API models) are all measured in tokens. If we send a 4,000-word file as context, what hits the model is its *token count*, not its word count. Misjudging this is the #1 cause of "I thought 200K context was enough" failures.

## The intuition

Imagine a Scrabble bag of ~250,000 differently-shaped tiles, ordered by frequency. Common English words like `the`, `agent`, `code` each have their own tile. Rare technical words (`tokenization`, `tensorparallel`) don't — the model breaks them into 2-4 smaller tiles that *do* exist in the bag (`token`, `ization`, or `tens`, `or`, `parallel`). Languages that the bag's designer didn't optimize for end up using lots of tiny tiles for ordinary words.

The bag is built *once*, before training. It cannot grow at inference time.

## The mechanics

### Byte-Pair Encoding (BPE) — the algorithm behind most modern tokenizers

1. Start with characters (or raw bytes) as the initial vocabulary.
2. Count every pair of adjacent symbols in a training corpus.
3. Merge the most frequent pair into a new symbol. Add it to the vocabulary.
4. Repeat steps 2–3 until you reach the target vocabulary size.

Variants:
- **Byte-level BPE** (used by GPT-2 / GPT-3 / Llama / Qwen): operates on raw bytes (256 base symbols) instead of Unicode characters. Guarantees *any* string can be tokenized (no unknown tokens), even non-Latin scripts.
- **SentencePiece** (used by T5, Gemma): same merge idea, but treats whitespace as a regular character (` ` → `▁`). Useful for languages without word delimiters (Chinese, Japanese).

### Why rare words split

Compounds like `kubectl`, `dataclass`, or `bộ_xử_lý_ngôn_ngữ` were not frequent enough during the merge phase to earn their own token, so they decompose at inference time into the most efficient combination of merged subwords.

### Why non-English costs more tokens

Training corpora skew heavily toward English. Vietnamese, Thai, Arabic, Hebrew etc. get less of the early "merge budget" so common words remain split:

| Language        | Approx. tokens per word | Note |
|-----------------|------------------------|------|
| English         | ~1.3                   | baseline |
| Spanish         | ~1.6–1.8               | Latin script + diacritics |
| Vietnamese      | ~1.5–2.0 [PARTIALLY VERIFIED — general "non-Latin / diacritic" pattern confirmed; exact Qwen 3.6 Vietnamese fertility not published in the model card] |
| Chinese         | ~1 token per character (~2x English per *meaning*) |
| Thai / Arabic   | up to 2-3x English |

**Practical heuristic**: `English ≈ 4 characters per token`. For a quick estimate, `tokens ≈ chars / 4`. For Vietnamese text, divide by ~2.5 instead.

### Qwen 3.6-27B tokenizer

- **Vocabulary size**: 248,320 (padded)
- **Type**: Byte-level BPE (Qwen series uses tiktoken-style byte BPE; the 3.6 series inherits this)
- This is a *very* large vocabulary (GPT-2 was 50,257; Llama-3 is 128,256). Large vocab → fewer tokens per text → cheaper inference per "thought" — but a bigger embedding matrix.

The model card says vocabulary = 248,320 padded; actual unique tokens may be slightly fewer (Qwen typically pads vocab to a power-of-two-friendly size for tensor parallelism).

## Concrete numbers for our setup

- Native context window: **262,144 tokens** (~200,000 English words ≈ a 600-page book)
- 27B parameter model has an *embedding table* of `248,320 × 5,120 = 1.27 billion parameters` just for the input/output vocabulary projection. About 4.7% of total parameters live in the tokenizer-facing layers.
- A typical agent turn (system + tools + user + 5 previous turns) for our coding agent should comfortably fit in 16–32K tokens. We won't bump into 262K limits for normal use.

## Likely questions from the professor

**Q: Why don't we just feed the model characters directly?**
A: Two reasons. (1) Sequences would be ~4x longer, and attention is O(n²), so a 4× sequence is 16× the compute. (2) Subwords align better with morphemes (meaningful units), so the model converges faster and generalizes better.

**Q: What happens if my input contains a character that's never been seen?**
A: With byte-level BPE, no character is "unseen" — every Unicode character decomposes to UTF-8 bytes, all 256 of which are base tokens. So you always get *some* tokenization. Worst case it's verbose (each character becomes 2–4 tokens).

**Q: Could we extend the tokenizer to add Vietnamese-specific tokens?**
A: Yes, you can extend the vocabulary, but the new tokens have random embeddings until you fine-tune the model on Vietnamese text. So in practice you accept the inefficiency or fine-tune.

**Q: Does the model see the token IDs directly, or the strings?**
A: Token IDs (integers). The first thing the model does is look up each ID in an embedding table to get a 5,120-dimensional vector. After that, no strings ever exist inside the model.

**Q: Why does "Hello world" cost 2 tokens but "Hellow0rld" cost 5?**
A: `Hello` and ` world` are frequent enough in training to each be one token. `Hellow0rld` is junk to the tokenizer; it splits into `Hello`, `w`, `0`, `r`, `ld` (illustrative — actual split depends on the merges).

## Common misconceptions / gotchas

- **"One word = one token."** No. Average English is ~1.3 tokens/word; rare words and code identifiers can be 2-5 tokens.
- **"The tokenizer is part of the neural network."** No. It's a deterministic preprocessing step, learned once before training, then frozen. You can swap tokenizers only by retraining.
- **"Whitespace is a separator, not a token."** Wrong for byte-level BPE — leading whitespace is *part of* the token (the BPE token for ` world` is different from `world`). This matters when constructing chat templates.
- **Previously confused with embedding**: A token is an integer ID. An embedding is the 5,120-dim vector you look up for that ID. They are distinct steps in the pipeline. See [03-embeddings-and-vector-space.md](03-embeddings-and-vector-space.md).

## Sources

- Qwen 3.6-27B model card (vocabulary size, tokenizer): https://huggingface.co/Qwen/Qwen3.6-27B (accessed 2026-05-17)
- Sennrich et al., "Neural Machine Translation of Rare Words with Subword Units" — original BPE for NMT: https://arxiv.org/abs/1508.07909
- Hugging Face, "Tokenization is Killing our Multilingual LLM Dream" (general multilingual tokenization inefficiency): https://huggingface.co/blog/omarkamali/tokenization (accessed 2026-05-17)
- Petrov et al., "Language Model Tokenizers Introduce Unfairness Between Languages": https://arxiv.org/pdf/2305.15425 (accessed 2026-05-17)
- OpenAI tiktoken README (4 chars/token heuristic): https://github.com/openai/tiktoken
