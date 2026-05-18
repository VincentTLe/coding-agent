# Aider repo map — cached reference

Source: https://aider.chat/2023/10/22/repomap.html (still authoritative in 2026),
fetched 2026-05-18.

## What it is
A compact map of the whole repo (top classes, functions, signatures) that
Aider injects into the prompt so the LLM has structural context without
reading entire files.

## How it's built
1. Walk all source files. For each, run a **tree-sitter** parse using the
   `py-tree-sitter-languages` wheels (130+ languages via the underlying
   `tree-sitter-language-pack`).
2. For each language, use a modified version of the language's `tags.scm`
   query (from the tree-sitter grammar) to extract:
   - **Definitions**: classes, functions, methods, vars, types.
   - **References**: identifier uses that may resolve to a definition somewhere.
3. Build a directed graph: nodes = files, edges = "file A references symbol
   defined in file B".
4. Run **personalized PageRank** (via NetworkX) with personalization mass
   placed on files the user is currently editing / chatting about.
5. Render the top-ranked definitions until a token budget is hit
   (`--map-tokens`, default 1000).

## Why it works
- Symbols referenced by many other files get higher rank, exactly matching
  the intuition "if everyone calls it, it's probably important context".
- No language-specific code beyond `tags.scm`; new language = drop in a query file.

## Recipe for our agent
We do NOT need to ship a repo map in v1. But the data path is reusable for
`find_symbol`:
```
parse(file) -> tree-sitter AST
query(AST, language.tags.scm) -> [{name, kind, range, file}]
```
This gives us a static `symbol_index` per file without an LSP, suitable
for "list symbols in this file" or "where is `Foo` defined" (first-match heuristic).

## Limits
- Reference edges are textual identifier matches over the AST — false
  positives across unrelated scopes (an LSP doesn't make this mistake).
- PageRank assumes "important" == "referenced", which is wrong for entry
  points (main, CLI handlers) — Aider papers over this with personalization.
</content>
</invoke>