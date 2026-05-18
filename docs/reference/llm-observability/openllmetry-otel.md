# OpenLLMetry / Traceloop (cached 2026-05-18)

Sources:
- https://github.com/traceloop/openllmetry
- https://www.traceloop.com/docs/openllmetry/introduction

## License and shape
- License: Apache-2.0.
- Latest version 0.60.x (Apr 2026 per GitHub releases [UNVERIFIED exact date]).
- It is an **instrumentation library**, not a backend. Auto-instruments 40+ LLM providers and frameworks, emits OTel spans tagged with the OpenTelemetry GenAI semantic conventions (gen_ai.*).
- Ships traces to any OTel-compatible backend: Phoenix, Datadog, Honeycomb, Grafana Tempo, self-hosted Jaeger, or Traceloop's own SaaS.

## OpenAI SDK auto-instrumentation
```python
from traceloop.sdk import Traceloop
Traceloop.init(app_name="coding-agent",
               api_endpoint="http://localhost:6006")  # send to Phoenix locally
```
The library monkey-patches the OpenAI SDK and emits spans with prompts, completions, tool calls, and token counts.

## Tool / agent tracing
- Provides `@workflow`, `@task`, `@agent`, `@tool` decorators for hierarchical span nesting beyond what the raw LLM instrumentation gives.
- Tool calls inside an OpenAI response become child spans on the LLM span; nested function-call invocations nest under whichever decorator is active.

## Why pair with Phoenix or Langfuse
OpenLLMetry alone has no UI. The common pattern in 2026 is: instrument with OpenLLMetry, ingest into Phoenix (or any OTel backend) for visualization. Langfuse also accepts OTel/OpenLLMetry data via its OTLP endpoint.
