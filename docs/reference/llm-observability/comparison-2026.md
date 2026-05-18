# LLM observability platform landscape (cached 2026-05-18)

Cross-cutting notes pulled from multiple sources during research.

## Quick facts table

| Platform | License | Self-host | Cloud free tier | OpenAI auto-instr | Tool-call tracing | Cost tracking |
|---|---|---|---|---|---|---|
| Langfuse | MIT | Yes, no caps | 50k obs/mo (Hobby) | Drop-in import + @observe | Native, OTel context nesting | Yes, per-model table |
| Arize Phoenix | Elastic 2.0 | Yes, no caps | Phoenix OSS is free; AX hosted free tier | OpenInference (OTel) | Native via OpenInference span kinds | Yes |
| LangSmith | Proprietary SaaS | No (cloud-only for most users; self-host is Enterprise add-on) | 5k traces/mo, 14-day retention | Yes, deep LangChain integration | Yes (LangGraph-native) | Yes |
| OpenLLMetry (Traceloop) | Apache-2.0 | Library, BYO backend | n/a (SDK); Traceloop cloud has free tier | Yes (OTel monkey-patch) | Yes via @tool/@agent decorators | Tag-based only |
| Helicone | Apache-2.0 (gateway is open) | Yes (gateway + observability) | 10k req/mo Hobby | Proxy-based; one-line base_url | Limited (proxy-level) | Best-in-class via cache + price DB |
| Lunary | Apache-2.0 core; some configs Enterprise | Yes (core) | 10k events/mo, 3 projects, 30-day retention | Wrapper / decorator | Yes | Yes |
| Braintrust | Proprietary SaaS | No (cloud-only) | 1M spans/mo, 10K eval runs, unlimited users | Yes | Yes | Yes |
| AgentOps | Proprietary (SDK MIT) | Cloud + limited self-host | Free tier; startup plans | Yes via SDK | Specialized for multi-agent workflows | Yes |

## Notable 2026 events
- Langfuse acquired by ClickHouse (Jan 2026).
- Helicone acquired by Mintlify (Mar 2026); third-party sources describe core observability as "maintenance mode" but the open-source repo and AI Gateway remain active.
- Phoenix's OpenInference spec is becoming the de facto OTel-GenAI convention pair, alongside the upstream OTel GenAI WG.

## Why nested-tool-call capture matters here
A coding agent does {plan -> tool call -> observe -> plan -> tool call ...}. Top-level model-call logging captures only the LLM I/O. The owner needs to see the *tool span tree*: which file was read, what the bash exit code was, how the model reasoned about the result. Langfuse `@observe` and Phoenix OpenInference both create that tree automatically through OTel context propagation, as long as tool execution happens inside the traced function. Proxy-only tools (Helicone) miss that nesting because they only see HTTP traffic to the model endpoint.

## Owner-fit ranking for this project
1. **Langfuse self-hosted** — MIT, runs on Docker Compose, drop-in OpenAI replacement, decorator-style spans match Rule C's verbose log philosophy.
2. **Phoenix self-hosted** — single-binary, OpenTelemetry-native, no DB to manage (SQLite default), strongest if also planning RAG evals.
3. **OpenLLMetry -> local Phoenix** — most "neutral" path; instrumentation is a library, backend is replaceable.
