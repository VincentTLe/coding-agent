# ReAct — Yao et al., ICLR 2023

Cached: 2026-05-18. Canonical sources:
- arXiv: https://arxiv.org/abs/2210.03629
- Reference impl: https://github.com/ysymyth/ReAct (MIT)
- Google Research blog: https://research.google/blog/react-synergizing-reasoning-and-acting-in-language-models/

## Idea (one line)
Interleave LLM-generated *Thought*, *Action* (tool call), *Observation* (tool output) in a single loop until done.

## Algorithm
```
state = initial messages
loop:
    response = LLM(state)
    if response has no tool calls: return final
    for each tool_call in response:
        obs = execute(tool_call)
        state.append(tool_call); state.append(obs)
```

## Key claims from the paper
- Outperforms reasoning-only (CoT) and acting-only baselines on HotPotQA, FEVER, ALFWorld, WebShop.
- Reasoning traces help "induce, track, and update action plans as well as handle exceptions."
- Actions let the model "interface with external sources" (search, env).

## 2026 implementation notes
- Native tool-calling APIs (OpenAI, Anthropic, Qwen) make the "Thought:/Action:" text protocol obsolete — use structured `tool_calls` blocks.
- Quadratic prompt growth: every turn re-sends the full transcript. Fight with prefix caching (vLLM, OpenAI, Anthropic all support this), per-tool output truncation, and turn-cap.
- Single most important safety control: hard `max_turns` (typical: 15–30) and `max_total_tokens`. Without them an agent can loop indefinitely on a hard task.

## Where it's used in production (2026)
- Claude Code Agent SDK — explicit ReAct loop with `max_turns` and `max_budget_usd` knobs.
- Codex CLI (OpenAI) — model emits tool calls, loop ends when none remain.
- Cursor Composer — ReAct per agent; multi-agent layer above.
- Aider — model in a loop with tools; differentiator is edit format, not loop.
- OpenHands CodeAct — ReAct with executable-code action space.

## When NOT to use
- Tasks with extremely large search spaces and a cheap verifier → LATS/MCTS may beat it.
- Latency-critical multi-tool tasks where the plan is stable → Plan-and-Execute / LLMCompiler parallelism.
- Tasks with a perfect automated verifier and you want best-effort quality at any cost → wrap in Reflexion.
