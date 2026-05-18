# D5 — Code Search & Navigation Tools for an AI Coding Agent (2026)

Date: 2026-05-18. Project: from-scratch coding agent at `/home/tle/code/coding-agent`.

## TL;DR
Wire up **three layers**, smallest first: (1) **ripgrep** for any-text search,
(2) **ast-grep** for structural search/rewrite, (3) an **LSP** (pyright for Python,
fronted by **Serena MCP**) for semantic `find_symbol` / `find_references`. Don't
build a custom indexer. Skip ctags/GNU global unless you target editors without
LSP. tree-sitter is the foundation under (2) and (3) — useful directly only if
we want our own repo-map a la Aider.

## Why this matters
Every state-of-the-art coding agent (Aider, Cursor, Claude Code, Codex CLI)
spends most of its tool calls on **search** — 10-30 search operations per task,
per [Codant](https://www.codeant.ai/blogs/ripgrep-vs-grep-performance) and
[DEV.to benchmarks](https://dev.to/rahulxsingh/ripgrep-vs-grep-performance-benchmarks-and-why-ai-agents-use-rg-1716).
With a 10-minute task budget, ~500 ripgrep searches fit; only ~2 GNU-grep
searches do [UNVERIFIED — second-hand benchmark, but order-of-magnitude
matches BurntSushi's original blog]. Bad search → agent guesses → agent
hallucinates patches. Good search → agent grounds its edits.

## State of the art in 2026
Three layers have crystallized, and the leaders use all three:

1. **Lexical** (regex on raw text). Fast, no parsing. Tool: ripgrep. Used by
   every agent for the "where does this string appear?" question.
2. **Structural** (tree-sitter AST patterns). Slower but precise; matches code
   shapes, not characters. Tool: ast-grep (Rust), semgrep (OCaml, slower CLI).
3. **Semantic** (LSP: types, definitions, references). Slowest, most accurate,
   needs a language server warm in-process. Tool: pyright / gopls / tsserver,
   often wrapped by [Serena MCP](https://github.com/oraios/serena).

Aider innovated a hybrid: tree-sitter parse + PageRank to *rank symbols by
importance* and inject the top N into the prompt as a [repo map](https://aider.chat/2023/10/22/repomap.html).
Other agents have adopted variants (e.g. RepoMapper, hermes-agent).

[Claude Code in April 2026 (v2.1.117) reportedly](https://www.buildmvpfast.com/blog/ripgrep-10-years-fast-cli-tools-ai-agents-2026)
swapped its embedded ripgrep for **ugrep + bfs** on native builds.
[UNVERIFIED — second-hand source, Anthropic hasn't published a changelog
entry on this.] The agent-facing tool interface didn't change.

## What the leaders actually do
- **Aider**: `rg` for ad-hoc search + tree-sitter `tags.scm` queries to build
  a PageRanked repo map; no LSP.
- **Cursor**: VS Code fork; uses the editor's built-in LSP fleet plus `rg`
  for raw search.
- **Claude Code**: `Grep` (rg → ugrep), `Glob`, `Bash`, plus an LSP/diagnostics
  bridge in newer versions (April 2026+, per
  [LSP feature posts](https://amirteymoori.com/lsp-language-server-protocol-ai-coding-tools/)).
- **Codex CLI, OpenCode, Continue**: rg + bash, no built-in LSP.
- **Serena MCP** (Oraios, MIT): a popular drop-in MCP server that wraps LSPs
  and exposes `find_symbol`, `find_referencing_symbols`, `replace_symbol_body`,
  `rename`, etc. for *any* MCP-speaking agent.

## Comparison table

| Tool          | Layer       | Speed (10k files) | Precision  | Setup cost   | Python support  | Best use in our agent             |
|---------------|-------------|-------------------|------------|--------------|-----------------|-----------------------------------|
| **ripgrep**   | lexical     | very fast (~0.1s) | low (text) | zero (binary)| any text        | `grep` tool — first-line search   |
| ag (silver-searcher) | lexical | fast            | low (text) | zero         | any text        | skip, rg is faster & better-maintained |
| GNU grep      | lexical     | 5-13x slower      | low (text) | zero         | any text        | skip, only as last resort         |
| **ast-grep**  | structural  | fast (Rust)       | medium     | low          | yes             | `structural_search` + rewrites    |
| semgrep       | structural  | medium (slower CLI)| medium-high| medium (rules)| yes            | optional — only for security rule packs |
| tree-sitter (raw) | structural | fast (lib)      | n/a (DIY)  | high (queries)| via grammars  | only if we build a repo map       |
| **pyright (LSP)** | semantic | medium (warm)    | high       | medium       | first-class     | `find_symbol`, `find_references` for Python |
| jedi (LSP)    | semantic    | medium            | medium     | low          | Python only     | fallback if pyright too heavy     |
| **Serena (MCP)** | semantic | medium            | high       | low (off-the-shelf)| via pyright | shortest path to find_symbol/find_references |
| Universal Ctags | semantic-lite | very fast       | low-medium | low          | yes             | skip; obsoleted by LSP for AI use |
| GNU Global    | semantic-lite | very fast       | low-medium | medium       | via pygments    | skip; same reasoning              |

## Recommendation
**Wire three tools, in this order, for v1:**

1. **`grep`** (ripgrep, `--json`): ~1 day. The agent's workhorse — answers
   "is the string anywhere?" and feeds 80% of investigations.
2. **`structural_search`** (ast-grep, `sg run --json`): ~1 day. Use when
   regex is unsafe (e.g. find all callers of `foo(`, find every `try` with
   no `except`).
3. **`find_symbol` + `find_references`** via **Serena MCP** wrapping
   pyright: ~2 days to integrate as an MCP client; saves us writing a
   pyright stdio bridge. If we want zero external deps, fall back to
   spawning `pyright-langserver --stdio` ourselves and calling
   `workspace/symbol` / `textDocument/references` directly.

**Don't build:**
- A custom indexer (SQLite / embeddings DB). Repo maps a la Aider are great
  but optional for v1 — defer until tools are working.
- Ctags / GNU Global integration. LSP gives the same answers with type info.
- A semgrep layer until we know we need a rule pack.

## Next steps — concrete recipes

### 1) `grep` tool (ripgrep)
CLI invocation:
```bash
rg --json --max-count=200 -n --column \
  ${case_flag} ${type_flag} ${context_flag} -- "$PATTERN" "$PATH"
```
Where `case_flag ∈ {"", "-i", "-s"}` based on `smart|insensitive|sensitive`,
`type_flag = "-t py"` when `file_type` is set, `context_flag = "-C 3"` if
context > 0. Parse line-delimited JSON; emit at most 200 matches with
`{path, line, col, text}`.

Tool schema:
```json
{
  "name": "grep",
  "description": "Regex search across the repo. Respects .gitignore. Returns at most 200 matches.",
  "input_schema": {
    "type": "object",
    "properties": {
      "pattern":   {"type": "string"},
      "path":      {"type": "string", "default": "."},
      "file_type": {"type": "string", "description": "rg -t value, e.g. 'py'"},
      "case":      {"enum": ["smart","sensitive","insensitive"], "default": "smart"},
      "context":   {"type": "integer", "default": 0, "minimum": 0, "maximum": 10}
    },
    "required": ["pattern"]
  }
}
```

### 2) `structural_search` (ast-grep)
CLI:
```bash
sg run --pattern "$PATTERN" --lang "$LANG" --json=stream "$PATH"
# or, with rewrite (requires explicit --update-all to write):
sg run --pattern "$P" --rewrite "$R" --lang "$LANG" --json=stream "$PATH"
```
Schema:
```json
{
  "name": "structural_search",
  "description": "AST-aware code search. Use ast-grep meta-vars like $X. Safer than grep for code shapes.",
  "input_schema": {
    "type": "object",
    "properties": {
      "pattern":  {"type": "string"},
      "language": {"enum": ["python","typescript","javascript","rust","go","java"]},
      "path":     {"type": "string", "default": "."}
    },
    "required": ["pattern","language"]
  }
}
```

### 3) `find_symbol` + `find_references` (LSP via Serena MCP, or direct pyright)

Direct-pyright path (no MCP):
```bash
pyright-langserver --stdio
# Then over JSON-RPC:
# 1. initialize { rootUri: file:///path/to/repo, capabilities: {...} }
# 2. workspace/symbol { query: "Foo" }
# 3. textDocument/references { textDocument: {uri}, position: {line,character}, context: {includeDeclaration: false} }
```

Schemas:
```json
{
  "name": "find_symbol",
  "description": "Locate function/class/method definitions by name across the workspace.",
  "input_schema": {
    "type": "object",
    "properties": {
      "query": {"type": "string"},
      "kind":  {"enum": ["any","function","class","method","variable"], "default": "any"}
    },
    "required": ["query"]
  }
}
```
```json
{
  "name": "find_references",
  "description": "Find every reference to the symbol at file:line:character. Use after locating the symbol with find_symbol.",
  "input_schema": {
    "type": "object",
    "properties": {
      "file":      {"type": "string"},
      "line":      {"type": "integer", "minimum": 0},
      "character": {"type": "integer", "minimum": 0},
      "include_declaration": {"type": "boolean", "default": false}
    },
    "required": ["file","line","character"]
  }
}
```

## Open questions
- Should v1 ship the `find_symbol`/`find_references` pair, or defer to v2?
  Trade-off: rg+ast-grep covers ~90% of agent queries; the remaining 10%
  (true reference-finding across modules) is where LSP shines. Recommend v1
  ship rg + ast-grep, v1.1 add LSP via Serena.
- For Python specifically, do we want pyright (TS, fast) or jedi
  (pure-Python, no Node dep)? Default to pyright; jedi as a config fallback.
- Do we ship an Aider-style PageRank repo map? Defer — heavy to maintain;
  measure first whether the agent actually loses without it.
- Claude Code's April 2026 swap of rg → ugrep: copy-cat or stick with rg?
  Stick with rg — better community, stable JSON output, no observable upside
  to ugrep documented yet.

## Sources
- [BurntSushi/ripgrep README](https://github.com/BurntSushi/ripgrep) — official, v15.1.0, Oct 2025.
- [Codant: ripgrep vs grep benchmarks](https://www.codeant.ai/blogs/ripgrep-vs-grep-performance) — third-party.
- [DEV.to: ripgrep vs grep for AI agents](https://dev.to/rahulxsingh/ripgrep-vs-grep-performance-benchmarks-and-why-ai-agents-use-rg-1716).
- [Build MVP Fast: ripgrep at 10 years](https://www.buildmvpfast.com/blog/ripgrep-10-years-fast-cli-tools-ai-agents-2026) — contains [UNVERIFIED] Claude Code v2.1.117 ugrep switch claim.
- [ast-grep docs + tool comparison](https://ast-grep.github.io/advanced/tool-comparison.html) — official.
- [ast-grep/ast-grep](https://github.com/ast-grep/ast-grep) — official repo.
- [Aider repo map blog](https://aider.chat/2023/10/22/repomap.html) — Aider docs, primary source.
- [Aider repository mapping (DeepWiki)](https://deepwiki.com/Aider-AI/aider/4.1-repository-mapping).
- [Oraios/serena](https://github.com/oraios/serena) — MIT, primary source for tool list.
- [Microsoft LSP 3.17 spec](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/) — `workspace/symbol`, `textDocument/references`.
- [amirteymoori: LSP for AI tools](https://amirteymoori.com/lsp-language-server-protocol-ai-coding-tools/) — claims the 50ms vs 45s LSP-vs-grep number [UNVERIFIED].
- [blackwell-systems/agent-lsp](https://github.com/blackwell-systems/agent-lsp) — pattern reference, MIT.
- [Simplico: what tools do AI assistants use](https://simplico.net/2026/03/22/what-tools-do-ai-coding-assistants-actually-use-claude-code-codex-cli-aider/).
- [batsov: supercharging Claude Code](https://batsov.com/articles/2026/02/17/supercharging-claude-code-with-the-right-tools/).
- [Universal Ctags docs](https://docs.ctags.io/en/latest/other-projects.html) and [GNU Global manual](https://www.gnu.org/software/global/manual/global.html) — official, included to confirm why we skip them.
</content>
</invoke>