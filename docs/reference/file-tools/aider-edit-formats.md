# Aider Edit Formats (cached)

Sources:
- https://aider.chat/docs/more/edit-formats.html (fetched 2026-05-18)
- https://aider.chat/docs/unified-diffs.html (fetched 2026-05-18)

## Formats Aider supports
- **whole** - full file rewrite; simplest, most tokens, easy to verify.
- **diff** - SEARCH/REPLACE blocks (git-conflict-marker style). File path
  outside the fence.
- **diff-fenced** - same but path inside the fence (Gemini-friendly).
- **udiff** - simplified unified diff. Designed to reduce GPT-4 Turbo "laziness."
- **editor-diff / editor-whole** - used in architect mode where one model
  plans and another applies.

## Benchmark numbers (from unified-diffs.html)
- GPT-4 Turbo laziness benchmark:
  - SEARCH/REPLACE baseline: 20% pass; lazy comments on 12/N tasks.
  - Unified diff: 61% pass; lazy comments on 4/N tasks (~3X reduction).
- gpt-4-0613:
  - SEARCH/REPLACE baseline: 26%.
  - Unified diff: 59%.
- "Flexible patching disabled -> 9X increase in editing errors" on Exercism;
  fuzzy/layered match application is required for unified diff to work well.

## Takeaway
Edit format is model-dependent. Aider chooses per-model. SEARCH/REPLACE
is the practical default for Claude-class models; unified diff helps with
older lazy GPT-4-Turbo-era models. Whole-file is a fallback for small files
or weak models.
