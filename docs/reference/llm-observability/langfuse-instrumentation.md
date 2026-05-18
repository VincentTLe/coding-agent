# Langfuse Python SDK instrumentation (cached 2026-05-18)

Sources:
- https://langfuse.com/docs/observability/sdk/python/instrumentation
- https://langfuse.com/docs/observability/sdk/instrumentation
- https://langfuse.com/self-hosting
- https://github.com/langfuse/langfuse (README)

## License and self-hosting
- License: MIT (core platform).
- Self-host options: Docker Compose, Kubernetes, or VM. Free, no usage cap.
- Cloud free tier: 50k observations/month (Hobby).
- Acquired by ClickHouse in January 2026 per third-party coverage (Laminar 2026 alternatives post); ClickHouse remains the backing store.

## OpenAI SDK auto-instrumentation
Drop-in import:
```python
from langfuse.openai import openai
```
Every `openai.chat.completions.create(...)` is captured automatically: prompt, completion, model, latency, token usage, streaming chunks, function/tool calls.

## @observe() decorator
- Wraps any Python function (sync or async).
- Creates a span; child Langfuse calls (including OpenAI calls) nest automatically via OpenTelemetry context propagation.
- `as_type="generation"` marks LLM-level spans for cost rollups.

## Nested tool call tracing
- Tool spans nest under the parent span without manual plumbing if the tool runs inside the decorated function.
- For workflows that span processes, pass `langfuse_parent_trace_id` / `langfuse_parent_observation_id` keyword args.
- Tool inputs/outputs are captured on the span.

## Self-hostable cost tracking
- Per-model price table editable in the UI (or via API). Custom local models (Qwen 3.6-27B) can be priced at $0 or per-token to track cost vs. SaaS equivalents.

## Minimal coding-agent setup (sketch)
```python
import os
from langfuse.openai import openai  # drop-in
from langfuse import observe

os.environ["LANGFUSE_HOST"] = "http://localhost:3000"
os.environ["LANGFUSE_PUBLIC_KEY"] = "..."
os.environ["LANGFUSE_SECRET_KEY"] = "..."

client = openai.OpenAI(base_url="http://localhost:8765/v1", api_key="dummy")

@observe(name="agent_step")
def step(messages, tools):
    resp = client.chat.completions.create(model="qwen-3.6-27b", messages=messages, tools=tools)
    return resp

@observe(name="tool_call")
def run_tool(name, args):
    ...  # nested automatically under step()
```
