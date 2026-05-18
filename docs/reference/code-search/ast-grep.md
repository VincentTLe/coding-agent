# ast-grep — cached reference

Source: https://ast-grep.github.io/ + https://github.com/ast-grep/ast-grep +
https://ast-grep.github.io/advanced/tool-comparison.html, fetched 2026-05-18.

## What it is
A Rust CLI for **structural** (AST-based) search and rewrite. Patterns look
like the target language ("write the code you want to match"); ast-grep parses
both pattern and source with **tree-sitter** and matches subtrees.

## Why structural beats regex for code
Regex `def\s+foo\s*\(` matches:
- A function `def foo(...)` ✓
- A string `"def foo("` inside a docstring ✗ (we don't want this)

ast-grep parses to AST, so the docstring case never matches.

## Pattern syntax (quick)
```bash
# Find every call to print() in the repo
sg --pattern 'print($A)' --lang python

# Rewrite x.foo(y) -> foo(x, y)
sg --pattern '$X.foo($Y)' --rewrite 'foo($X, $Y)' --lang python

# YAML rule with constraints
sg scan --rule rule.yml
```

## Strengths
- Multi-threaded, written in Rust → "tens of thousands of files in seconds"
  (project's own claim, broadly corroborated by HN benchmarks).
- Uses tree-sitter grammars → ~20+ supported languages out of the box.
- Pattern is the **source code**, not a separate query DSL — low learning curve.
- CLI + library (Rust, Node, Python bindings).

## Weaknesses
- No semantic / type info, no taint analysis, no data-flow. For "find every
  caller of this method when `self` is `Foo`" you still need an LSP.
- Younger than Semgrep; fewer prebuilt rule packs.

## When the agent should reach for ast-grep
- "Rename every call to `old_api(x, y)` to `new_api(y, x)`": structural rewrite
  is the safe tool. Regex would break on multi-line calls or comments.
- "Find all `try` blocks with no `except`": trivially expressible in AST.

## Recipe — `structural_search` tool
```json
{
  "name": "structural_search",
  "description": "AST-aware code search using ast-grep patterns. Use when regex would be unsafe.",
  "input_schema": {
    "type": "object",
    "properties": {
      "pattern":  {"type": "string", "description": "ast-grep pattern, e.g. 'print($A)'"},
      "language": {"enum": ["python","typescript","javascript","rust","go","java"]},
      "path":     {"type": "string", "default": "."},
      "rewrite":  {"type": "string", "description": "optional rewrite template"}
    },
    "required": ["pattern", "language"]
  }
}
```
CLI: `sg run --pattern $PATTERN --lang $LANG --json $PATH` (or `--rewrite`
if `rewrite` is set; otherwise read-only).
</content>
</invoke>