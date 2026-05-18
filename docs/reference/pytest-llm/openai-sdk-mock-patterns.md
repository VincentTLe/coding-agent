# OpenAI SDK v2 mock patterns

Sources: https://shubham-singh98.medium.com/unit-testing-openai-chatcompletion-api-calls-with-pytest-121813c14b0a ; http://blog.pamelafox.org/2023/09/mocking-async-openai-package-calls-with.html (pattern still valid, adapt patch paths for v2)

## Patch points

- Class method (works for all client instances): `openai.resources.chat.completions.Completions.create`
- Async equivalent: `openai.resources.chat.completions.AsyncCompletions.create`
- Instance: `patch.object(client.chat.completions, "create")`

## Build typed responses (preferred over dict)

```python
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from openai.types.completion_usage import CompletionUsage

def make_completion(content: str) -> ChatCompletion:
    return ChatCompletion(
        id="chatcmpl-test", object="chat.completion", created=0, model="gpt-4o",
        choices=[Choice(
            index=0, finish_reason="stop",
            message=ChatCompletionMessage(role="assistant", content=content),
        )],
        usage=CompletionUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
    )
```

## Async streaming iterator

```python
class FakeStream:
    def __init__(self, chunks): self._chunks = list(chunks); self._i = 0
    def __aiter__(self): return self
    async def __anext__(self):
        if self._i >= len(self._chunks): raise StopAsyncIteration
        c = self._chunks[self._i]; self._i += 1; return c
```

Patch with `monkeypatch.setattr("openai.resources.chat.completions.AsyncCompletions.create", fake_create)` where `fake_create` returns `FakeStream([...])` when `stream=True`.

## Tool-call response shape (for agent loop tests)

```python
ChatCompletionMessage(
    role="assistant", content=None,
    tool_calls=[{
        "id": "call_abc", "type": "function",
        "function": {"name": "shell", "arguments": '{"cmd":"ls"}'},
    }],
)
```
