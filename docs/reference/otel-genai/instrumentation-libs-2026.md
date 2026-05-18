# Cached: Python GenAI Instrumentation Libraries (snapshot 2026-05-18)

## opentelemetry-python-contrib (official)
- Org: OpenTelemetry project
- Package path: `instrumentation-genai/opentelemetry-instrumentation-{openai-v2,openai-agents-v2,...}`
- Coverage: OpenAI, OpenAI Agents documented; Anthropic listed as "boilerplate skeleton"
- Spec alignment: tracks gen_ai.* spec exactly; smallest framework surface
- Env: `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT`

## OpenLLMetry (Traceloop)
- Repo: github.com/traceloop/openllmetry
- License: Apache 2.0
- Latest: 0.60.0 (2026-04-19)
- Coverage: OpenAI/Azure, Anthropic, Gemini, Cohere, Mistral, Groq, Bedrock, SageMaker, Vertex AI, LangChain, LlamaIndex, CrewAI, LangGraph, Pinecone, Chroma, Qdrant, Weaviate
- Spec alignment: contributed its semconv to OTel; emits `gen_ai.*` plus some Traceloop-specific extensions
- 257 releases, ~1,388 commits on main

## OpenInference (Arize)
- Repo: github.com/Arize-ai/openinference
- License: Apache 2.0
- Coverage: ~31 Python packages: OpenAI, Anthropic, Claude Agent SDK, Groq, Mistral, Bedrock, LangChain, LlamaIndex, DSPy, CrewAI, Haystack, PydanticAI, AutoGen, BeeAI, smolagents, OpenAI Agents
- Also ships 13 JS, 4 Java packages
- Phoenix-native, OTLP-compatible elsewhere
- Has converter span processors for OpenLLMetry and OpenLIT

## Backend Interop
- Langfuse: OTLP HTTP endpoint `/api/public/otel` (also `/api/public/otel/v1/traces`); recognizes `gen_ai.*` natively; explicitly maps OpenInference `input.value`/`output.value`; supports OpenLLMetry
- Arize Phoenix: OTel-native, primary OpenInference consumer but ingests vanilla OTel GenAI
- Datadog: native GenAI semantic conventions support since OTel v1.37
- Grafana: collects LLM traces in Loki
