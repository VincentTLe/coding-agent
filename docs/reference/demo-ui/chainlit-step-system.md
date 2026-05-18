# Chainlit Step / Message System (cache)

Source: https://docs.chainlit.io/concepts/step ; https://deepwiki.com/Chainlit/chainlit/4-step-and-message-system ; https://github.com/Chainlit/chainlit

## Step system

- Steps = "individual units of execution (LLM calls, tool usage, chains, etc.)". Messages = specialized Steps for user-facing communication.
- Steps form a tree via `parent_id`; a `local_steps` context variable maintains a stack of currently-active steps.
- `config.ui.cot` setting (in `.chainlit/config.toml`) controls how the chain of thought renders: `full`, `hidden`, or `tool_call` (tool calls only).

## Minimal example (from docs)

```python
import chainlit as cl

@cl.step(type="tool")
async def tool():
    await cl.sleep(2)
    return "Response from the tool!"

@cl.on_message
async def main(message: cl.Message):
    tool_res = await tool()
    await cl.Message(content="This is the final answer").send()
```

The decorator captures input args, return value, duration, and parent-child relationships automatically. Renders as an expandable "Used tool" card in the chat.

## Built-in chat features (from project README)

- Markdown rendering, code-block rendering with syntax highlighting (uses standard markdown fenced-code blocks).
- Native message streaming (token-by-token).
- Typing indicators, file uploads, audio.
- LangChain / LlamaIndex / Semantic Kernel integration auto-wires steps from agent callbacks.
- Persistent conversation history (data layer plugin).
- "Chain of Thought" visualizer.

## Demo-relevant gotchas

- 2025-05: original founding team (LiteralAI / Chainlit SAS) stepped back. Project is community-maintained under a Maintainer Agreement. Two high-severity CVEs disclosed late 2025 — pin a recent version.
- GH issues #1372, #2365: tool-step ordering vs final answer is configurable but historically buggy. Verify in a real browser before demo (see project pain point).
- No built-in dataframe / chart widgets — pure chat focus.

## LOC for a tool-call demo

~20 LOC for `app.py` (decorator + on_message handler), zero LOC for the UI itself; `chainlit run app.py` serves on :8000.
