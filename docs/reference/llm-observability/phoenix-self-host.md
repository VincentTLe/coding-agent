# Arize Phoenix self-hosting (cached 2026-05-18)

Sources:
- https://github.com/Arize-ai/phoenix
- https://arize.com/docs/phoenix/self-hosting
- https://github.com/Arize-ai/openinference

## License and self-hosting
- License: Elastic License 2.0 (ELv2). Free self-host on your own infra, free for internal use; restriction is reselling Phoenix as a managed hosted competing service.
- Single Python service that doubles as an OTLP collector + web UI; persists to SQLite or Postgres.
- Install: `pip install arize-phoenix` (latest 15.10.x as of May 2026 per GitHub releases [UNVERIFIED specific patch]).
- Docker image: `arizephoenix/phoenix` on Docker Hub.

## Instrumentation model: OpenInference + OpenTelemetry
- OpenInference is the open semantic-convention spec; instrumentation libraries emit OTel spans tagged with OpenInference attributes (input.value, output.value, tool calls, embeddings, etc.).
- Vendor-agnostic: Phoenix can be the backend, or any OTel-compatible backend (Honeycomb, Datadog, Jaeger).

## OpenAI SDK auto-instrumentation
```python
from openinference.instrumentation.openai import OpenAIInstrumentor
from phoenix.otel import register

tracer_provider = register(project_name="coding-agent", endpoint="http://localhost:6006/v1/traces")
OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)
```
After that, every `openai.chat.completions.create(...)` produces a span with tool calls as structured attributes.

## Nested tool call capture
- OpenInference spec defines `tool.name`, `tool.parameters`, `tool.result` attributes on a `TOOL` span kind.
- Custom tool spans created via `tracer.start_as_current_span("tool", kind=TOOL)` nest under the model call automatically because of OTel context.
- LlamaIndex, LangGraph, OpenAI Agents SDK, Claude Agent SDK, CrewAI, Vercel AI SDK, Mastra all have first-party OpenInference instrumentors.

## Coding-agent fit
- Pure Python, no external services required beyond Phoenix itself.
- Single process, low RAM (~200MB idle).
- LLM-as-judge evaluators built in (relevance, hallucination, Q&A correctness, toxicity).
