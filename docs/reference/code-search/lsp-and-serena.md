# LSP (pyright/jedi) + Serena MCP — cached reference

Sources:
- LSP 3.17 spec: https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/
- Serena: https://github.com/oraios/serena
- agent-lsp: https://github.com/blackwell-systems/agent-lsp
Fetched 2026-05-18.

## Why LSP for an agent
Regex/AST search answer "where does this string/shape appear?".
LSP answers semantic questions:
- "Where is this symbol **defined**?" → `textDocument/definition`
- "Who **calls** this function?" → `textDocument/references`
- "What are the **symbols** in this workspace matching `Foo`?" → `workspace/symbol`
- "What's the **type** here?" → `textDocument/hover`

Reported impact (agent-lsp / amirteymoori): finding all call sites of a
function takes ~50ms via LSP vs ~45s via repo-wide text search on large
TypeScript monorepos. [UNVERIFIED — single source, but plausible order of magnitude.]

## Python servers (pick one)
| Server   | Backend       | Strength                       | Notes |
|----------|---------------|--------------------------------|-------|
| pyright  | MS, TypeScript| Fast, strict types, monorepo-friendly | Default for Pylance / many AI tools |
| jedi (jedi-language-server) | Pure Python | Lighter; no type-checking      | Good for completion, weaker for refs |
| pylsp    | Plugin host   | Extensible, slower             | Older crowd, less LSP feature coverage |

For an AI coding agent in 2026: **pyright** by default. Faster, stricter,
better at cross-file `references`.

## How agents wire LSP without becoming an editor
You don't reimplement an editor. Two patterns:

### Pattern A: spawn an LSP, drive it over JSON-RPC stdio
```
agent ↔ JSON-RPC stdio ↔ pyright-langserver --stdio
```
Each tool call sends `initialize` (once), then a method like
`workspace/symbol`, gets a response, returns the result to the agent.

### Pattern B: use **Serena MCP** (off-the-shelf)
Serena (Oraios, MIT) is an MCP server that:
- Spawns the right LSP per file extension (.py → pyright, .ts → tsserver, .go → gopls).
- Exposes ready-made tools: `find_symbol`, `find_referencing_symbols`,
  `find_implementations`, `symbol_overview`, `replace_symbol_body`,
  `insert_before_symbol`, `insert_after_symbol`, `rename`, `safe_delete`,
  `diagnostics`, `search_for_pattern`.
- Used by Claude Code, Cursor, Codex, JetBrains via MCP.

For a from-scratch agent this is the fastest way to "not invent a custom indexer".

## Tool schema sketches (Pattern A — direct LSP)
```json
{
  "name": "find_symbol",
  "description": "Find symbols (functions/classes/vars) by name across the workspace.",
  "input_schema": {
    "type": "object",
    "properties": {
      "query": {"type": "string", "description": "Symbol name or substring"},
      "kind":  {"enum": ["any","function","class","method","variable"], "default": "any"}
    },
    "required": ["query"]
  }
}
```
Implementation: send LSP `workspace/symbol { query }` to pyright;
filter results by `SymbolKind` if `kind != any`; return
`[{name, kind, file, range}]`.

```json
{
  "name": "find_references",
  "description": "Find every reference to the symbol at a given location.",
  "input_schema": {
    "type": "object",
    "properties": {
      "file":      {"type": "string"},
      "line":      {"type": "integer"},
      "character": {"type": "integer"},
      "include_declaration": {"type": "boolean", "default": false}
    },
    "required": ["file","line","character"]
  }
}
```
Implementation: `textDocument/references` with `Position { line, character }`.

## What LSP can't do
- Doesn't index unopened files until you open them (or the server's project
  config picks them up). For Python, pyright requires `pyrightconfig.json`
  or `pyproject.toml` to anchor the project root.
- Initialization is slow on first call (seconds to tens of seconds on big repos)
  — agent should `initialize` once and keep the server warm.
- Doesn't help with strings/templates/SQL (LSP only knows the language).
</content>
</invoke>