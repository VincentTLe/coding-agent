# E4 - Cost and Token Tracking for Self-Hosted vLLM (2026)

## TL;DR
vLLM ships a rich Prometheus `/metrics` endpoint with per-request token counts, TTFT, ITL, e2e latency, KV-cache and prefix-cache counters. For a coding agent on a self-hosted A6000/H100, the recommended stack is **vLLM `/metrics` -> Prometheus -> upstream production-stack Grafana dashboard**, plus **Langfuse** with a custom model price entry for $/token attribution per trace. Compute the electricity-only $ figure from `rate(vllm:generation_tokens[1m])` and a TDP * PUE * $/kWh formula; compare against published cloud per-token rates.

## Why this matters
Without cost/token tracking we cannot answer "did this agent run cost more than a GPT-4-class API call?" or "is FP8 worth the engineering time?" Self-hosting hides cost behind a flat GPU hour bill, so per-run attribution must be derived from telemetry. We need it for E1 observability work and for the demo cost panel in F4.

## State of the art (2026-05)

### What vLLM exposes
The v1 engine standardised metrics around request lifecycle ([vLLM docs](https://docs.vllm.ai/en/stable/usage/metrics/), [v1 design](https://docs.vllm.ai/en/stable/design/metrics/)):
- **Tokens**: `vllm:prompt_tokens` (Counter), `vllm:generation_tokens` (Counter), `vllm:prompt_tokens_cached` (Counter), `vllm:iteration_tokens_total` (Histogram).
- **Latency histograms**: `vllm:time_to_first_token_seconds`, `vllm:inter_token_latency_seconds`, `vllm:e2e_request_latency_seconds`, `vllm:request_queue_time_seconds`.
- **Load gauges**: `vllm:num_requests_running`, `vllm:num_requests_waiting`, `vllm:kv_cache_usage_perc`.
- **Prefix cache**: `vllm:prefix_cache_queries`, `vllm:prefix_cache_hits` (compute hit-rate in PromQL).
- **Optional MFU (`--enable-mfu-metrics`)**: `vllm:estimated_flops_per_gpu_total`, `vllm:estimated_read_bytes_per_gpu_total`.
- **Removed in v1**: `vllm:tokens_total`, `vllm:num_requests_swapped`, `vllm:cpu_cache_usage_perc`.

The OpenAI-compatible HTTP endpoint also returns `usage.prompt_tokens` / `usage.completion_tokens` per request, so per-trace attribution does not require parsing Prometheus.

### Throughput per GPU (reference)
- Llama-3.1-8B BF16 on 1xH100: ~12,500 tok/s aggregate ([Modal almanac](https://modal.com/llm-almanac/advisor)).
- Llama-3.1-70B FP8 on 1xH100 (batched): ~460 tok/s ([Cerebrium](https://cerebrium.ai/blog/benchmarking-vllm-sglang-tensorrt-for-llama-3-1-api)); 8xH100 stacks reach 0.385-0.39 J/tok energy efficiency ([Spheron 2026](https://www.spheron.network/blog/ai-inference-power-electricity-cost-2026/)).

### Computing $ for a run
Electricity-only formula (Spheron 2026):
```
$/hr_per_gpu = TDP_kW * server_overhead(~1.8) * PUE(~1.4) * $/kWh
$/token       = ($/hr) / (tok_per_sec * 3600)
```
Example H100 at $0.12/kWh: 0.7 * 1.8 * 1.4 * 0.12 = **$0.21/hr**. A6000 (300W): ~$0.09/hr. Tok/s comes straight from `rate(vllm:generation_tokens[1m])`.

Cloud-equivalent: multiply observed `prompt_tokens` / `completion_tokens` by published API rates (e.g. GPT-4o, Claude 3.5 Sonnet) - Langfuse ships these in its model catalog so you can render two-cost-columns side by side.

### Langfuse custom pricing for vLLM
[Langfuse docs](https://langfuse.com/docs/observability/features/token-and-cost-tracking): ingested usage beats inferred. vLLM emits an OpenAI-compatible `usage` block, so the Langfuse Python SDK auto-captures it. Define a custom model in Project Settings -> Models with `inputPrice` / `outputPrice` per 1M tokens; Langfuse multiplies and shows it in the cost dashboard.

### Dashboards
- **Upstream**: `vllm-project/production-stack/helm/dashboards/vllm-dashboard.json` ([repo](https://github.com/vllm-project/production-stack)) - four sections: system overview, QoS, engine load, resources. Mirrored at [Grafana Labs ID 25043](https://grafana.com/grafana/dashboards/25043-vllm-dashboard/).
- **LMCache dashboard**: companion in production-stack, focuses on cache hit, retrieve speed, CPU cache use.
- **Community**: Glukhov 2026 walkthrough wires it up for vLLM/TGI/llama.cpp ([blog](https://www.glukhov.org/observability/monitoring-llm-inference-prometheus-grafana/)).

## Most-used in practice
Prometheus + Grafana (vLLM production-stack dashboard) for engine-level telemetry; Langfuse (or LangSmith) for per-trace token attribution with custom pricing. The OpenTelemetry exporter ([Parseable post](https://www.parseable.com/blog/vllm-inference-metrics-otel)) is gaining mindshare but Prometheus is still the default.

## Comparison

| Tool | Per-request tokens | $ attribution | TTFT/ITL | GPU/KV stats | Self-host friction |
|------|--------------------|--------------|----------|--------------|--------------------|
| vLLM `/metrics` + Grafana | aggregate only | no (PromQL math) | yes | yes | low - built-in |
| Langfuse v3 (self-hosted) | yes (per trace) | yes (custom price) | optional | no | medium - ClickHouse+Postgres+Redis stack |
| LangSmith (SaaS) | yes | yes | yes | no | low for SaaS, no self-host |
| OTel + Parseable/Jaeger | yes (spans) | manual | yes | partial | medium |
| vLLM logs only | yes (parse) | manual | no | no | low |

## Recommendation
For the coding-agent project: enable vLLM `--disable-log-stats=False` (default) and scrape `/metrics` into Prometheus. Import the upstream production-stack Grafana dashboard. Run Langfuse self-hosted (v3 docker-compose) with a custom model entry for the Qwen/whichever local model, priced at the electricity-derived $/1M-token figure plus a second "cloud-equivalent" model entry priced at GPT-4o rates - this gives a built-in cost comparison panel without extra code. Add a Prometheus recording rule `vllm:cost_per_hour_usd = (TDP_kW * 1.8 * 1.4 * <kwh_rate>)` to surface live $ on the Grafana panel.

## Next steps
1. Stand up Prometheus + Grafana, import dashboard JSON 25043 from grafana.com.
2. Deploy Langfuse v3 via official docker-compose; create two model entries (local vLLM, cloud-equivalent).
3. Wire the agent's OpenAI client to point at vLLM and add Langfuse decorators; verify `usage` ingest.
4. Add a recording rule + Grafana stat panel for live $/hr and cumulative $.
5. Optional: enable `--enable-mfu-metrics` for FLOPS efficiency.

## Open questions
- Does the OpenAI-compatible vLLM endpoint report cached prompt tokens separately in `usage` (so Langfuse can discount prefix-cache hits)? Docs do not confirm. [UNVERIFIED]
- Best-practice PUE for a home lab A6000 (not a colo) - the 1.4 default is colo-biased.

## Sources
- [vLLM Production Metrics docs](https://docs.vllm.ai/en/stable/usage/metrics/) (official)
- [vLLM v1 Metrics design](https://docs.vllm.ai/en/stable/design/metrics/) (official)
- [vllm-project/production-stack Grafana dashboards](https://github.com/vllm-project/production-stack) (official)
- [Grafana Labs dashboard 25043 - vLLM Dashboard](https://grafana.com/grafana/dashboards/25043-vllm-dashboard/)
- [Langfuse Token & Cost Tracking](https://langfuse.com/docs/observability/features/token-and-cost-tracking) (official)
- [Langfuse self-host pricing](https://langfuse.com/pricing-self-host) (official)
- [Spheron - AI Inference Power & Electricity Costs 2026](https://www.spheron.network/blog/ai-inference-power-electricity-cost-2026/)
- [Glukhov - Monitor LLM Inference (vLLM/TGI/llama.cpp) 2026](https://www.glukhov.org/observability/monitoring-llm-inference-prometheus-grafana/)
- [Parseable - vLLM OpenTelemetry metrics](https://www.parseable.com/blog/vllm-inference-metrics-otel)
- [Red Hat - 5 steps to triage vLLM performance (2026-03)](https://developers.redhat.com/articles/2026/03/09/5-steps-triage-vllm-performance)
- [Modal LLM Almanac advisor](https://modal.com/llm-almanac/advisor)
