# Claude Code Tools Reference (cached)

Source: https://code.claude.com/docs/en/tools-reference (fetched 2026-05-18)

## Read
- Parameters: `file_path` (absolute, required), `offset` (optional line start),
  `limit` (optional line count).
- Returns content in `cat -n` format (line numbers starting at 1).
- Default limit ~2000 lines; lines >2000 chars truncated.
- Handles images, PDFs (max 20 pages/call), Jupyter notebooks.
- Reads files only, not directories.

## Write
- Creates or overwrites with full content. No append/merge.
- Read-before-overwrite check: cannot overwrite an existing file unless Claude
  read it in this conversation. New files exempt.

## Edit
- Exact string replacement: `old_string` -> `new_string`.
- No regex / fuzzy matching.
- Three preconditions:
  1. Read-before-edit (file read this session, unchanged on disk).
  2. `old_string` appears exactly as written.
  3. `old_string` appears exactly once (or `replace_all: true`).
- Whitespace/indentation is significant.

## Glob
- Standard glob syntax with `**` for recursive.
- Results sorted by mtime, capped at 100 files; truncation flag if hit.
- Does NOT respect `.gitignore` by default (env var to invert).

## Grep
- Built on ripgrep, regex syntax (not POSIX).
- Output modes: `files_with_matches` (default), `content`, `count`.
- Scoping: `glob` (e.g., `**/*.tsx`) or `type` (e.g., `py`, `rust`).
- Optional `multiline: true` for cross-line patterns.
- Respects `.gitignore` (opposite of Glob).
