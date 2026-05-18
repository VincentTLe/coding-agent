# OpenAI Codex CLI apply_patch / V4A Format (cached)

Sources:
- https://developers.openai.com/api/docs/guides/tools-apply-patch
- https://codex.danielvaughan.com/2026/03/31/codex-cli-apply-patch-v4a-diff-format/
- https://github.com/openai/codex/blob/main/codex-rs/core/prompt_with_apply_patch_instructions.md

## Summary
Codex CLI mutates files exclusively through `apply_patch`, which emits a
"V4A diff" - a purpose-built patch grammar that OpenAI's models are trained
on. It is NOT standard unified diff; it has its own structure.

## Key properties
- Single tool for create / update / delete.
- Relative paths only (absolute paths rejected as a security constraint).
- Layered context matching: exact -> whitespace-fuzzy -> contextual.
- Reference implementations: `apply_diff.py` (Python SDK),
  `applyDiff.ts` (TS SDK), community `codex-apply-patch` package.

## Why it works for GPT models
"Significant training effort" was reportedly invested into making the model
fluent in V4A (per the GPT-4.1 cookbook release). This is the OpenAI analogue
of Anthropic's str_replace_editor: model + format co-design.

## Practical note for a Claude-based agent
You don't get the V4A training bias; Anthropic models lean toward exact
string-replace semantics (`Edit` / `str_replace_editor`). Pick the format
the model already prefers.
