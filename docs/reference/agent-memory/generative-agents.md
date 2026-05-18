# Generative Agents — Park et al. (Stanford, 2023)

Source: Park, O'Brien, Cai, Morris, Liang, Bernstein, "Generative Agents: Interactive Simulacra of Human Behavior," arXiv:2304.03442, UIST 2023. https://ar5iv.labs.arxiv.org/html/2304.03442

## Why it's a reference point

This is the paper that put the **memory stream + reflection + planning** triad on the map. Every later agent-memory design (MemGPT, Mem0, LangMem, Letta) cites or echoes it.

## Architecture

1. **Memory stream** — append-only log in natural language of every observation, action, dialog turn.
2. **Retrieval** — for any moment-to-moment decision, score memories by:
   - **Relevance** — embedding similarity to the current situation.
   - **Recency** — exponential decay over time.
   - **Importance** — LLM-rated salience score (1–10), assigned at write time.
   - Final score is a weighted sum; top-k are surfaced.
3. **Reflection** — periodically, the agent prompts itself to draw higher-level inferences from clusters of memories ("Klaus values academic rigor"). Reflections are themselves written back to the stream and retrieved like any other memory.
4. **Planning** — daily plans → hour blocks → fine-grained actions; plans live in the same stream.

## Smallville experiment

25 agents in a Sims-style sandbox; from one seed prompt ("agent wants to throw a Valentine's party"), the population spontaneously spread invitations, formed couples, and showed up at the right time and place.

## Lessons for coding agents

- **Importance score at write time** is the cheapest way to make later retrieval not-garbage. Most "vector store dumps" skip it.
- **Reflections** are the missing layer between raw episodic memory and semantic memory. Useful for a coding agent: "user prefers small PRs", "tests in this repo are flaky on Mondays" — derived, not observed.
- **Recency + importance + relevance** triple beats pure cosine similarity.
