# Claude Code Agent Loop — Recovery Behavior (cached)

Source: https://code.claude.com/docs/en/agent-sdk/agent-loop (fetched 2026-05-18)

## Termination subtypes (`ResultMessage.subtype`)
- `success` — normal end (no tool calls in final assistant message).
- `error_max_turns` — hit `maxTurns` / `max_turns`.
- `error_max_budget_usd` — hit `maxBudgetUsd` / `max_budget_usd`.
- `error_during_execution` — API failure or cancellation interrupted the loop.
- `error_max_structured_output_retries` — structured-output validation failed past retry limit.

The `result` field (final text) is **only** present on `success`. All subtypes carry `total_cost_usd`, `usage`, `num_turns`, `session_id` — so cost/resume info survives errors.

## Loop step (verbatim from doc)
1. Receive prompt → `SystemMessage{subtype:"init"}`.
2. Evaluate → `AssistantMessage` (text + tool_use blocks).
3. Execute tools → `UserMessage` with `tool_result` blocks fed back automatically.
4. Repeat until the assistant message contains **no tool calls** ("Turns continue until Claude produces output with no tool calls").
5. Yield `ResultMessage`.

## Budget knobs
- `max_turns` / `maxTurns` — caps tool-use round trips (no default, no limit if unset).
- `max_budget_usd` / `maxBudgetUsd` — dollar cap.
- Quote: *"Setting a budget is a good default for production agents."*

## When a tool is denied
Quote: *"When a tool is denied, Claude receives a rejection message as the tool result and typically attempts a different approach or reports that it couldn't proceed."* — i.e. the model is expected to escalate or pivot on its own when given an error tool_result.

## Compaction (recovery from context overflow)
When context nears the limit, the SDK auto-compacts and emits `compact_boundary`. Persistent constraints belong in CLAUDE.md (re-injected each request) rather than the initial user prompt (gets summarized away).

## Stop reasons (independent of subtype)
`stop_reason` on the last assistant turn: `end_turn`, `max_tokens`, `refusal`. Refusal is detected by string equality.

## Resume pattern
Capture `session_id` from any `ResultMessage` (even error variants). Resume with a larger budget to keep going past `error_max_turns`/`error_max_budget_usd`.

## Recent SDK changelog note
Per anthropics/claude-agent-sdk-typescript CHANGELOG, error result messages (`error_during_execution`, `error_max_turns`, `error_max_budget_usd`) now correctly set `is_error: true` with descriptive messages, and MCP servers retry on the next message instead of being permanently stuck after a connection race.
