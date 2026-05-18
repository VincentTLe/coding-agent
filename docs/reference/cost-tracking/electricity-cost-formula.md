# Electricity-only cost formula (cached)

Source: https://www.spheron.network/blog/ai-inference-power-electricity-cost-2026/ (fetched 2026-05-18)

## Power draw under inference load
- H100 SXM5: 700 W TDP, typical 600-680 W
- A100 SXM4: 400 W TDP, typical 340-380 W

## $/hour per GPU
```
$/hr = TDP_kW * server_overhead * PUE * $/kWh
```
- server_overhead ~ 1.80 (CPU, NIC, fans, NVSwitch)
- PUE ~ 1.4 (typical colo); 1.1-1.2 efficient DC
- Example H100 @ $0.12/kWh: 0.7 * 1.80 * 1.4 * 0.12 = **$0.21/hr**
- Example A100 @ $0.12/kWh: 0.4 * 1.80 * 1.4 * 0.12 = **$0.12/hr**

## $/token
```
$/tok = ($/hr) / (tok_per_sec * 3600)
```
With Prometheus we can derive `tok_per_sec` directly:
```
sum(rate(vllm:generation_tokens[1m]))
```

## Joules per token references
- Llama-3-70B FP8 on 8xH100 vLLM: 0.385-0.39 J/tok (best practice, 2026)
- FP8 vs BF16: 30-40% more tok/s at same power = 23-29% cheaper electricity

## Cloud-equivalent reference rates (for comparison)
- H100 SXM5 spot ~ $1.03/hr (Spheron quote, 2026) [UNVERIFIED for general market]
- OpenAI/Anthropic per-1M token rates: pull from Langfuse model catalog
