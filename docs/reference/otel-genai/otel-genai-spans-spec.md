# Cached: OTel GenAI Client Spans Spec (snapshot 2026-05-18)

Source: https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/

## Span Name Format
`{gen_ai.operation.name} {gen_ai.request.model}` (or `{...} {gen_ai.data_source.id}` for retrievals)

## Core Required Attributes (Development stability)
- `gen_ai.operation.name` — enum: `chat`, `text_completion`, `generate_content`, `embeddings`, `retrieval`, `execute_tool`, `create_agent`, `invoke_agent`, `invoke_workflow`
- `gen_ai.provider.name` — enum: `openai`, `anthropic`, `aws.bedrock`, `gcp.vertex_ai`, `azure.ai.openai`, etc.

## Request Attributes
- `gen_ai.request.model` (Conditionally Required)
- `gen_ai.request.stream` (boolean, Conditionally Required)
- `gen_ai.request.max_tokens`, `temperature`, `top_p`, `top_k`, `frequency_penalty`, `presence_penalty`, `stop_sequences`, `choice.count`, `seed`

## Response Attributes
- `gen_ai.response.model`, `gen_ai.response.id`, `gen_ai.response.finish_reasons`, `gen_ai.response.time_to_first_chunk`

## Usage Attributes
- `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`
- `gen_ai.usage.cache_creation.input_tokens`, `gen_ai.usage.cache_read.input_tokens`
- `gen_ai.usage.reasoning.output_tokens`

## Content Capture (Opt-In, sensitive)
- `gen_ai.system_instructions`, `gen_ai.input.messages`, `gen_ai.output.messages`, `gen_ai.tool.definitions`
- Toggle via env: `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true`

## Stability — IMPORTANT
All attributes were "Development" status per the official spec page at fetch time (2026-05-18). Some 2026 secondary sources claim client spans "exited experimental" in early 2026, but the spec page itself still says Development. Use `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` to opt into newer attribute shapes during transition.

## Agent/Framework Spans (separate page, all Development)
- Create Agent, Invoke Agent (Client), Invoke Agent (Internal), Invoke Workflow, Execute Tool
- Same `gen_ai.operation.name` + `gen_ai.provider.name` required base
- Adds: agent identity, conversation id, data source id, output type
