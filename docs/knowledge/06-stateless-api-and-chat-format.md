# 06 — Stateless API and Chat Format

## Core idea (1-2 sentences)

The server holds no conversation memory. Every API call sends the *entire* conversation history; the model treats it as a single document to continue.

## Why it matters for our project

This is the **central design fact** for the agent loop. The agent's job is to maintain the conversation history *client-side*, append new turns and tool results, and re-send everything each round. The whole "agent" exists in our orchestrator code, not on the model server.

## The intuition

Calling an LLM API is not a conversation; it's a one-shot text completion that *looks* like a conversation because we structure the input as a transcript. Imagine writing a play. Each "turn" is a line of dialog you append to the script. Then you hand the entire script to an actor and say "improvise the next line." Then you append their line to the script. Repeat. The actor never remembers — only the script does.

## The mechanics

### What you actually send

OpenAI-compatible APIs (which vLLM serves) expect:

```json
POST /v1/chat/completions
{
  "model": "Qwen/Qwen3.6-27B",
  "messages": [
    { "role": "system",    "content": "You are a coding agent..." },
    { "role": "user",      "content": "List files in src/" },
    { "role": "assistant", "content": "I'll call the ls tool.",
                            "tool_calls": [ {...} ] },
    { "role": "tool",      "tool_call_id": "...", "content": "agent.py\nutil.py" },
    { "role": "assistant", "content": "Two files: agent.py, util.py." },
    { "role": "user",      "content": "Now read agent.py." }
  ],
  "max_tokens": 1024,
  "temperature": 0.2
}
```

Every previous turn is *resent* every time. The server has zero memory between requests.

### How the server turns this into a single token stream

vLLM applies the *chat template* from the model's tokenizer config. For Qwen, that template looks roughly like:

```text
<|im_start|>system
You are a coding agent...<|im_end|>
<|im_start|>user
List files in src/<|im_end|>
<|im_start|>assistant
I'll call the ls tool.<|im_end|>
<|im_start|>tool
agent.py
util.py<|im_end|>
<|im_start|>assistant
```

(Exact tokens vary by model — the Qwen 3.6 template is in its tokenizer config on Hugging Face.)

This is one big string. The model continues from the trailing `<|im_start|>assistant\n`. Special tokens like `<|im_start|>` and `<|im_end|>` are *trained-in* — they have their own embedding vectors and the model recognizes them as turn markers.

### Roles

- **system**: instructions, persona, constraints. Set once at the start, kept across turns.
- **user**: messages from the human / orchestrator.
- **assistant**: messages from the model. When *we* are constructing history, we record what the model previously said here.
- **tool**: tool results. Returned in response to an assistant's tool call. (Some APIs use `function` as the role name; OpenAI's newer schema uses `tool`.)

### The chat template handles formatting; you handle content

You almost never write the `<|im_start|>...` tokens yourself. You hand the API a list of `{role, content}` dicts and the server applies the template. This is good — it isolates you from model-specific quirks. But it means switching models can change behavior subtly if the templates disagree about whitespace or BOS tokens.

### Tool calling — the "function calling" mechanism

When the API supports tool calling (OpenAI-compatible and vLLM does), the assistant's response can include a structured `tool_calls` field:

```json
{
  "role": "assistant",
  "content": null,
  "tool_calls": [
    { "id": "call_abc",
      "type": "function",
      "function": {
        "name": "read_file",
        "arguments": "{\"path\": \"src/agent.py\"}"
      }
    }
  ]
}
```

The orchestrator (us) executes that tool, captures the result, and appends it as a `role: "tool"` message keyed by `tool_call_id`. Then re-call the API. The model has now "seen" the result.

This is the entire agentic loop in one paragraph. Building it is most of Phase 1 of our project.

### Why this design is good

- Horizontal scaling: any server can handle any request (no session affinity).
- Stateless servers can be reset, restarted, moved without state migration.
- The client has full transparency into what the model sees.
- Easy to debug: log the messages list to reproduce a call exactly.

### Why this design has costs

- Network bandwidth: every turn resends the whole history.
- Token cost: every turn re-processes the whole history (though vLLM caches KV across requests for the same prefix — *prefix caching*, a real optimization in vLLM that we'll benefit from for free).
- Client complexity: history management is now our job. Trim, summarize, persist.

## Concrete numbers for our setup

- vLLM serves OpenAI-compatible endpoints at `http://localhost:8765/v1/...` (per our `.env.example`).
- We use the **OpenAI Python SDK** as the client. Same interface that talks to OpenAI's servers talks to vLLM unchanged. This is one of the big wins of using vLLM. See [10-vllm-vs-ollama.md](10-vllm-vs-ollama.md).
- The owner's `.env.example` lists `VLLM_MODEL_NAME=Qwen/Qwen3.6-27B-Instruct`. **NOTE**: the actual published Hugging Face repo is `Qwen/Qwen3.6-27B` (no "-Instruct" suffix); the model supports both "thinking" and "non-thinking / instruct" modes in a single weights checkpoint. Verify what `vllm serve` actually loads. [PARTIALLY VERIFIED — official model card found at https://huggingface.co/Qwen/Qwen3.6-27B; the `-Instruct` suffix returned 401 in our fetch, plausibly because that variant doesn't exist or is restricted].
- vLLM **prefix caching** (`--enable-prefix-caching`) means resent history is mostly free in compute terms — the KV cache for the unchanged prefix is reused.

### Example: agent loop in pseudocode (the design)

```python
messages = [{"role": "system", "content": SYSTEM_PROMPT}]
messages.append({"role": "user", "content": task})

while True:
    response = client.chat.completions.create(
        model="Qwen/Qwen3.6-27B",
        messages=messages,
        tools=TOOL_SCHEMAS,
    )
    msg = response.choices[0].message
    messages.append(msg.model_dump())          # record what the model said

    if not msg.tool_calls:
        return msg.content                      # final answer

    for call in msg.tool_calls:
        result = execute_tool(call.function.name, call.function.arguments)
        messages.append({
            "role": "tool",
            "tool_call_id": call.id,
            "content": result,
        })
    # loop continues with appended tool results
```

(Reference for the owner — the actual implementation lives in `src/`. This is the *shape*.)

## Likely questions from the professor

**Q: How does the model know "this is the user's turn"?**
A: Special role-marker tokens are inserted into the input string by the chat template. The model was trained to recognize `<|im_start|>user` etc. as turn boundaries and to attend differently to system vs user vs assistant text.

**Q: If the API is stateless, how does ChatGPT remember our last conversation?**
A: ChatGPT (the product) stores history in a database server-side, *not* in the model. When you open a chat, the product sends the saved history to the model, just like an agent does. The model is still stateless.

**Q: What if my history exceeds the context window?**
A: The request fails with a 400 error. The agent must summarize, trim, or split. There's no "long-term memory" built into the API.

**Q: How does the model handle tool calls — is that part of the architecture?**
A: No. The architecture is just next-token prediction. Tool calling is a *training* result — the model was trained on examples where the assistant produces JSON-shaped output for tool calls. The API/SDK then parses that JSON. Tool calling is convention, not architecture.

**Q: Why doesn't the model just call tools itself?**
A: It generates *requests* to call tools (text describing what to call with what arguments). The orchestrator (our code) actually executes the tool. The model never has direct access to your filesystem or shell — it just *describes intent*, and we choose whether/how to fulfill it. This is what makes "agents" safe by construction.

## Common misconceptions / gotchas

- **"The model remembers the conversation."** It doesn't. Your code does.
- **"I can send `messages` in any order."** No — the model expects strictly alternating user/assistant with system at the start. Tool results follow tool calls. Violating this confuses the model.
- **"Token costs are charged per turn, so short turns are free."** Each turn re-processes the whole history. Token cost is approximately the size of the history * number of turns.
- **"Tool schemas are part of the system prompt."** They're sent separately as a `tools` parameter. The server formats them into the prompt for you. Don't manually duplicate them into the system message.
- **Previously confused with WebSocket / streaming**: Streaming responses (`stream=True`) is about how tokens arrive *during one call*, not about server memory. The API is still stateless either way.

## Sources

- OpenAI API reference (chat completions, tools): https://platform.openai.com/docs/api-reference/chat (accessed 2026-05-17)
- vLLM OpenAI-compatible server docs: https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html
- Hugging Face chat templating docs: https://huggingface.co/docs/transformers/main/chat_templating
- Qwen 3.6-27B model card (chat template, special tokens): https://huggingface.co/Qwen/Qwen3.6-27B (accessed 2026-05-17)
- vLLM prefix caching guide: https://docs.vllm.ai/en/latest/features/automatic_prefix_caching.html
