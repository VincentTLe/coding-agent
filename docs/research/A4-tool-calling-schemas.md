# A4 — Tool / Function Calling Schemas

## TL;DR

Use OpenAI's `tools=[{type:"function", function:{name, description, parameters}}]` shape — it is what `vllm serve` speaks. Define `read_file`, `write_file`, `run_bash` as JSON Schema with `additionalProperties:false`. Launch vLLM with `--enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser qwen3`: Qwen3.6 was trained on the Qwen3-Coder XML grammar (`<function=…><parameter=…>value</parameter></function>`); vLLM converts that to OpenAI `tool_calls` on the wire. For hard guarantees use `tool_choice="required"` or `extra_body={"structured_outputs":{"json":…}}` (xgrammar). `auto` does not enforce.

## Why

Every agent step is a tool call. Malformed JSON breaks the loop. We need a wire format and parser combo that (a) ships out of the box on vLLM 0.12 and (b) Qwen3.6 was actually trained to produce.

## SOTA, May 2026

- **vLLM 0.12**: ~25 `--tool-call-parser` values; all translate to OpenAI `tool_calls`.
- **XGrammar-2** (MLC, 2026-05-04): Structural Tag DSL, ~80× compile-speedup, lists Qwen 3.6 in strict-mode tool calling.
- **Qwen3.6** emits XML, not Hermes JSON. Streaming via `qwen3_coder` still buggy (vllm-project/vllm #31871); non-streaming is solid.
- **Anthropic** added `strict:true` tool definitions in 2026. **Gemini 2.5+** dropped its OpenAPI-3.0-subset restriction for full JSON Schema.

## Most-used

OpenAI's `{type:"function", function:{…}}` shape is universal: vLLM, SGLang, TRT-LLM, Ollama, LiteLLM all accept it.

## Comparison

| Provider / engine (ver.) | Schema differentiator | vLLM support | Tradeoffs |
| --- | --- | --- | --- |
| OpenAI Chat Completions (2026, `strict`) | Nested `{type:"function", function:{…}}`; args as **stringified JSON**; result `role:"tool"` | Native wire format | Universal; arg-as-string friction |
| Anthropic Messages (2026, `strict`) | Flat `{name, input_schema}`; `tool_use` block with **parsed** `input` | n/a | Full JSON-Schema 2020-12; not our wire |
| Gemini 2.5+ | `function_declarations` + JSON-Schema mode; `functionCall` part | n/a | Strict; recent JSON-Schema parity |
| Raw JSON-Schema 2020-12 | Just the params object | Internal to xgrammar | Ubiquitous; no transport |
| XML / pseudo-tags (Qwen3.6) | `<function=…><parameter=…>` emitted by model | `qwen3_coder` parser | Token-friendly; streaming buggy |
| vLLM `--tool-call-parser qwen3_coder` | Engine flag for Qwen3.5/3.6 | The flag itself | Correct for our model; not `hermes` |
| XGrammar-2 (2026-05) | Structural Tag DSL | Default `auto` backend | Near-zero overhead; engaged on `required` |

## Recommendation — schemas for our tools

Server:

```bash
vllm serve Qwen/Qwen3.6-27B \
  --tensor-parallel-size 2 --max-model-len 131072 \
  --reasoning-parser qwen3 \
  --enable-auto-tool-choice --tool-call-parser qwen3_coder
```

Tools (sent on every request, `tool_choice="auto"`):

```json
[
 {"type":"function","function":{
   "name":"read_file",
   "description":"Read a UTF-8 text file from the workspace. Returns contents or an error if missing. Use before editing.",
   "parameters":{"type":"object","additionalProperties":false,"required":["path"],
     "properties":{"path":{"type":"string","description":"Workspace-relative path; no '..'","minLength":1,"maxLength":1024}}}}},
 {"type":"function","function":{
   "name":"write_file",
   "description":"Write or overwrite a UTF-8 text file. Creates parent dirs. No partial edits in v1.",
   "parameters":{"type":"object","additionalProperties":false,"required":["path","content"],
     "properties":{
       "path":{"type":"string","minLength":1,"maxLength":1024},
       "content":{"type":"string","maxLength":1048576},
       "mode":{"type":"string","enum":["overwrite","create_only"],"default":"overwrite"}}}}},
 {"type":"function","function":{
   "name":"run_bash",
   "description":"Run a bash command in the workspace. Captures stdout/stderr/exit. Use for builds, tests, git, ripgrep. NOT for long-running servers.",
   "parameters":{"type":"object","additionalProperties":false,"required":["command"],
     "properties":{
       "command":{"type":"string","minLength":1,"maxLength":8192,"description":"Invoked via /bin/bash -lc."},
       "timeout_s":{"type":"integer","minimum":1,"maximum":120,"default":30}}}}}
]
```

Rules baked in: `additionalProperties:false` + explicit `required`; enums over free text; hard caps to bound damage; descriptions written as terse usage docs (they ARE part of the prompt). Tool results return as `{"role":"tool", "tool_call_id":…, "content":"<truncated string>"}`; truncate `read_file` >50 kB and bash stdout >8 kB.

## Next steps

1. Wrap `openai.OpenAI` with these three tools + `tool_choice="auto"` (A6).
2. Client-side `jsonschema` validate every tool call (defense in depth).
3. Pin a vLLM version where `qwen3_coder` streaming is fixed, else run non-streaming for demo.
4. Reserve `structured_outputs` for non-tool JSON (e.g. self-reflection).

## Open questions

- `qwen3_xml` vs `qwen3_coder` on the pinned vLLM — sources conflict; smoke-test.
- First-token latency penalty when `tool_choice="required"` on 2× A6000 [UNVERIFIED for this hardware].
- Combined streaming + reasoning + tool calls — confirm by running.

## Sources

- vLLM Tool Calling: https://docs.vllm.ai/en/stable/features/tool_calling/
- vLLM Qwen3.5/3.6 Usage Guide: https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3.5.html
- vLLM Structured Outputs: https://docs.vllm.ai/en/latest/features/structured_outputs/
- vLLM Issue #31871 (qwen3_coder streaming): https://github.com/vllm-project/vllm/issues/31871
- Qwen Function Calling: https://qwen.readthedocs.io/en/latest/framework/function_call.html
- Anthropic tool use: https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/implement-tool-use
- Anthropic Structured outputs (2026): https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- Gemini function calling: https://ai.google.dev/gemini-api/docs/function-calling
- Gemini JSON-Schema mode (2026): https://blog.google/innovation-and-ai/technology/developers-tools/gemini-api-structured-outputs/
- MLC XGrammar-2 (2026-05-04): https://blog.mlc.ai/2026/05/04/xgrammar-2-fast-customizable-structured-generation
