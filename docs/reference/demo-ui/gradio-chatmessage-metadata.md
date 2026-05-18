# Gradio ChatInterface + ChatMessage metadata (cache)

Source: https://www.gradio.app/guides/agents-and-tool-usage ; https://www.gradio.app/docs/gradio/chatinterface

## Display of agent thoughts / tool calls

`gr.ChatMessage(role="assistant", content="...", metadata={...})` renders a collapsible accordion next to the chat message.

`metadata` dict keys:

- `title` (required to render as a thought card) — e.g. "Used tool Weather API"
- `id`, `parent_id` — nest thoughts (one tool call invoking sub-tools)
- `duration` — execution time in seconds
- `status` — `"pending"` shows a spinner, `"done"` collapses the card
- `log` — extra subdued-font line under the title

## Minimal LangChain-style example (from docs)

```python
import gradio as gr
from gradio import ChatMessage

async def interact_with_agent(prompt, messages):
    messages.append(ChatMessage(role="user", content=prompt))
    yield messages
    async for chunk in agent_executor.astream({"input": prompt}):
        if "steps" in chunk:
            for step in chunk["steps"]:
                messages.append(ChatMessage(
                    role="assistant",
                    content=step.action.log,
                    metadata={"title": f"Used tool {step.action.tool}"}
                ))
        yield messages

gr.ChatInterface(fn=interact_with_agent, type="messages").launch()
```

## LOC

- Bare chat: 4 LOC (`gr.ChatInterface(fn=chat).launch()`)
- Agent with tool-call cards: ~25-35 LOC

## Code rendering

Standard markdown fenced code blocks in `content` are rendered with syntax highlighting. No native side-by-side diff widget; have to render diff as ```diff``` fenced block or HTML.

## Replay

`gr.ChatInterface` exposes a queue + (optional) save_history; not a true session-replay system. Asciinema or custom JSONL log is needed for run-replay.

## Browser verification note

Gradio's launch produces a real localhost web app + optional share URL — test in actual browser, not just curl, because client-side React renders the metadata accordion.
