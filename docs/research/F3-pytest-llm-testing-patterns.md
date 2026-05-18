# F3 - pytest patterns for testing LLM-calling code (2026)

## TL;DR

For a vLLM-backed coding agent, the 2026 sweet spot is: **(a) unit-test the agent loop against a hand-rolled `FakeLLM` injected via a pytest fixture, (b) use `respx` for a handful of SDK-level transport tests, (c) use `syrupy` to snapshot agent trajectories / tool-call payloads, and (d) keep one `pytest-recording` (VCR) cassette as the live-vLLM smoke test.** `MagicMock` of `client.chat.completions.create` is a fine starter pattern but loses type safety and breaks when the SDK changes; prefer a typed `FakeLLM` plus `respx` for transport edge cases. `openai-responses-python` exists but is in maintenance mode and is overkill for an internal agent.

## Why this matters

The agent loop runs an LLM in a hot loop with tool calls. Tests must be (i) fast (no network), (ii) deterministic (no temperature drift), (iii) able to drive multi-turn flows, (iv) able to exercise streaming and tool-call branches, and (v) catch regressions in prompt or schema changes. The same suite must still smoke-test against the real vLLM endpoint occasionally.

## SOTA (May 2026)

- `pytest` 9.x and `pytest-asyncio` are still the core. `pytest-asyncio` is the de-facto async runner; the recommended `asyncio_mode = "auto"` makes async tests transparent. ([dasroot.net 2026 best practices][1])
- The Python community has converged on three transport-level mocking strategies, depending on layer:
  - **`MagicMock` / `monkeypatch.setattr`** at `openai.resources.chat.completions.Completions.create`. Simple, no extra deps, but you must build `ChatCompletion` Pydantic objects (dicts will not deserialize via SDK). ([Singh, Medium][2])
  - **`respx`** intercepts httpx, which is what the OpenAI v2 SDK uses. Exercises full SDK (de)serialization including streaming SSE. ([tonyaldon.com 2026][3])
  - **`vcrpy` + `pytest-recording`** record once, replay forever. Best for "freeze a real vLLM response and CI off it." 0.13.4 (2025) is current. ([pytest-recording PyPI][4])
- **`openai-responses-python`** is a higher-level RESPX-based pytest plugin with decorator `@openai_responses.mock()`. Streaming added in v0.4. Maintainer flagged it "maintenance mode" (May 2025) - use cautiously. ([openai-responses-python README][5])
- **Snapshot testing**: `syrupy` dominates; `pytest-insta` is the niche alternative. Both useful for capturing tool-call traces, but syrupy fails on missing snapshots (a feature) and has a `JSONSnapshotExtension` ideal for agent trajectories. ([syrupy GitHub][6])
- **Agent-shaped guidance**: keep a `FakeLLM` dataclass with a queue of canned responses and a call log; store 5-10 representative response fixtures (normal, tool-call, refusal, malformed, empty) as JSON under `tests/fixtures/`. ([CallSphere][7])

## Most-used in 2026

Going by GitHub usage and 2026 blog coverage, the dominant stack for LLM-agent test suites is:

1. `pytest` + `pytest-asyncio` (auto mode).
2. A project-owned `FakeLLM` fixture in `conftest.py` for unit tests.
3. `respx` for SDK-level transport tests (retries, error codes, streaming bytes).
4. `syrupy` for snapshotting agent transcripts and prompt-rendered messages.
5. `pytest-recording` + 1-3 cassettes for the e2e smoke layer.

`openai-responses-python` shows up in tutorials but is rarely seen in production codebases - one less moving part if you already have respx. [UNVERIFIED ranking - based on blog frequency, not download stats.]

## Comparison table

| Approach | Layer | Pros | Cons | Best fit |
|---|---|---|---|---|
| `MagicMock` on `Completions.create` | Python | No deps; trivial | Drift with SDK; must build typed objects; no streaming realism | One-off unit tests |
| `FakeLLM` dataclass + DI | App | Multi-turn scripting; inspect call log; type-stable | You write it | **Default for agent-loop unit tests** |
| `respx` | httpx | Exercises real SDK; streaming SSE | Slightly more setup; you craft JSON | SDK-level transport tests |
| `vcrpy` + `pytest-recording` | HTTP | Record once / replay forever; realistic bytes | Cassette drift; secrets must be filtered | Smoke / e2e against vLLM |
| `openai-responses-python` | RESPX wrapper | One decorator; covers Assistants/Files | Maintenance mode; OpenAI-shape only | Tests that touch many endpoints |
| `syrupy` snapshots | assertion | Catches prompt/output drift; JSON ext | Snapshots need curation | Transcripts, rendered prompts |
| `pytest-insta` snapshots | assertion | REPL diff review | Smaller community | If you prefer REPL workflow |

## Recommendation

**Primary: `FakeLLM` fixture + `pytest-asyncio` + `syrupy`** for unit tests; **`respx`** for a thin layer of SDK transport tests; **`pytest-recording`** for one e2e smoke test against the local vLLM. Keep the agent's LLM dependency behind a `Protocol` / abstract client - this is the single highest-leverage decision; everything else follows.

Skip `openai-responses-python` unless you find yourself testing Assistants/Threads/Vector Stores - it adds a maintenance-mode dependency for what is otherwise three lines of respx.

## Next steps - concrete pytest fixtures

### Layout

```
tests/
  conftest.py                  # FakeLLM + shared fixtures
  fixtures/
    chat_normal.json
    chat_tool_call.json
    chat_refusal.json
  unit/
    test_agent_loop.py
    test_tool_dispatch.py
    test_prompt_builder.py
  integration/
    test_respx_transport.py   # uses respx
    cassettes/
      test_vllm_smoke.yaml    # VCR cassette
    test_vllm_smoke.py        # uses pytest-recording
```

In `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
markers = [
    "integration: hits real vLLM (deselect with -m 'not integration')",
]
testpaths = ["tests"]
```

### conftest.py - FakeLLM + canned response fixtures

```python
# tests/conftest.py
from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import pytest
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from openai.types.completion_usage import CompletionUsage


class LLMClient(Protocol):
    def complete(self, messages: list[dict], **kw: Any) -> ChatCompletion: ...


@dataclass
class FakeLLM:
    """Deterministic LLM stand-in. Queue canned ChatCompletions; tests inspect call_log."""
    responses: list[ChatCompletion] = field(default_factory=list)
    call_log: list[dict] = field(default_factory=list)
    _i: int = 0

    def complete(self, messages: list[dict], **kw: Any) -> ChatCompletion:
        self.call_log.append({"messages": messages, **kw})
        if self._i >= len(self.responses):
            raise AssertionError("FakeLLM exhausted - agent made more calls than scripted")
        r = self.responses[self._i]; self._i += 1; return r


def _completion(content: str | None = None, tool_calls=None) -> ChatCompletion:
    msg = ChatCompletionMessage(role="assistant", content=content, tool_calls=tool_calls)
    return ChatCompletion(
        id="chatcmpl-test", object="chat.completion", created=0, model="fake",
        choices=[Choice(index=0, finish_reason="stop", message=msg)],
        usage=CompletionUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
    )


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def reply():
    """Helper to build typed canned replies inline."""
    return _completion


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"
```

### Unit test - agent loop without vLLM

```python
# tests/unit/test_agent_loop.py
from agent.loop import run_agent  # whatever the project's entrypoint is

def test_agent_terminates_on_final_answer(fake_llm, reply):
    fake_llm.responses = [reply(content="done")]
    result = run_agent("what is 2+2?", llm=fake_llm)
    assert result.final == "done"
    assert len(fake_llm.call_log) == 1

def test_agent_dispatches_tool_call(fake_llm, reply):
    fake_llm.responses = [
        reply(tool_calls=[{
            "id": "call_1", "type": "function",
            "function": {"name": "shell", "arguments": '{"cmd":"echo hi"}'},
        }]),
        reply(content="ok"),
    ]
    result = run_agent("run echo hi", llm=fake_llm)
    assert result.final == "ok"
    assert fake_llm.call_log[1]["messages"][-1]["role"] == "tool"
```

### Snapshot test for prompt / trajectory

```python
# tests/unit/test_prompt_builder.py
from syrupy.extensions.json import JSONSnapshotExtension
import pytest

@pytest.fixture
def snapshot_json(snapshot):
    return snapshot.with_defaults(extension_class=JSONSnapshotExtension)

def test_system_prompt_rendered(snapshot_json):
    from agent.prompt import build_messages
    assert build_messages(task="hello") == snapshot_json
```

### Async streaming test

```python
# tests/unit/test_streaming.py
import pytest

class _Stream:
    def __init__(self, chunks): self._c = list(chunks)
    def __aiter__(self): return self
    async def __anext__(self):
        if not self._c: raise StopAsyncIteration
        return self._c.pop(0)

async def test_stream_consumed(monkeypatch):
    async def fake_create(*a, **k): return _Stream(["he", "llo"])
    monkeypatch.setattr(
        "openai.resources.chat.completions.AsyncCompletions.create", fake_create,
    )
    from agent.stream import consume
    assert await consume() == "hello"
```

### SDK transport test with respx

```python
# tests/integration/test_respx_transport.py
import httpx, pytest
from openai import OpenAI

@pytest.mark.respx(base_url="http://localhost:8000/v1/")
def test_retry_on_5xx(respx_mock):
    route = respx_mock.post("/chat/completions").mock(side_effect=[
        httpx.Response(503, json={"error": "busy"}),
        httpx.Response(200, json={
            "id":"x","object":"chat.completion","created":0,"model":"q",
            "choices":[{"index":0,"finish_reason":"stop",
                "message":{"role":"assistant","content":"hi"}}],
            "usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2},
        }),
    ])
    client = OpenAI(api_key="x", base_url="http://localhost:8000/v1/")
    r = client.chat.completions.create(model="q", messages=[{"role":"user","content":"y"}])
    assert r.choices[0].message.content == "hi"
    assert route.call_count == 2
```

### e2e smoke against vLLM with pytest-recording

```python
# tests/integration/test_vllm_smoke.py
import pytest
from openai import OpenAI

@pytest.fixture(scope="module")
def vcr_config():
    return {"filter_headers": ["authorization", "api-key"]}

@pytest.mark.integration
@pytest.mark.vcr
def test_vllm_responds():
    client = OpenAI(api_key="EMPTY", base_url="http://localhost:8000/v1/")
    r = client.chat.completions.create(
        model="qwen3.6-27b",
        messages=[{"role":"user","content":"reply with the single word: pong"}],
        temperature=0,
    )
    assert "pong" in r.choices[0].message.content.lower()
```

Record once with `pytest --record-mode=once -m integration`. Commit `cassettes/test_vllm_smoke.yaml`. CI runs replay-only (`--record-mode=none`, the default).

## Open questions

- Does `openai-responses-python` still receive updates in 2026, or has it been archived? [UNVERIFIED]
- Does VCR cassette matching still cope with vLLM's streaming SSE responses cleanly in 0.13.x, or do we need a custom `match_on`? [UNVERIFIED - worth a spike before committing.]
- pytest-asyncio's recommended `asyncio_mode` for nested event-loop streaming tests in 2026 (auto vs strict). [UNVERIFIED - the dasroot.net article cites 0.21.0 which feels low for 2026; double-check actual current version.]

## Sources

1. [Python Agent Testing: Best Practices & Tools (dasroot.net, Feb 2026)](https://dasroot.net/posts/2026/02/python-agent-testing-best-practices-tools/)
2. [Unit Testing OpenAI ChatCompletion API Calls with pytest (Singh, Medium)](https://shubham-singh98.medium.com/unit-testing-openai-chatcompletion-api-calls-with-pytest-121813c14b0a)
3. [Mocking the OpenAI API with respx in Python (tonyaldon.com, Feb 2026)](https://tonyaldon.com/2026-02-12-mocking-the-openai-api-with-respx-in-python/)
4. [pytest-recording on PyPI](https://pypi.org/project/pytest-recording/)
5. [openai-responses-python (GitHub)](https://github.com/mharrisb1/openai-responses-python)
6. [syrupy (GitHub)](https://github.com/syrupy-project/syrupy)
7. [Unit Testing AI Agents: Mocking LLM Calls (CallSphere)](https://callsphere.ai/blog/unit-testing-ai-agents-mocking-llm-calls-deterministic-tests)
8. [vcrpy docs](https://vcrpy.readthedocs.io/en/latest/)
9. [Mocking async openai package calls with pytest (Pamela Fox)](http://blog.pamelafox.org/2023/09/mocking-async-openai-package-calls-with.html)
10. [pytest-insta on PyPI](https://pypi.org/project/pytest-insta/)
