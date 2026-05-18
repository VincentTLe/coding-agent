# Syrupy (cached reference)

Source: https://github.com/syrupy-project/syrupy and https://syrupy-project.github.io/syrupy/

- License: MIT.
- Version observed: v5.2.0 (released May 16, 2026). [UNVERIFIED — based on WebFetch summary; confirm against PyPI before pinning.]
- Requirements: Python >= 3.10, pytest >= 8.
- Zero-dependency pytest snapshot plugin.
- Loads snapshots back into the interpreter and compares live Python objects, so it supports custom serializers and binary formats.
- Built-in `path_type` matcher replaces non-deterministic fields (UUIDs, timestamps, IDs) with type placeholders before comparison — the canonical hook for hiding LLM-side jitter in stable-shaped responses.
- `--snapshot-update` regenerates snapshots; CI failure on diff is the regression gate.

LLM-specific usage notes:
- Snapshot the *parsed* structured output (e.g. JSON action plan, tool-call args), not raw assistant text.
- Combine with `temperature=0` + a fixed `seed`; use `path_type` to mask any timestamps or run_ids still present.
- For free-text fields, snapshot a normalized form (lowercased, whitespace-collapsed) or skip them with a matcher and assert separately via an LLM-judge.
