# vLLM Tool Calling (Cached Summary)

Source: https://docs.vllm.ai/en/stable/features/tool_calling/
Source: https://recipes.vllm.ai/Qwen/Qwen3.6-27B
Source: https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3.5.html (Qwen3.5/3.6 Usage Guide)
Source: https://qwen.readthedocs.io/en/latest/framework/function_call.html
Accessed: 2026-05-18

## Required flags

- `--enable-auto-tool-choice` — mandatory; lets the model decide when to emit a tool call.
- `--tool-call-parser <name>` — selects the parser that converts the model's native tool-call format back into OpenAI-compatible `tool_calls`.
- `--chat-template <path>` — optional; needed only when the tokenizer-bundled template does not already support tool-role messages.
- `--reasoning-parser <name>` — separates "thinking" tokens from the final answer for reasoning models (e.g. `qwen3`, `deepseek_r1`).

Server then exposes the standard OpenAI Chat Completions endpoint at `/v1/chat/completions` and accepts `tools=[...]` plus `tool_choice` (`auto` / `none` / `required` / `{type:"function", function:{name:...}}`).

## Parser → model mapping (selected, full table in source)

| Parser | Target models |
| --- | --- |
| `hermes` | Nous Hermes 2 Pro/Theta/3; Qwen2.5; Qwen3-Next; QwQ-32B |
| `qwen3_coder` | Qwen3-Coder (480B / 30B), Qwen3.5, **Qwen3.6** — XML tag format `<function=name><parameter=key>value</parameter></function>` |
| `qwen3_xml` | Listed in newer docs as alias/successor for the Qwen3 XML format; some sources still use `qwen3_coder` for Qwen3.6 |
| `llama3_json` | Llama 3.1 / 3.2 / 4 (JSON-tagged calls) |
| `llama4_pythonic` / `pythonic` | Llama 4, ToolACE, Ultravox (Python literal calls) |
| `mistral` | Mistral 7B Instruct v0.3+ |
| `deepseek_v3` / `deepseek_v31` | DeepSeek V3 / V3.1 / R1 |
| `granite`, `granite4`, `granite-20b-fc` | IBM Granite series |
| `glm45`, `glm47` | GLM-4.5 family / 4.7 family |
| `openai` | gpt-oss-20b / 120b |
| `kimi_k2`, `hunyuan_a13b`, `cohere_command3`, `longcat`, `gigachat3`, `xlam`, `minimax`, `internlm`, `jamba`, `functiongemma`, `olmo3` | model-specific |

## Qwen3.6-27B specifically

The official Qwen3.5/3.6 Usage Guide (vLLM Recipes) gives:

```
vllm serve Qwen/Qwen3.6-27B \
  --tensor-parallel-size 2 \
  --max-model-len 262144 \
  --reasoning-parser qwen3 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder
```

- Qwen3.6 was trained on the same XML tool grammar as Qwen3-Coder, so `qwen3_coder` is the correct parser. The Hermes parser still works for Qwen2.5/QwQ but does **not** match Qwen3.6's emitted tokens reliably.
- Known issue: streaming with `qwen3_coder` has bugs (split tags across SSE deltas, lost trailing newlines, fragmented content tracking) — see vllm-project/vllm Issue #31871 and related. Non-streaming `tool_calls` parse correctly.
- The model emits XML on the wire; vLLM converts to OpenAI-style `tool_calls` with `function.name` and `function.arguments` (JSON string) before returning over HTTP.

## Tool result message format

Standard OpenAI shape (what vLLM accepts):

```json
{"role": "tool", "tool_call_id": "call_abc123", "content": "{...json result...}"}
```

For Qwen3 reasoning models, **ReAct-style stop-token prompts are explicitly discouraged** in the Qwen docs — the thinking section may emit tokens that look like stop words and corrupt the parse. Use the OpenAI-compatible flow (tools=[...], `tool_choice="auto"`) instead.

## Structured outputs (guided JSON)

Separate from tool calling but composable with it. As of vLLM v0.12.0 the legacy `guided_*` params were renamed:

| Old | New (`extra_body`) |
| --- | --- |
| `guided_json` | `{"structured_outputs": {"json": <schema>}}` |
| `guided_regex` | `{"structured_outputs": {"regex": <pattern>}}` |
| `guided_choice` | `{"structured_outputs": {"choice": [...]}}` |
| `guided_grammar` | `{"structured_outputs": {"grammar": <ebnf>}}` |

Backends: `xgrammar` (default `auto`-selected, fastest), `outlines`, `lm-format-enforcer`, `guidance`. When `tool_choice` is `required` or a named function, vLLM internally invokes structured outputs to schema-validate the arguments. With `tool_choice="auto"` there is **no** schema enforcement on `function.arguments` — malformed JSON can occur.

XGrammar-2 (released 2026-05-04, MLC blog) introduces a "Structural Tag" DSL that unifies tool calling, reasoning channels, and JSON Schema constraints, and reports ~80× compile-time speedup over XGrammar-1 across 10→500 tools, with strict-mode tool calling explicitly supported for DeepSeek V4 / Qwen 3.6 / GPT-OSS / Molmo-2.
