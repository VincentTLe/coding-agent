# Langfuse custom pricing for vLLM (cached)

Source: https://langfuse.com/docs/observability/features/token-and-cost-tracking and https://langfuse.com/faq/all/costs-tokens-langfuse (fetched 2026-05-18)

## Cost source priority
1. Ingested usage/cost (from API response or trace SDK)
2. Inferred via tokenizer + model definition

## Self-hosted model setup
- Project Settings -> Models -> Add model (UI) or POST /api/public/models
- Define `inputPrice`, `outputPrice`, `totalPrice` per usage type (per 1M tokens)
- Match by `modelName` regex against `generation.model`
- For vLLM: ingest the `usage` object returned by the OpenAI-compatible endpoint (`prompt_tokens`, `completion_tokens`) - vLLM emits these natively.

## Custom tokenizer fallback
- OpenAI tokenizer-format config with `tokensPerMessage`, `tokensPerName`
- Manual fallback: ingest token counts directly via SDK `generation()` `usage` argument.

## Self-host stack (v3)
- langfuse-web + langfuse-worker + ClickHouse + Postgres + Redis + MinIO
- MIT licensed core, no event cap
- ClickHouse is the main operational cost driver
