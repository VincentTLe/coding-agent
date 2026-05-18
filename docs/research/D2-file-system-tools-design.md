# D2 - File-System Tool Design for Coding Agents (2026)

## TL;DR

Across Claude Code, Cursor Composer, Aider, OpenHands, and Codex CLI, the
2026 consensus shape of a file-tool surface is: `Read` (line-numbered, with
offset/limit), `Write` (full rewrite, with read-before-overwrite guard),
`Edit` (exact string-replace with read-before-edit + uniqueness), `Glob`
(file-name patterns), and `Grep` (ripgrep-style content search). The single
biggest reliability lever is the `Edit` strategy. **Exact string-replace
(`old_string` -> `new_string`) with strict preconditions is what Claude-class
models edit most reliably with**, while OpenAI/Codex models prefer their
trained V4A `apply_patch` grammar. Whole-file rewrites are token-expensive
and trigger "laziness"; raw line-range edits drift when files change.

## Why this matters for us

`/home/tle/code/coding-agent` is a Claude-driven agent. The file tools are
the hot path: every coding turn reads, searches, writes, or edits. If
`edit_file` fails 10% of the time we eat retry tokens, lose context cache,
and frustrate the user. Picking the right edit primitive (and its
preconditions) is the most leveraged choice in the v0 toolset.

## State of the art - mid-2026

| Agent | Read | Edit primitive | Search | Notes |
|---|---|---|---|---|
| Claude Code | `Read` with `cat -n` line numbers, offset/limit | `Edit` = exact `old_string`/`new_string` + `replace_all`; requires read-before-edit, uniqueness | `Glob` + `Grep` (ripgrep) | The reference design for Claude-class models. |
| Cursor Composer 2.0 | hidden | `apply_patch` (V4A); also a separate "apply model" merges sketches | hidden | Two-model architecture: planner sketches, fast apply model commits. Has documented `apply_patch` failures in the wild. |
| Aider | full-file context, no read tool | Per-model pluggable: `whole`, `diff` (SEARCH/REPLACE), `diff-fenced`, `udiff` | repo-map + grep | Strongest published benchmark data on edit-format effect. |
| OpenHands | `view` command | `str_replace_editor` (based on Anthropic's released spec) + unified-diff fallback | bash + ripgrep | Server-side application of the editor since PR #6671. |
| Codex CLI | hidden | `apply_patch` emitting V4A diff (model trained on this grammar) | bash | Relative paths only, layered match (exact -> fuzzy). |

The most-used family of edit primitives in 2026 is **exact string-replace
with strict preconditions** (Claude Code `Edit`, OpenHands `str_replace_editor`,
Aider `diff`/SEARCH-REPLACE). Codex/Cursor use `apply_patch`/V4A; both work
because they are co-designed with the model.

## Comparison of edit strategies and failure modes

| Strategy | How it works | Wins | Fails when... | Evidence |
|---|---|---|---|---|
| **Exact string-replace** (Claude `Edit`, OpenHands `str_replace_editor`) | Model supplies `old_string` + `new_string`; tool requires unique exact match | Token-cheap; trivial to verify; preserves rest of file byte-for-byte | Whitespace drifts, file changed since read, `old_string` not unique | Anthropic docs require read-before-edit, exact match, uniqueness; OpenHands refuses non-unique matches |
| **Unified diff (udiff / apply_patch / V4A)** | Model emits `@@`/`---`/`+++` patch; tool applies with fuzzy hunks | Compact for multi-region edits; standardized | Models hallucinate context lines; line numbers drift; needs fuzzy matcher (Aider: disabling flexibility -> **9X more edit errors**) | Aider benchmarks: GPT-4 Turbo went from 20% (SEARCH/REPLACE) to 61% (udiff) on laziness bench - format helps lazy models, not necessarily good ones |
| **Whole-file rewrite** | Model returns entire new file | Always applies; no match logic | Expensive in tokens; triggers laziness ("// ... existing code ..."); easy to lose unrelated code | Aider whole-format: 46% (Feb GPT-4) -> 39% (June GPT-4); Morph reports 1000-line file = 10-12s vs 1.3s with fast-apply |
| **Line-range edit** (replace lines X-Y) | Model gives start/end line + new content | Mechanically simple | Brittle to any prior edit; line numbers shown in `Read` drift; off-by-one errors common | Anthropic Issue #36654: line-number prefix in Read causes Claude to short-wrap replacement text |
| **Apply-model two-stage** (Morph Fast Apply, Cursor) | Big model emits "lazy sketch" with `// ... existing code ...`; small fast model merges | 10x faster, fewer retries (84-96% per Morph) | Adds an external model dependency; failure is opaque ("apply model got it wrong") | Morph reports 2-3.5x fewer retries vs search-and-replace [UNVERIFIED - vendor benchmark] |

**Which fails least often on real edits?** For Anthropic-family models, the
public evidence (Claude Code shipping it as default; OpenHands adopting it
directly; Aider auto-selecting SEARCH/REPLACE for Claude) points to
**exact string-replace with read-before-edit + uniqueness**. For
OpenAI-family models, `apply_patch` is co-trained and wins on their bench.
There is no public SWE-bench-Verified ablation comparing these formats
controlled-for-model, so the "least failure" claim rests on vendor/Aider
benchmarks and adoption patterns. [UNVERIFIED at a single SWE-bench head-to-head]

## Recommendation - concrete JSON schemas

Match Claude Code's surface as closely as practical. Five tools, exact
string-replace for `edit_file`, no line-range edits, no apply-model in v0.

```json
{
  "name": "read_file",
  "description": "Read a file with line numbers (cat -n format). Always pass an absolute path. Use offset/limit for large files.",
  "input_schema": {
    "type": "object",
    "properties": {
      "path": {"type": "string", "description": "Absolute path to the file."},
      "offset": {"type": "integer", "minimum": 1, "description": "1-based line number to start at. Default 1."},
      "limit":  {"type": "integer", "minimum": 1, "maximum": 2000, "description": "Max lines to return. Default 2000."}
    },
    "required": ["path"]
  }
}
```

```json
{
  "name": "write_file",
  "description": "Create a new file or fully overwrite an existing one. For existing files, you must have called read_file on it earlier in this session.",
  "input_schema": {
    "type": "object",
    "properties": {
      "path":    {"type": "string", "description": "Absolute path."},
      "content": {"type": "string", "description": "Full file contents. No append/merge."}
    },
    "required": ["path", "content"]
  }
}
```

```json
{
  "name": "edit_file",
  "description": "Exact string replacement in a file. old_string must appear EXACTLY ONCE (including whitespace) unless replace_all is true. You must have read the file in this session and it must be unchanged on disk.",
  "input_schema": {
    "type": "object",
    "properties": {
      "path":        {"type": "string", "description": "Absolute path."},
      "old_string":  {"type": "string", "description": "Exact text to replace, including surrounding context for uniqueness."},
      "new_string":  {"type": "string", "description": "Replacement text."},
      "replace_all": {"type": "boolean", "default": false, "description": "Replace every occurrence instead of requiring uniqueness."}
    },
    "required": ["path", "old_string", "new_string"]
  }
}
```

```json
{
  "name": "list_dir",
  "description": "List entries in a directory. Non-recursive by default. Use grep/glob-style patterns for filtering.",
  "input_schema": {
    "type": "object",
    "properties": {
      "path":       {"type": "string", "description": "Absolute directory path."},
      "pattern":    {"type": "string", "description": "Optional glob (e.g. **/*.py). If provided, behaves like a glob search rooted at path."},
      "max_depth":  {"type": "integer", "minimum": 1, "default": 1},
      "max_results":{"type": "integer", "minimum": 1, "default": 200}
    },
    "required": ["path"]
  }
}
```

```json
{
  "name": "grep",
  "description": "Search file contents with a ripgrep-style regex. Respects .gitignore by default.",
  "input_schema": {
    "type": "object",
    "properties": {
      "pattern":     {"type": "string", "description": "Regex pattern (ripgrep syntax)."},
      "path":        {"type": "string", "description": "File or directory to search. Default: cwd."},
      "glob":        {"type": "string", "description": "Optional path filter, e.g. **/*.ts"},
      "output_mode": {"type": "string", "enum": ["files_with_matches", "content", "count"], "default": "files_with_matches"},
      "case_insensitive": {"type": "boolean", "default": false},
      "multiline":   {"type": "boolean", "default": false},
      "max_results": {"type": "integer", "minimum": 1, "default": 100}
    },
    "required": ["pattern"]
  }
}
```

### Behavioral guardrails to enforce in the tool layer

1. **Absolute paths only.** Reject relative; print `cwd` to the model.
2. **Read-before-edit / read-before-overwrite.** Track a per-session set of
   (path, sha256-after-read). Reject `edit_file`/`write_file` on an existing
   path that is either unread this session or whose on-disk sha differs.
3. **Uniqueness on edit.** Count occurrences of `old_string`; if > 1 and not
   `replace_all`, return a structured error including a snippet of each
   match site - this is what lets the model recover in one turn.
4. **Line numbers in Read output only.** Strip them from anything fed back
   into Edit. Don't accept line numbers in `edit_file` input.
5. **Truncation flags.** Always tell the model when output was capped
   (line limit, 100-file glob cap, etc.); silent truncation is the worst
   failure mode.

## Next steps

- Implement the five tools above with the listed guardrails.
- Add a smoke-test harness that fuzzes `edit_file` on the demo repo: random
  whitespace perturbations, duplicate `old_string`, stale read - all should
  return structured errors, not silent corruption.
- Defer apply-model (Morph) integration to a v1 follow-up if edit failure
  rate exceeds ~5% on real tasks.
- Optionally add a `view_dir` tree command if `list_dir` proves too
  shallow for navigation.

## Open questions

- Should `edit_file` accept multiple (old, new) pairs in one call? Claude
  Code shipped a `MultiEdit` variant at one point; the tradeoff is atomic
  multi-edit vs. clearer per-edit error attribution.
- Do we want a `view`-style command that returns a directory tree with
  sizes (cheaper than many `list_dir` calls)?
- Should `grep` default to `content` mode for tiny result sets and
  `files_with_matches` for large ones (auto-mode)?
- Is there a public SWE-bench-Verified ablation that controls for model and
  varies only edit format? Not located in this pass.

## Sources

- [Claude Code Tools reference](https://code.claude.com/docs/en/tools-reference)
- [Aider edit formats](https://aider.chat/docs/more/edit-formats.html)
- [Aider unified diffs benchmark](https://aider.chat/docs/unified-diffs.html)
- [Aider GPT code editing benchmarks](https://aider.chat/docs/benchmarks.html)
- [Aider code editing leaderboard](https://aider.chat/docs/leaderboards/edit.html)
- [OpenAI apply_patch guide](https://developers.openai.com/api/docs/guides/tools-apply-patch)
- [Codex V4A diff format - Daniel Vaughan](https://codex.danielvaughan.com/2026/03/31/codex-cli-apply-patch-v4a-diff-format/)
- [Codex apply_patch instructions (GitHub)](https://github.com/openai/codex/blob/main/codex-rs/core/prompt_with_apply_patch_instructions.md)
- [OpenHands str_replace_editor refactor PR #6671](https://github.com/All-Hands-AI/OpenHands/pull/6671)
- [OpenHands file_editor README](https://github.com/All-Hands-AI/OpenHands/blob/main/openhands/runtime/plugins/agent_skills/file_editor/README.md)
- [Cursor 2.0 Composer blog](https://cursor.com/blog/2-0)
- [Fabian Hertwig - Code Surgery: how AI assistants make precise edits](https://fabianhertwig.com/blog/coding-assistants-file-edits/)
- [Morph Fast Apply](https://www.morphllm.com/fast-apply-model)
- [SWE-bench Verified leaderboard](https://www.swebench.com/)
- [SWE-Edit paper (arXiv 2604.26102)](https://arxiv.org/html/2604.26102v1) [UNVERIFIED arXiv ID lookup]
