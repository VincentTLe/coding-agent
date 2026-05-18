# Morph Fast Apply (cached)

Source: https://www.morphllm.com/fast-apply-model (fetched 2026-05-18)

## Concept
A small purpose-trained "apply" model that merges an LLM's "lazy" edit
snippet (with `// ... existing code ...` markers) into the original file.
This replaces having the main LLM either:
- rewrite the whole file (token-heavy, slow), or
- emit exact SEARCH/REPLACE blocks (failure-prone on context drift).

## Reported numbers
- ~10,500 tokens/sec, 98% claimed merge accuracy.
- 1,000-line file: 1.3s vs 10-12s for whole-file rewrite.
- Token usage: -50-60% vs whole-file rewrite.
- Frontier model success rates 84-96%; 2-3.5x fewer retry turns vs search/replace.

[UNVERIFIED] - vendor-reported benchmarks; no independent SWE-bench
breakdown that isolates Fast Apply contribution.

## Why this matters for us
Optional second-stage architecture: planner model emits sketch + diff hint,
apply model commits. Not required for v0; mention as "Next steps" if exact
string-replace turns out to fail too often.
