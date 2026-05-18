# E2 — OpenTelemetry GenAI Semantic Conventions (May 2026)

## TL;DR

OTel GenAI semantic conventions are the de facto wire format for LLM tracing in 2026, but the spec itself is still officially "Development" status — none of the `gen_ai.*` attributes have been formally marked Stable on opentelemetry.io. In practice, the client-span attribute set (`gen_ai.operation.name`, `gen_ai.provider.name`, `gen_ai.request.model`, `gen_ai.usage.*`) has been stable enough that Datadog, Grafana, Langfuse, and Arize Phoenix all consume it natively, and the three major Python instrumentation libraries (official `opentelemetry-python-contrib`, OpenLLMetry, OpenInference) all emit it. Building against OTel-GenAI today is a reasonable bet **provided you guard schema risk with `OTEL_SEMCONV_STABILITY_OPT_IN`** and treat agent/framework span shapes as still moving.

## Why this matters for the coding-agent

A coding agent emits many LLM round-trips per task plus nested tool/agent invocations. Picking a non-portable trace schema now means rewriting later. The win of OTel-GenAI: same instrumentation feeds Langfuse for dev, Phoenix for evals, Datadog/Grafana for prod — no schema rewrite. Coupled with E1 (LLM observability), this defines the wire format.

## State of the spec (SOTA, May 2026)

- **Official status**: All `gen_ai.*` attributes are marked **Development** on the spec page [UNVERIFIED whether the formal "Stable" stamp has landed; secondary sources (CallSphere, dev.to) claim client spans "exited experimental" early 2026, but opentelemetry.io still labels them Development].
- **Latest semconv release**: v1.41.1 (2026-05-11); v1.41.0 (2026-04-28) shipped major GenAI updates — streaming attributes, tool definitions, split of `invoke_agent` into client vs internal spans.
- **Standardized span name format**: `{gen_ai.operation.name} {gen_ai.request.model}`.
- **Operation enum**: `chat`, `text_completion`, `generate_content`, `embeddings`, `retrieval`, `execute_tool`, `create_agent`, `invoke_agent`, `invoke_workflow`.
- **Required attrs on every span**: `gen_ai.operation.name`, `gen_ai.provider.name`.
- **Request attrs**: `gen_ai.request.{model,stream,max_tokens,temperature,top_p,top_k,frequency_penalty,presence_penalty,stop_sequences,choice.count,seed}`.
- **Response attrs**: `gen_ai.response.{model,id,finish_reasons,time_to_first_chunk}`.
- **Usage attrs**: `gen_ai.usage.{input_tokens,output_tokens,cache_creation.input_tokens,cache_read.input_tokens,reasoning.output_tokens}`.
- **Content (opt-in)**: `gen_ai.system_instructions`, `gen_ai.input.messages`, `gen_ai.output.messages`, `gen_ai.tool.definitions` — gated by `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true`.
- **Stability shim**: `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` lets you dual-emit during version transitions.

## Most-used Python implementations

1. **OpenLLMetry (Traceloop)** — Apache-2.0, latest 0.60.0 (Apr 2026). Broadest framework auto-instrumentation: OpenAI/Azure, Anthropic, Gemini, Cohere, Mistral, Groq, Bedrock, SageMaker, Vertex, LangChain, LlamaIndex, CrewAI, LangGraph, plus 4+ vector DBs. Its early semconv was upstreamed into OTel.
2. **OpenInference (Arize)** — Apache-2.0. ~31 Python instrumentors; deepest Phoenix integration; ships converter span processors for OpenLLMetry/OpenLIT. Adds OpenInference attrs (`input.value`, `output.value`) on top of `gen_ai.*`.
3. **opentelemetry-python-contrib (official)** — Tracks the spec exactly. As of May 2026: shipped `opentelemetry-instrumentation-openai-v2` and `opentelemetry-instrumentation-openai-agents-v2`. Anthropic instrumentor exists but is described as "boilerplate skeleton" in third-party reviews [UNVERIFIED how complete].

## Comparison table

| Library | License | Spec alignment | Provider coverage | Framework coverage | Best when |
|---|---|---|---|---|---|
| `opentelemetry-python-contrib` | Apache-2.0 | Tracks spec exactly (closest to upstream) | OpenAI strong; Anthropic skeleton; others TBD | OpenAI Agents v2 | Long-term spec purity; only OpenAI today |
| OpenLLMetry (Traceloop) | Apache-2.0 | Emits `gen_ai.*` + Traceloop extensions; semconv upstreamed | OpenAI, Anthropic, Gemini, Cohere, Mistral, Groq, Bedrock, Vertex, SageMaker | LangChain, LlamaIndex, CrewAI, LangGraph, Haystack | Broadest plug-and-play coverage; LangChain-heavy stacks |
| OpenInference (Arize) | Apache-2.0 | Emits `gen_ai.*` + OpenInference attrs | OpenAI, Anthropic, Claude Agent SDK, Bedrock, Groq, Mistral | LangChain, LlamaIndex, DSPy, CrewAI, AutoGen, PydanticAI, smolagents, OpenAI Agents | Phoenix-native dev loop; widest agent-framework set |

### Backend interop

| Backend | OTLP endpoint / mode | Native `gen_ai.*` | OpenLLMetry | OpenInference |
|---|---|---|---|---|
| Langfuse | HTTP `/api/public/otel`, `/api/public/otel/v1/traces` (no gRPC) | Yes | Yes | Yes (maps `input.value`/`output.value`) |
| Arize Phoenix | OTel-native | Yes | Via converter | First-class |
| Datadog | Native GenAI semconv since OTel v1.37 | Yes | Yes (consumes OTel) | Yes (consumes OTel) |
| Grafana / Loki | OTLP | Yes | Yes | Yes |

## Recommendation for `coding-agent`

**Build against OTel-GenAI conventions** — this is the safest bet for May 2026. Concretely:

1. Emit standard `gen_ai.*` attributes from a thin in-process wrapper around our LLM client calls. Set `gen_ai.operation.name`, `gen_ai.provider.name`, `gen_ai.request.model`, full `gen_ai.usage.*`.
2. **Use OpenLLMetry as the auto-instrumentor** in the short term — broadest provider coverage, native LangChain/LlamaIndex hooks if/when we adopt them, and its semconv was upstreamed so divergence risk is low.
3. **Watch `opentelemetry-python-contrib`** monthly — once Anthropic-v2 lands properly, migrate the LLM client wrapper to it for spec purity.
4. Set `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` so we get newest shapes; keep an env-flag escape hatch to roll back.
5. Default backend = Langfuse self-hosted (already in E1 plan). It accepts all three flavors so we're not locked in.

**Stable bet? Mostly yes, with one caveat.** Client-span attributes are essentially frozen in practice and every major vendor consumes them. Agent/framework span shapes are still moving — don't bake `gen_ai.agent.*` deep into our own data model yet; treat those as pass-through to the backend.

## Next steps

- Implement `obs/otel_genai.py` wrapper: span factory that takes operation name + provider + model and emits the required attrs.
- Add a feature flag `CODING_AGENT_OTEL_CAPTURE_CONTENT` mapping to `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT`.
- Wire to Langfuse OTLP HTTP exporter (no gRPC).
- Add a single integration test that emits a synthetic `chat` span and asserts attribute names against a frozen list.

## Open questions

- Has client-span stability been formally ratified, or only socialized in 2026 blog posts? The spec page still says Development; the [UNVERIFIED] claim that "client spans exited experimental in early 2026" comes from secondary sources and a PR/transition-plan update that I did not confirm directly.
- Is the official `opentelemetry-instrumentation-anthropic` past skeleton status as of v1.41.1? Need to check the contrib repo directly before depending on it.
- How does `gen_ai.usage.reasoning.output_tokens` map to Anthropic's extended-thinking tokens specifically? Spec mentions it generically.

## Sources

- [OpenTelemetry — GenAI semantic conventions index](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
- [OpenTelemetry — GenAI client spans](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/)
- [OpenTelemetry — GenAI agent/framework spans](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/)
- [OpenTelemetry — GenAI metrics](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-metrics/)
- [OpenTelemetry — GenAI events](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-events/)
- [semantic-conventions releases (GitHub)](https://github.com/open-telemetry/semantic-conventions/releases) — v1.41.0 (Apr 2026), v1.41.1 (May 2026)
- [opentelemetry-python-contrib instrumentation-genai](https://github.com/open-telemetry/opentelemetry-python-contrib/tree/main/instrumentation-genai/opentelemetry-instrumentation-openai-v2)
- [OpenLLMetry (Traceloop) — GitHub](https://github.com/traceloop/openllmetry)
- [OpenInference (Arize) — GitHub](https://github.com/Arize-ai/openinference)
- [Langfuse OpenTelemetry integration](https://langfuse.com/integrations/native/opentelemetry)
- [CallSphere — OTel GenAI Conventions for AI Agents in 2026](https://callsphere.ai/blog/vw3c-opentelemetry-genai-conventions-ai-agents-2026)
- [FutureAGI — Best OTel Instrumentation Tools for LLMs in 2026](https://futureagi.com/blog/best-otel-instrumentation-tools-llm-2026)
- [Zylos Research — OTel for AI Agents (Feb 2026)](https://zylos.ai/research/2026-02-28-opentelemetry-ai-agent-observability)
