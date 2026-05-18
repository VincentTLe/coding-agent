# ripgrep — cached reference

Source: https://github.com/BurntSushi/ripgrep (README + man), fetched 2026-05-18.
Current release: 15.1.0 (Oct 2025).

## What it is
A line-oriented recursive regex search tool written in Rust, by Andrew Gallant
(BurntSushi). Drop-in faster replacement for `grep -r`. License: MIT / Unlicense.

## Defaults that matter for an agent
- Recursive from cwd.
- Respects `.gitignore`, `.ignore`, `.rgignore`, hidden file rules.
- Skips binary files automatically.
- Outputs `path:line:col:match` (with `-n --column`).
- Use `rg -uuu` to disable ALL filtering (search everything).

## Flags we'll actually use
```
rg PATTERN                # basic regex search, recursive from .
rg -t py PATTERN          # restrict to Python files (file-type aware)
rg -T js PATTERN          # exclude JS files
rg -l PATTERN             # only print matching paths
rg -c PATTERN             # only print count per file
rg --json PATTERN         # one JSON message per event; great for tool parsing
rg -A 3 -B 3 PATTERN      # context lines
rg -n --column PATTERN    # line + col, anchorable for editors
rg -F 'literal'           # disable regex; literal string mode
rg -w PATTERN             # whole-word match
rg --files                # list all files rg would search (useful for glob)
rg --files -g '**/*.py'   # glob filter
```

## Why agents pick rg over grep
- 5-13x faster than GNU grep on typical trees (codeant.ai benchmark, 2026).
- 75K-file Linux kernel: rg 0.082s vs grep 0.671s (cited in DEV.to benchmark).
- `.gitignore` awareness means no `node_modules/` / `.venv/` noise.
- `--json` is a stable schema — easier than parsing `grep` text output.

## How leading agents use it
- **Aider, Cursor, Codex CLI, Continue, OpenCode**: shell out to `rg`.
- **Claude Code**: originally exposed a `Grep` tool backed by rg. As of
  v2.1.117 (April 2026) the native macOS/Linux builds switched to embedded
  **ugrep** + **bfs** (Bash-invoked). The semantics for the agent remain
  the same: "give me a regex, get matches back". [UNVERIFIED — secondary source].

## Recipe — minimum viable agent tool
```json
{
  "name": "grep",
  "description": "Search regex in repo files. Respects .gitignore. Returns at most 200 matches.",
  "input_schema": {
    "type": "object",
    "properties": {
      "pattern":   {"type": "string"},
      "path":      {"type": "string", "default": "."},
      "file_type": {"type": "string", "description": "rg -t value, e.g. 'py'"},
      "case":      {"enum": ["smart","sensitive","insensitive"], "default": "smart"},
      "context":   {"type": "integer", "default": 0}
    },
    "required": ["pattern"]
  }
}
```
Wire to: `rg --json --max-count=200 -n --column [flags] PATTERN PATH`,
parse the line-delimited JSON, return `[{path,line,col,text}]`.
</content>
</invoke>