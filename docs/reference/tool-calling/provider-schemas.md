# Tool/Function Calling Schemas — Provider Conventions (Cached Summary)

Sources:
- OpenAI: https://platform.openai.com/docs/guides/function-calling
- Anthropic: https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/implement-tool-use
- Anthropic structured outputs: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- Gemini: https://ai.google.dev/gemini-api/docs/function-calling
- Gemini JSON Schema announcement: https://blog.google/innovation-and-ai/technology/developers-tools/gemini-api-structured-outputs/
- Comparison: https://ofox.ai/blog/function-calling-tool-use-complete-guide-2026/ ; https://tokenmix.ai/blog/function-calling-guide
Accessed: 2026-05-18

## OpenAI `tool_calls`

Tool definition (request):

```json
{
  "type": "function",
  "function": {
    "name": "read_file",
    "description": "Read a UTF-8 text file.",
    "parameters": { "<JSON Schema>": "..." },
    "strict": true
  }
}
```

Model response carries `choices[0].message.tool_calls = [{id, type:"function", function:{name, arguments:"<JSON string>"}}]`. Tool results are sent back as `{role:"tool", tool_call_id, content}` messages.

JSON Schema dialect: subset of Draft 2020-12 (no `format: uuid`, no `minimum`/`maximum`, etc., when `strict:true`).

## Anthropic `tool_use`

Tool definition (request, top-level `tools`):

```json
{
  "name": "read_file",
  "description": "Read a UTF-8 text file.",
  "input_schema": { "<JSON Schema>": "..." },
  "strict": true,
  "cache_control": {"type":"ephemeral"}
}
```

Flat — no `function` wrapper. Response is a list of content blocks where tool calls appear as `{"type":"tool_use", "id":"toolu_...", "name":..., "input": {...parsed object...}}`. Tool results come back as a user message with `{"type":"tool_result", "tool_use_id":..., "content":...}`.

Note: `input` is already a **parsed JSON object**, not a stringified one as in OpenAI. JSON Schema dialect: closest to full Draft 2020-12.

## Google Gemini `function_calling`

Tool definition (request):

```json
{ "function_declarations": [
  { "name": "read_file",
    "description": "...",
    "parameters": { "<OpenAPI 3.0 subset>": "..." }
}]}
```

Response has `candidates[0].content.parts[*].functionCall = {name, args:{...}}` (parsed object). Tool result returned as a `functionResponse` part.

JSON Schema dialect: restricted OpenAPI 3.0 subset — no `$ref`, no `anyOf`/`oneOf` historically; 2026 update added JSON Schema mode for Gemini 2.5+ models and preserves key ordering.

## Raw JSON-Schema vs XML conventions

Open-weight models emit tool calls in one of three native conventions before vLLM/SGLang/etc. translate them:

1. **JSON-tagged** (Hermes, Llama3 `<|python_tag|>`, DeepSeek): a sentinel token marks the boundary; arguments are JSON.
2. **XML / pseudo-tags** (Qwen3-Coder / Qwen3.6): `<function=name><parameter=key>value</parameter></function>`. Parameters are emitted as nested tags, not JSON literals — easier for models to produce token-by-token but requires a special parser to coerce types.
3. **Pythonic** (Llama 4, ToolACE): `name(arg1=val1, arg2=val2)` evaluated as Python literals.

Inference engines reconcile all three to the OpenAI `tool_calls` shape on the wire, so client code stays portable.

## Schema design tips (synthesis of sources)

- **Always set `additionalProperties: false`** and list `required`. Open schemas hallucinate fields.
- **Descriptions are part of the prompt** — Anthropic's guide explicitly counts the tool description and per-property descriptions as the primary signal for tool selection.
- **Enums beat strings** wherever the value space is bounded (e.g. `mode: ["overwrite","append"]`).
- **Avoid recursive / `$ref` schemas** if you may target Gemini.
- **Keep argument objects small (<10 fields)** — every provider degrades with bloat.
- **Structured outputs / strict mode** is what guarantees parseable JSON; "auto" tool_choice does not.
