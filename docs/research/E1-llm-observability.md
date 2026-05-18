# E1 — LLM observability platforms in 2026

*Researched 2026-05-18 for the coding-agent project.*

## TL;DR

For a student-budget, self-hosted, verbose coding agent on vLLM + OpenAI SDK, the best fit is **Langfuse, self-hosted via Docker Compose**: MIT-licensed, drop-in OpenAI SDK replacement, `@observe()` decorator that nests tool calls automatically via OpenTelemetry context, per-model cost tracking. **Arize Phoenix** is the strong runner-up (Elastic License 2.0, single Python service, OpenInference + OTel-native). **OpenLLMetry** is the vendor-neutral path — instrument once, ship traces to any OTel backend.

## Why

AGENTS.md Rule C requires the agent runtime to be verbose: every tool call, tool result, and reasoning step must be observable. A coding agent runs `plan -> tool -> observe -> plan -> ...`, so capturing only top-level chat completions loses the tool span tree. Must-haves: self-host or generous free tier, OpenAI Python SDK compatibility (vLLM endpoint), structured function/tool-call spans, cost tracking even for local models.

## SOTA (May 2026)

Two architectures dominate. (1) Backend-first platforms with their own SDKs and UIs: Langfuse, LangSmith, Braintrust, Lunary, AgentOps — most now also accept OTLP. (2) OpenTelemetry-native stacks: Arize Phoenix + OpenInference, and OpenLLMetry. The OTel GenAI conventions (`gen_ai.*`) and OpenInference are converging.

2026 events: Langfuse acquired by ClickHouse (Jan 2026) per third-party coverage [UNVERIFIED long-term license impact]; Helicone acquired by Mintlify (Mar 2026), observability now in maintenance mode; OpenLLMetry shipped its Hub gateway and an MCP server.

## Most-used in 2026

Across Latitude, Laminar, Braintrust, Softcery, and TokenMix round-ups, the most-repeated "recommended" names are **Langfuse, Phoenix, LangSmith, Braintrust**, with **OpenLLMetry** as the most-cited OTel instrumentation library.

## Comparison

| Platform | License | Self-host | Free tier | OpenAI auto-instr | Nested tool calls | Cost tracking |
|---|---|---|---|---|---|---|
| Langfuse | MIT | Yes, no caps | 50k obs/mo cloud | Drop-in `from langfuse.openai import openai` + `@observe` | Yes, OTel context | Yes, per-model table |
| Arize Phoenix | Elastic 2.0 | Yes, free internal | $0 OSS; AX hosted free tier | `OpenAIInstrumentor()` (OpenInference) | Yes, span kinds nest | Yes |
| LangSmith | Proprietary | Self-host = Enterprise | 5k traces/mo, 14d | Yes | Yes (LangGraph-native) | Yes |
| OpenLLMetry | Apache-2.0 | BYO backend | n/a (lib) | Yes, OTel monkey-patch | Yes via `@workflow/@tool` | Tag-based |
| Helicone | Apache-2.0 | Yes | 10k req/mo; Pro $79 | Proxy `base_url` swap | Limited (HTTP-level) | Best-in-class |
| Lunary | Apache-2.0 core | Yes | 10k events/mo, 30d | Wrapper/decorator | Yes | Yes |
| Braintrust | Proprietary | No | 1M spans/mo, 10K evals | Yes | Yes | Yes |
| AgentOps | Proprietary (SDK MIT) | Limited self-host | Free + startup plans | Yes | Multi-agent focus | Yes |

## Recommendation

**Self-hosted Langfuse.** MIT + no usage caps fits the student budget; the drop-in OpenAI wrapper requires only an import change at the vLLM client; `@observe()` produces the hierarchical trace tree Rule C demands; tool spans nest under the agent step automatically via OTel context, so no manual span plumbing. The per-model price table records Qwen 3.6-27B at $0 (or synthetic) so total cost is visible. Langfuse also accepts OTLP, so a later switch to OpenLLMetry keeps the same backend.

Phoenix is the swap-in if disk pressure or eval needs grow. LangSmith and Braintrust are excluded as cloud-only; Helicone's proxy model misses nested tool calls; AgentOps is overkill for a single-agent demo.

## Next steps (concrete setup)

1. `uv add langfuse`.
2. Launch Langfuse via the official `docker compose` stack (Postgres + ClickHouse + worker + web); UI at `http://localhost:3000`.
3. Create a project; copy keys into `.env` as `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`.
4. In the agent's OpenAI client construction, swap `from openai import OpenAI` for `from langfuse.openai import openai`; keep `base_url="http://localhost:8765/v1"`.
5. Decorate the top-level agent step `@observe(name="agent_step")` and each tool (`read_file`, `write_file`, `run_bash`) with `@observe(name="tool:...")`.
6. Add Qwen 3.6-27B to the model price list.
7. Run an end-to-end task and click through the trace tree in the browser to verify nested tool spans (per MEMORY.md: don't trust curl, verify the UI).

## Open questions

- Does ClickHouse's acquisition of Langfuse change MIT terms going forward? [UNVERIFIED] Pin a known-good release for the May 29 demo.
- Storage footprint of three Langfuse services vs. disk at 73%. If pressure rises, switch to Phoenix (single Python process, SQLite default).

## Sources

- Langfuse GitHub: https://github.com/langfuse/langfuse
- Langfuse self-hosting: https://langfuse.com/self-hosting
- Langfuse Python instrumentation: https://langfuse.com/docs/observability/sdk/python/instrumentation
- Langfuse OpenAI cookbook: https://langfuse.com/guides/cookbook/integration_openai_sdk
- Arize Phoenix GitHub (Elastic License 2.0): https://github.com/Arize-ai/phoenix
- Phoenix self-hosting: https://arize.com/docs/phoenix/self-hosting
- OpenInference: https://github.com/Arize-ai/openinference
- LangSmith pricing: https://www.langchain.com/pricing
- OpenLLMetry GitHub: https://github.com/traceloop/openllmetry
- OpenLLMetry docs: https://www.traceloop.com/docs/openllmetry/introduction
- Helicone GitHub: https://github.com/Helicone/helicone
- Lunary pricing: https://lunary.ai/pricing
- AgentOps GitHub: https://github.com/AgentOps-AI/agentops
- Braintrust 2026 agent observability guide: https://www.braintrust.dev/articles/agent-observability-complete-guide-2026
- Latitude 2026 comparison: https://latitude.so/blog/best-ai-agent-observability-tools-2026-comparison
- Laminar Langfuse alternatives 2026 (acquisition reference): https://laminar.sh/article/langfuse-alternatives-2026
