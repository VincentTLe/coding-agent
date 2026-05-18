# A5 — Error Handling and Recovery in Agent Loops (2026)

## TL;DR
Treat every loop turn as: *(tool_result | malformed-output | repetition | budget-hit) → react*. The 2026 consensus pattern, used by Claude Code and Aider both, is **bounded in-context recovery**, not unbounded retry: (1) classify the failure (syntactic / semantic / environmental / intentional / refusal), (2) re-prompt the model with the error inlined as `tool_result.is_error=true` (zero backoff for model-side errors; exponential backoff with jitter only for environmental 429/5xx), (3) detect repetition with a `(tool, hash(args))` window and inject steering messages, then dampen, then abort, (4) enforce hard `max_turns` and `max_budget_usd` caps that emit a typed termination subtype the caller can resume from. Aider hard-codes a 3-reflection cap; Claude Code SDK exposes typed result subtypes (`error_max_turns`, `error_max_budget_usd`, `error_during_execution`, `error_max_structured_output_retries`) so the host can resume the session with a larger budget. There is no general "task impossible" signal from the model; you implement it by giving the model an explicit `cannot_proceed(reason)` tool and treating that as a clean exit.

## Why (for this repo)
The coding-agent has a ReAct-style loop with shell + file tools. Without explicit recovery rules, three real failure modes will eat tokens immediately: (a) the model fabricates a tool name or emits JSON that fails parse and the loop just keeps re-asking; (b) a `Bash` call fails for an environmental reason (e.g. network blip) and the model gives up rather than retrying; (c) the model repeats the same broken `Edit` against a file whose contents differ from what it expects. Anthropic itself has an open bug (claude-code#29944) on case (c). We need policy-level handling baked into the loop, not left to model judgment.

## State of the art, 2026
- **Typed terminations as the canonical exit channel.** Claude Code's `ResultMessage.subtype` enumerates the precise reason — `success`, `error_max_turns`, `error_max_budget_usd`, `error_during_execution`, `error_max_structured_output_retries`. All error subtypes still carry `total_cost_usd`, `usage`, `num_turns`, and `session_id`, so a host can resume past a budget hit by re-invoking with a larger cap. The SDK changelog explicitly notes error-result messages now set `is_error: true` with descriptive text.
- **Bounded reflection cycles.** Aider's `base_coder.py` ships `max_reflections = 3` as a class constant. On a malformed SEARCH/REPLACE block or test failure, Aider feeds the diagnostic back as the next user turn and counts the cycle; the fourth attempt prints "Only 3 reflections allowed, stopping." and exits the request. This is a deliberately tight budget — empirical, not theoretical.
- **Reflexion-style verbal self-critique.** The original Reflexion paper (Shinn et al., arXiv 2303.11366) showed verbal post-failure critique stored in an episodic buffer takes HumanEval pass@1 to 91% vs the ~80% baseline at the time. 2026 follow-ups (MAR multi-agent reflexion, structured reflection in LLM agents) consistently report that an *explicit* "why did that fail?" step beats just re-feeding the raw error.
- **Tool-loop detection as a standard scaffold component.** OpenClaw, MiniMax M2.7 (self-evolved scaffold added loop detection for +30% on internal eval, per MarkTechPost 2026-04), and Hermes Agent all expose detection of "same tool + same args + same error". Standard response is escalate-then-abort: inject a steering message → dampen / refuse the duplicate call → abort with `loop_detected`.
- **Error classification drives retry policy.** The shared best-practice writeups (fast.io, mightybot.ai, apxml.com, markaicode.com) all split errors into syntactic / semantic / environmental / intentional, with raw exponential backoff (1s/2s/4s + jitter) reserved for environmental 429/5xx only; model-side errors get re-prompted with the error inline and *no* sleep.
- **"Cannot proceed" is a tool, not a magic phrase.** Modern scaffolds give the model an explicit `AskUserQuestion`-style affordance or a `cannot_proceed(reason)` tool; Claude Code's docs note that on tool denial, "Claude... typically attempts a different approach or reports that it couldn't proceed." There is no implicit give-up signal.

## Most-used pattern (mainstream 2026)
The dominant pattern across Claude Code, Aider, Cursor, and OpenAI Agents SDK:

```
loop:
  on tool error:
    classify → re-prompt with is_error tool_result inline
  on malformed JSON / tool-call schema violation:
    re-prompt with the parser error + the offending text (no backoff)
  on environmental error (429, 5xx, network):
    exponential backoff (1s, 2s, 4s) with jitter, then bubble as is_error tool_result
  on duplicate (tool, args, error) within window N:
    inject "you already tried this, do X different" steering message;
    on persistent duplication, dampen the call; on continued repetition, abort
  on max_turns/max_budget hit:
    emit typed termination; caller decides whether to resume with larger budget
  on model refusal / cannot_proceed tool call:
    clean exit, surface reason
```

## Comparison table

| System | Tool-error feedback | Malformed-output policy | Loop / repetition detection | Step-budget cap | "Cannot proceed" |
|---|---|---|---|---|---|
| **Claude Code SDK** | `tool_result.is_error=true` fed back to model; model decides next action | Structured-output validation with `error_max_structured_output_retries` cap | Not enforced by SDK; relies on model + caller (open bug #29944) | `max_turns`, `max_budget_usd`; emits typed `ResultMessage.subtype` | Implicit — model emits text without tool calls; refusal detected via `stop_reason=="refusal"` |
| **Aider** | Diff/lint/test errors re-fed as next user turn ("reflection") | Same reflection loop; switched edit format after empirical failures | None (model-driven only) | Hard-coded `max_reflections = 3` per request | Prints "Only N reflections allowed, stopping." — no model-side give-up |
| **Cursor (Agent + MCP)** | Returns tool error as tool_result; forum reports agent *exits* on MCP errors instead of recovering (#138088) | ModelBehaviorError raised on malformed tool args | Configurable MCP retry on roadmap; not native | Per-task limit + model-classifier permission mode | Not exposed as a separate signal |
| **OpenAI Agents SDK** | `ModelRetrySettings` with base_delay/max_delay/jitter; ModelBehaviorError vs UserError split | Pydantic validation + Try-Rewrite-Retry pattern | Circuit-breaker pattern recommended | `max_iterations`; "early stopping generate" prompt at cap | Surface via final answer; no dedicated tool |
| **Reflexion (research baseline)** | Verbal critique of the failure stored in episodic memory | Same memory replays into next trial | Implicit via reflection memory ("you tried X and it failed because Y") | Caller-defined trial budget | Not modeled — failure is just another reflection |

## Recommendation for this repo

Adopt **typed-termination + classified-retry + bounded-reflection + repetition-detection**, in roughly that order of importance. Skip exotic LATS/PRM/MCTS scaffolds for v1.

### Concrete pseudocode (drop into the loop body)

```python
MAX_TURNS = 30                # mirror Claude Code default-good-practice
MAX_BUDGET_USD = 5.0          # hard dollar cap
MAX_REFLECTIONS = 3           # mirror Aider
DUP_WINDOW = 8                # last N tool calls
DUP_THRESHOLD = 3             # 3 identical (tool, args) → loop_detected

def classify(err) -> str:
    if isinstance(err, JSONDecodeError | SchemaError):     return "syntactic"
    if isinstance(err, ToolNotFound | BadToolName):        return "intentional"
    if isinstance(err, RateLimit | ServerError | Network): return "environmental"
    if isinstance(err, ToolReturnedError):                 return "semantic"
    return "unknown"

def backoff(attempt):  # only for environmental
    return min(2 ** attempt + random.uniform(0, 0.5), 30.0)

while True:
    if turns >= MAX_TURNS:     return Result("error_max_turns",  session)
    if cost  >= MAX_BUDGET_USD: return Result("error_max_budget", session)

    msg = model.complete(history)

    if no_tool_calls(msg):
        return Result("success", session, text=msg.text)

    if msg.is_cannot_proceed_tool():
        return Result("cannot_proceed", session, reason=msg.reason)

    for call in msg.tool_calls:
        # repetition check BEFORE execution
        key = (call.name, stable_hash(call.args))
        recent.append(key)
        if recent[-DUP_WINDOW:].count(key) >= DUP_THRESHOLD:
            if not steered:
                history.append(tool_result(call, is_error=True,
                    text=f"You have already tried {call.name} with these args "
                         f"{DUP_THRESHOLD}x. Try a different approach or call "
                         f"cannot_proceed(reason=...)."))
                steered = True; break
            return Result("loop_detected", session, last_call=call)

        # execute with classified retry
        for attempt in range(3):
            try:
                out = run_tool(call); is_err = False; break
            except Exception as e:
                cls = classify(e)
                if cls == "environmental" and attempt < 2:
                    time.sleep(backoff(attempt)); continue
                out = format_error(e, cls); is_err = True; break

        history.append(tool_result(call, is_error=is_err, text=out))

    turns += 1
```

Notes on the design:
- **No exponential backoff for model-side errors.** A 400 will be a 400 on retry. Inline the error into the next prompt so the model can fix it.
- **`is_error=true` is the universal signal.** Matches the Anthropic SDK tool-protocol convention and gives the model one consistent input shape for "that didn't work."
- **`cannot_proceed` is a registered tool**, not a string match. Cheap to add, ends the loop deterministically, no false-positive parsing.
- **Repetition steering before aborting.** One steering message ("you already tried this") resolves a lot of stuck loops at near-zero cost; abort is the second line.
- **Reflection budget is implicit in the dup threshold + max_turns**, no separate counter needed. If we later add Reflexion-style explicit critique, set `MAX_REFLECTIONS=3` and require the model to emit a `reflect(diagnosis)` tool call between identical failures.

## Next steps
1. Wire the four-way error `classify()` and the `is_error` tool_result format into the loop.
2. Add the duplicate-detection sliding window keyed on `(tool, stable_hash(args))`.
3. Register a `cannot_proceed(reason)` tool and a `Result` enum with the same subtypes as Claude Code so the harness can resume.
4. Make `MAX_TURNS`, `MAX_BUDGET_USD`, `MAX_REFLECTIONS` config-driven (env vars).
5. Log every error class + retry decision; we will need this to debug loop detection false positives.

## Open questions
- Should environmental-error backoff happen inside the loop (the way OpenAI Agents SDK retries silently) or be surfaced as a recoverable `is_error` for the model to see? [UNVERIFIED] — production reports are mixed.
- For long-running sessions, does verbal Reflexion buy us anything once we already have inline-error re-prompting? The Reflexion paper number is on RL/eval tasks, not real coding agents. [UNVERIFIED for coding-agent setting in 2026].
- "Cannot proceed" granularity — do we want a single tool, or split into `need_clarification` vs `task_blocked` vs `task_impossible`?
- How aggressively should we compact context vs end the session? Claude Code auto-compacts; Aider tells you to `/clear` manually. Probably a 0.8 × max-context trigger to start.

## Sources
- Claude Code Agent SDK — How the agent loop works (Anthropic, 2026). https://code.claude.com/docs/en/agent-sdk/agent-loop
- Anthropic claude-agent-sdk-typescript CHANGELOG (error result subtypes, MCP retry fix). https://github.com/anthropics/claude-agent-sdk-typescript/blob/main/CHANGELOG.md
- anthropics/claude-code issue #29944 — model retries identical failing Edit tool call without diagnosing. https://github.com/anthropics/claude-code/issues/29944
- Aider base_coder.py — `max_reflections = 3`. https://github.com/Aider-AI/aider/blob/main/aider/coders/base_coder.py
- Aider issue #3450 — "Only 3 reflections allowed, stopping." https://github.com/Aider-AI/aider/issues/3450
- Aider issue #3713 — Gemini 2.5 Pro fails SEARCH/REPLACE blocks until 3 retries. https://github.com/Aider-AI/aider/issues/3713
- Aider docs — File editing problems. https://aider.chat/docs/troubleshooting/edit-errors.html
- Shinn et al., Reflexion: Language Agents with Verbal Reinforcement Learning. https://arxiv.org/abs/2303.11366
- MAR: Multi-Agent Reflexion Improves Reasoning Abilities in LLMs (2026). https://arxiv.org/html/2512.20845v1
- Cursor forum #138088 — Agent exits tool-call loop on MCP tool error. https://forum.cursor.com/t/cursor-agent-exits-tool-call-loop-on-mcp-tool-error/138088
- OpenAI Agents Python — Error Recovery Patterns (DeepWiki). https://deepwiki.com/openai/openai-agents-python/14.2-multi-agent-orchestration-examples
- MightyBot — Designing Fault-Tolerant AI Agent Pipelines (idempotency, retries, state). https://mightybot.ai/blog/fault-tolerant-ai-agent-pipelines/
- Fast.io — AI Agent Error Handling: Best Practices & Patterns. https://fast.io/resources/ai-agent-error-handling/
- MarkAICode — Hermes Agent error fixes 2026 (backoff numbers). https://markaicode.com/hermes-agent-not-working-fix/
- MarkTechPost — MiniMax M2.7 self-evolved scaffold added loop detection for +30% (2026-04-12). https://www.marktechpost.com/2026/04/12/minimax-just-open-sourced-minimax-m2-7-a-self-evolving-agent-model-that-scores-56-22-on-swe-pro-and-57-0-on-terminal-bench-2/
- Arun Baby — Error Handling and Recovery in AI Agents. https://www.arunbaby.com/ai-agents/0033-error-handling-recovery/
