# vLLM Prometheus Metrics (cached)

Source: https://docs.vllm.ai/en/stable/usage/metrics/ and https://docs.vllm.ai/en/stable/design/metrics/ (fetched 2026-05-18)

## Token counters
- `vllm:prompt_tokens` (Counter) - prefill tokens processed
- `vllm:generation_tokens` (Counter) - decode tokens emitted
- `vllm:prompt_tokens_cached` (Counter) - prefix-cached prompt tokens
- `vllm:iteration_tokens_total` (Histogram) - tokens per engine step

## Latency histograms
- `vllm:time_to_first_token_seconds` (Histogram) - TTFT
- `vllm:inter_token_latency_seconds` (Histogram) - ITL / TPOT
- `vllm:e2e_request_latency_seconds` (Histogram) - end-to-end
- `vllm:request_queue_time_seconds` (Histogram)

## Gauges
- `vllm:num_requests_running`, `vllm:num_requests_waiting`
- `vllm:kv_cache_usage_perc` (1.0 = 100%)

## Counters
- `vllm:request_success`, `vllm:num_preemptions`, `vllm:corrupted_requests`
- `vllm:prefix_cache_queries`, `vllm:prefix_cache_hits` (compute hit-rate in PromQL)

## Optional MFU (with `--enable-mfu-metrics`)
- `vllm:estimated_flops_per_gpu_total`
- `vllm:estimated_read_bytes_per_gpu_total`

## Removed in v1
- `vllm:tokens_total`, `vllm:num_requests_swapped`, `vllm:cpu_cache_usage_perc`, prefix-cache hit-rate gauge.

## Useful PromQL
- Tok/s: `rate(vllm:generation_tokens[1m])`
- TTFT p95: `histogram_quantile(0.95, rate(vllm:time_to_first_token_seconds_bucket[5m]))`
- Prefix hit-rate: `rate(vllm:prefix_cache_hits[5m]) / rate(vllm:prefix_cache_queries[5m])`
