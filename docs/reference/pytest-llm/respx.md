# respx

Source: https://lundberg.github.io/respx/ ; https://tonyaldon.com/2026-02-12-mocking-the-openai-api-with-respx-in-python/

- httpx mock router. Because `openai` Python SDK v1+ runs on httpx, respx intercepts calls cleanly.
- Decorator: `@pytest.mark.respx(base_url="https://api.openai.com/v1/")` or fixture `respx_mock`.
- Supports sync and async; supports streaming responses (`httpx.Response` with `stream=` content).

Example (paraphrased):

```python
import httpx, pytest
from openai import OpenAI

@pytest.mark.respx(base_url="https://api.openai.com/v1/")
def test_chat(respx_mock):
    respx_mock.post("/chat/completions").mock(
        return_value=httpx.Response(200, json={
            "id": "x", "object": "chat.completion", "created": 0,
            "model": "gpt-4o", "choices": [{
                "index": 0, "finish_reason": "stop",
                "message": {"role": "assistant", "content": "hello"},
            }], "usage": {"prompt_tokens":1,"completion_tokens":1,"total_tokens":2},
        })
    )
    client = OpenAI(api_key="sk-fake", base_url="https://api.openai.com/v1/")
    r = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":"hi"}])
    assert r.choices[0].message.content == "hello"
```

Useful for: exercising the SDK's own (de)serialization path; testing retries via `side_effect=[...]`.
