# A1: Agent Loop Patterns in 2026 — ReAct, Plan-and-Execute, Reflexion, ReWOO

Research date: 2026-05-18. Author: research agent for `/home/tle/code/coding-agent`.

## TL;DR

- **Use ReAct (Thought → Action → Observation, repeat) as the core loop** for a from-scratch coding agent in 2026. Every major production coding agent — Claude Code, Cursor, OpenHands, Codex CLI — is a ReAct-style `while not done: model → tools → results` loop. The interesting engineering lives in tools, context management, permissions, and stop conditions, **not** in the loop itself ([Steve Kinney 2026](https://stevekinney.com/writing/agent-loops); [Augment Code on Claude SDK](https://www.augmentcode.com/guides/claude-agent-sdk-agent-loops-tool-calls)).
- Plan-and-Execute, Reflexion, ReWOO, and LATS remain academically interesting; none has displaced ReAct in production coding agents. Reflexion-style self-critique is sometimes *layered on top* of ReAct (e.g. via a "verify" subagent) but rarely replaces it.
- For a Math/Stat 361 demo on Qwen 3.6-27B (BF16, vLLM, OpenAI SDK), the right shape is: tool-calling loop, hard `max_turns` cap (15–30), hard token-budget cap, structured stop-reason handling, and *one* file-edit tool with a robust edit format (search-replace block). Plan/Reflect can be added later as observable hooks, not core control flow.

## Why this matters for this project

The owner needs to understand every line. ReAct is the only pattern with a one-page mental model that fits that constraint: the model emits text and tool calls; we execute the tools; we feed results back; we stop when the model emits no tool calls or we hit a budget. Plan-and-Execute splits this into two LLMs (planner + executor + replanner) with non-trivial state; ReWOO front-loads a multi-step plan in a single prompt and breaks when a tool returns something unexpected; Reflexion adds an outer retry loop with an evaluator and a "self-reflection" LLM. All of those are 3–5x more code and 2–5x more LLM calls per task. None of them improves SWE-bench scores enough on a 27B model to be worth the complexity right now (gap on SWE-Bench Verified between scaffold choices on the same model: ~5 pp; [SWE-Bench Pro analysis, Morph 2026](https://www.morphllm.com/swe-bench-pro)).

Demo is 2026-05-29 (11 days). The risk is not "wrong loop pattern"; it's "loop runs forever, edits the wrong file, or burns the token budget". A boring ReAct loop with strict caps and good tools wins.

## SOTA 2026 — the five patterns at a glance

### 1. ReAct (Yao et al., ICLR 2023)
**Source**: [arXiv:2210.03629](https://arxiv.org/abs/2210.03629) — Yao, Zhao, Yu, Du, Shafran, Narasimhan, Cao.
**How it works**: Single LLM. At each step it emits a *thought* (free-form reasoning), then an *action* (tool call), then receives an *observation* (tool result). Loop continues until the model outputs a "final answer" / stops calling tools. In modern implementations the "thought" is implicit in the model's tool-calling stream — you don't even need to prompt for `Thought:` tokens, since native tool-calling APIs (OpenAI, Anthropic, Qwen) already emit reasoning blocks before tool calls.
**Strengths**: Trivially implementable (~60 lines of Python over the OpenAI SDK; [AI Builder Club 2026](https://www.aibuilderclub.com/blog/how-to-build-ai-agent-from-scratch)). Adapts to mid-task discoveries. Plays nicely with tool-calling fine-tuning. Reasoning trace is itself debuggable.
**Weaknesses**: Each turn re-sends the full transcript (quadratic input cost without prompt caching; [Augment Code 2026](https://www.augmentcode.com/guides/ai-agent-loop-token-cost-context-constraints)). Susceptible to "looping" failure where the model keeps trying minor variations of a failed action. Needs explicit safety caps.
**Production use 2026**: Default in Claude Code Agent SDK ([code.claude.com docs](https://code.claude.com/docs/en/agent-sdk/agent-loop)), Codex CLI ([OpenAI 2026](https://openai.com/index/unrolling-the-codex-agent-loop/)), OpenAI Agents SDK runner ([developers.openai.com](https://developers.openai.com/api/docs/guides/agents/running-agents)), OpenHands CodeAct agent.

### 2. Plan-and-Execute (LangChain framing; Kim et al. LLMCompiler ICML 2024)
**Source**: [LangChain blog](https://www.langchain.com/blog/planning-agents); LLMCompiler [arXiv:2312.04511](https://arxiv.org/abs/2312.04511) (Kim et al.) [UNVERIFIED — paper ID inferred, confirmed via secondary source [Wollen Labs 2025](https://www.wollenlabs.com/blog-posts/navigating-modern-llm-agent-architectures-multi-agents-plan-and-execute-rewoo-tree-of-thoughts-and-react)].
**How it works**: A *planner* LLM produces a structured multi-step plan up front. An *executor* (often a cheap model or pure code) walks the plan; a *replanner* updates it when execution diverges. LLMCompiler additionally extracts a DAG of tool calls so independent steps run in parallel.
**Strengths**: Fewer expensive LLM turns for long-horizon tasks. LLMCompiler reports up to 3.6× speedup over sequential ReAct on planning benchmarks ([Wollen Labs 2025](https://www.wollenlabs.com/blog-posts/navigating-modern-llm-agent-architectures-multi-agents-plan-and-execute-rewoo-tree-of-thoughts-and-react)).
**Weaknesses**: Brittle when the world doesn't match the plan (the typical case in coding — tests fail, paths don't exist, an import breaks). Replanner is a second source of bugs. Two-LLM architecture doubles code and prompt surface.
**Production use 2026**: Anthropic's multi-agent *research* system uses a planner/orchestrator that delegates to subagent workers ([Anthropic engineering 2025](https://www.anthropic.com/engineering/built-multi-agent-research-system)) — but their coding agent (Claude Code) does **not** use a separate planner LLM. Claude Code has a "plan mode" that is still one model: it just runs read-only tools and emits a plan text before any editing ([code.claude.com docs](https://code.claude.com/docs/en/agent-sdk/agent-loop), `permission_mode: "plan"`).

### 3. Reflexion (Shinn et al., NeurIPS 2023)
**Source**: [arXiv:2303.11366](https://arxiv.org/abs/2303.11366) — Shinn, Cassano, Berman, Gopinath, Narasimhan, Yao.
**How it works**: Three roles. *Actor* attempts the task (often ReAct internally). *Evaluator* scores the output (test pass, heuristic, or LLM judge). *Self-reflector* produces verbal critique. The critique is appended to memory; the actor retries. Reported HumanEval pass@1 jumped from 80% (GPT-4 baseline) to 91% in the paper.
**Strengths**: Best when there is a clean, automatic verifier (unit tests, compile success). Critique is human-readable, so debuggable.
**Weaknesses**: Every retry is a *full* run — expensive. A 2025 replication study found single-agent Reflexion often "hallucinates a new task specification" and steers further from the goal across retries because the same model both produces and critiques the work ([Reflexion limitations review](https://medium.com/@milesk_33/the-silent-failures-when-ai-agents-break-without-alerts-23a050488b16); pattern in [agent-patterns docs](https://agent-patterns.readthedocs.io/en/stable/patterns/reflexion.html)). Susceptible to local minima ([Shinn et al. §6](https://arxiv.org/abs/2303.11366)).
**Production use 2026**: Not used as the *core* loop by any major coding agent. The shape *is* used as an evaluator subagent in Anthropic's research system and in Cursor's `/multitask` flow, but those are still ReAct loops with an extra critic node.

### 4. ReWOO (Xu et al., 2023)
**Source**: [arXiv:2305.18323](https://arxiv.org/abs/2305.18323) — Xu, Peng, et al.
**How it works**: *Planner* emits the entire chain — including placeholders for tool outputs — in one prompt. *Worker* executes all the tool calls (often in parallel). *Solver* synthesizes the final answer from observations. Only **two** LLM calls total per task.
**Strengths**: ~5× token efficiency vs ReAct on HotpotQA. Tool calls can run in parallel.
**Weaknesses**: Plan is committed at step 1. If a tool fails or returns surprising data, the placeholders downstream are wrong and the solver hallucinates around them. Fundamentally unsuitable for "explore-then-edit" coding workflows where the next action depends on what `grep` or `cat` returned ([Nutrient 2025](https://www.nutrient.io/blog/rewoo-vs-react-choosing-right-agent-architecture/)).
**Production use 2026**: Reference architecture; appears in IBM educational material ([IBM what-is-rewoo](https://www.ibm.com/think/topics/rewoo)). No production coding agent uses it.

### 5. LATS — Language Agent Tree Search (Zhou et al., 2023)
**Source**: [arXiv:2310.04406](https://arxiv.org/pdf/2310.04406).
**How it works**: Wraps ReAct in Monte Carlo Tree Search. Each node is a state; the agent expands several candidate next actions, rolls out, evaluates, and backpropagates. Unifies reasoning, acting, planning.
**Strengths**: Higher ceiling on hard reasoning benchmarks; outperforms ReAct and Reflexion on selected tasks.
**Weaknesses**: *Many* model calls per task (rollouts × branches × depth). Latency and cost are prohibitive for interactive coding. Verifier quality dominates results.
**Production use 2026**: Research demonstrations only. Not used in any shipping coding agent the search surfaced.

## Most-widely-used in production coding agents (2026)

Every shipped product converges on **ReAct with tool-calling**, then differentiates on context engineering, tools, and orchestration around the loop. Concrete confirmations:

- **Claude Code / Claude Agent SDK** — explicit ReAct: "Receive prompt → Evaluate and respond → Execute tools → Repeat → Return result" with `max_turns` and `max_budget_usd` caps; built-in tools (`Read`, `Edit`, `Write`, `Glob`, `Grep`, `Bash`, `WebSearch`, `WebFetch`, `Agent` for subagent spawn). "Plan mode" is a permission setting on the same loop, not a different loop ([code.claude.com docs](https://code.claude.com/docs/en/agent-sdk/agent-loop)).
- **Codex CLI (OpenAI)** — "core agent loop works by having user input trigger inference, the model may issue tool calls whose outputs are appended to the prompt, and the cycle repeats until the model produces a final assistant message" ([OpenAI blog, Feb 2026](https://openai.com/index/unrolling-the-codex-agent-loop/)). Stateless turns, aggressive prefix caching to fight quadratic prompt growth. Codex `/goal` adds a built-in autonomous outer loop on top.
- **Cursor Composer / Agents Window** — ReAct loop per agent; Cursor 2.0/3.0 adds parallel subagents in separate git worktrees, each driving its own ReAct loop, coordinated by an orchestrator ([Cursor scaling blog](https://cursor.com/blog/scaling-agents); [Cursor agent best practices](https://cursor.com/blog/agent-best-practices)).
- **Aider** — "A coding agent is a model in a loop with tools" ([Morph 2026](https://www.morphllm.com/build-your-own-coding-agent)); ReAct loop with two notable design choices: (1) git-native (every edit is a commit), (2) pluggable *edit formats* (whole-file, diff, search-replace, "architect/editor" two-model pair). Edit-format choice changes the *same model's* score by +8% on average across 16 models tested in 2026 — the loop is unchanged, only how the model is asked to express edits ([Morph 2026](https://www.morphllm.com/build-your-own-coding-agent)).
- **OpenHands CodeAct** — ReAct with a unified executable-code action space: `IPythonRunCellAction`, `CmdRunAction`, `BrowserInteractiveAction` ([OpenHands README](https://github.com/OpenHands/OpenHands/blob/main/openhands/agenthub/codeact_agent/README.md); [OpenHands arXiv 2407.16741](https://arxiv.org/html/2407.16741v3)). The 2026 v2 SDK paper [arXiv:2511.03690](https://arxiv.org/html/2511.03690v1) keeps the same loop shape.

A 2026 spread benchmark on SWE-Bench Verified with a fixed model (Claude Opus 4.5) showed scores vary from 50.2% to 55.4% based purely on agent scaffold differences ([SWE-Bench Pro analysis, Morph 2026](https://www.morphllm.com/swe-bench-pro)) — i.e. ~5pp lives in scaffold, ~30pp lives in the model. Spending complexity budget on a fancy loop is a bad trade.

## Comparison table

| Pattern | Origin (date) | License (of canonical impl) | Key differentiator | Best for | Worst for | LLM calls / task | Used in production coding agents 2026? |
|---|---|---|---|---|---|---|---|
| ReAct | Yao et al., Oct 2022 (arXiv) / ICLR 2023 | MIT (ysymyth/ReAct) | Interleave Thought/Action/Observation in one loop | Any task with feedback; default for tool-use | Tasks with very deep search trees | N (one per turn, N=turns) | Yes — Claude Code, Codex, Cursor, Aider, OpenHands |
| Plan-and-Execute / LLMCompiler | Wang et al. 2023; Kim et al. ICML 2024 | Apache-2.0 (LLMCompiler) | Upfront plan, parallel exec, optional replanner | Long-horizon, mostly-stable plans, latency-sensitive multi-tool flows | Volatile envs where next step depends on last result (most coding) | 2 + replans | Partial — Anthropic research orchestrator; not Claude Code |
| Reflexion | Shinn et al., Mar 2023 / NeurIPS 2023 | MIT (noahshinn/reflexion) | Outer retry loop with verbal self-critique stored in memory | Tasks with clean automatic verifier (tests, compilers) | Open-ended tasks; same-model judge falls into local minima | (Actor + Eval + Reflect) × retries | As an evaluator subagent; never the core loop |
| ReWOO | Xu et al., May 2023 | Apache-2.0 (billxbf/ReWOO) | Decouple plan from observation; single planner emits the whole chain | Read-only research with parallel tool calls | Coding (next step depends on previous tool output) | 2 | No |
| LATS | Zhou et al., Oct 2023 | MIT | MCTS over thought/action tree | Hard reasoning with cheap verifier | Interactive UX, cost-bounded systems | Branches × depth × rollouts | No |

## Recommendation

**Implement plain ReAct over the OpenAI SDK Chat Completions / Responses API**, using native function-calling against the vLLM endpoint serving Qwen 3.6-27B. Specifically:

1. One model in one loop. No planner/executor split. No outer Reflexion retry.
2. Native tool calling (the SDK already emits `tool_calls` blocks). Don't roll your own `Thought:`/`Action:` text parser — it's a sharp edge that ate hours in 2022-2023 implementations and is now obsolete.
3. Hard caps: `max_turns` (start at 20), `max_tokens_total` (start at 200k for a 27B run), per-tool timeouts, per-task wall-clock cap. **Caps that print a clear stop reason are the difference between a demo and a debugging session.**
4. Termination: stop when the model's response has no `tool_calls`. Mirror Claude Code's `stop_reason`: `end_turn`, `max_tokens`, `refusal`, `error_max_turns`, `error_max_budget_usd`.
5. Tool set for v1: `read_file`, `write_file` (with a search-replace edit format — see snippets below), `list_dir`, `grep`, `run_bash` (sandboxed, read-only env vars). Five tools is enough to be Turing-complete-in-practice for the demo.
6. Context strategy: persist the full transcript in memory; let vLLM's prefix caching (or just the natural KV cache reuse with chat templates) absorb the quadratic cost up to ~30 turns. Add a "summarize older turns" compaction step only when the demo task needs it.
7. Logging: emit a structured event per turn (`turn_index`, `tool_name`, `tool_args_hash`, `tokens_in`, `tokens_out`, `duration_ms`). This is the OTel-genai surface area you already have in `docs/reference/otel-genai/`.

What to skip for the demo: Plan-and-Execute (adds a second LLM you have to debug), Reflexion (the demo task already has a human evaluator: the audience), ReWOO (coding workflows violate its assumption), LATS (cost killer).

## Concrete next steps (code snippets)

### Minimal ReAct loop (Python 3.12, OpenAI SDK, vLLM endpoint)

```python
# coding_agent/loop.py
from dataclasses import dataclass
from typing import Any, Callable
from openai import OpenAI

@dataclass
class StopReason:
    kind: str            # "end_turn" | "max_turns" | "max_tokens" | "error"
    detail: str = ""

def run_agent(
    client: OpenAI,
    model: str,
    system_prompt: str,
    user_prompt: str,
    tools_schema: list[dict],          # OpenAI-style tool JSON schemas
    tool_impls: dict[str, Callable[[dict], str]],
    max_turns: int = 20,
    max_total_tokens: int = 200_000,
) -> tuple[str, StopReason, list[dict]]:
    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_prompt},
    ]
    total_tokens = 0

    for turn in range(max_turns):
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools_schema,
            tool_choice="auto",
            temperature=0.2,
        )
        if resp.usage:
            total_tokens += resp.usage.total_tokens
            if total_tokens > max_total_tokens:
                return "", StopReason("max_tokens", f"{total_tokens}"), messages

        msg = resp.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))

        if not msg.tool_calls:
            # No tool calls => model is done.
            return msg.content or "", StopReason("end_turn"), messages

        # Execute each tool call sequentially. Parallel execution is an
        # optimization; do it later once correctness is locked.
        for call in msg.tool_calls:
            name = call.function.name
            args = _safe_json(call.function.arguments)
            try:
                result = tool_impls[name](args)
            except Exception as e:                       # noqa: BLE001
                result = f"ERROR: {type(e).__name__}: {e}"
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": result[:8000],                 # cap a single observation
            })

    return "", StopReason("max_turns", str(max_turns)), messages


def _safe_json(s: str) -> dict:
    import json
    try:
        return json.loads(s)
    except Exception:
        return {"_raw": s}
```

That is the whole loop. Everything else lives in `tools_schema` / `tool_impls`, the system prompt, and the logging hooks.

### Recommended edit-format tool (search-replace block)

Aider's 2026 testing showed +8% on coding accuracy from edit-format choice alone ([Morph 2026](https://www.morphllm.com/build-your-own-coding-agent)). Use a search-replace format because it's robust to model whitespace inconsistencies and gives a clear error when the model gets the original text wrong:

```python
# coding_agent/tools/edit.py
from pathlib import Path

def edit_file(args: dict) -> str:
    """
    args = {"path": "src/foo.py", "search": "...", "replace": "..."}
    The 'search' string MUST match exactly once. If it matches zero or
    multiple times, the tool returns an explicit error so the model can
    retry with more surrounding context (Aider's loop-of-tightening trick).
    """
    p = Path(args["path"])
    text = p.read_text()
    needle = args["search"]
    n = text.count(needle)
    if n == 0:
        return f"ERROR: search block not found in {p}. Re-read the file and copy exact text."
    if n > 1:
        return f"ERROR: search block matches {n} locations in {p}. Add more surrounding context to disambiguate."
    p.write_text(text.replace(needle, args["replace"], 1))
    return f"OK: edited {p} ({len(args['search'])}→{len(args['replace'])} chars)"
```

### Tool schemas (OpenAI function-calling format)

```python
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file and return its contents.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Edit a file by replacing a unique search block.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path":    {"type": "string"},
                    "search":  {"type": "string"},
                    "replace": {"type": "string"},
                },
                "required": ["path", "search", "replace"],
            },
        },
    },
    # list_dir, grep, run_bash similar
]
```

### Suggested system prompt skeleton

```text
You are a coding agent. You can call tools. After each tool result, decide
whether to call another tool or to write a final answer. When you have
nothing left to do, respond with a normal message and no tool calls.

Rules:
- Read files before editing them. Edits must match the file's exact text.
- Prefer small, reversible edits. Commit nothing.
- If a test fails, read the test and the implementation before guessing.
- When uncertain, ask via a final message rather than guessing destructively.
```

### Order of work (this week)

1. (Day 1) Get the loop above running against vLLM. Hard-code a single trivial tool (`echo`) and confirm a clean end-turn termination.
2. (Day 2) Add `read_file`, `list_dir`, `grep`. Demo: "find every TODO in this repo and summarize them."
3. (Day 3) Add `edit_file` with search-replace. Demo: "rename the function `foo` to `bar` in `src/utils.py`."
4. (Day 4) Add `run_bash` with a 10s timeout, blocked outside the repo root. Demo: "run `pytest` and fix the one failing test."
5. (Day 5) Structured event logging → OTel. Verify the max-turns and max-tokens caps both trigger cleanly under stress.
6. (Day 6+) Only then consider: plan-mode (read-only first turn), a critic subagent, prompt caching, parallel tool execution.

## Open questions

1. **Does Qwen 3.6-27B's native tool-calling format match OpenAI's function-calling JSON?** vLLM's `--enable-auto-tool-choice` plus the right `--tool-call-parser` should make this work, but the Qwen 3.6 tool-call template needs to be verified end-to-end before relying on it. [UNVERIFIED — needs an empirical check against the deployed endpoint.]
2. **Should we cache the system prompt and tool schemas via vLLM prefix caching, or rely on KV reuse from the chat template?** vLLM 2026 supports both; perf delta is the experiment to run.
3. **Does the demo benefit from a plan-mode read-only first pass?** Claude Code defaults to it; for a 5-minute live demo it may be friction rather than safety.

## Sources

Official documentation:
- [Claude Code Agent SDK — How the agent loop works](https://code.claude.com/docs/en/agent-sdk/agent-loop) (Anthropic, 2026)
- [OpenAI — Unrolling the Codex agent loop](https://openai.com/index/unrolling-the-codex-agent-loop/) (Feb 2026)
- [OpenAI — Function calling guide](https://developers.openai.com/api/docs/guides/function-calling)
- [OpenAI — Running agents (Agents SDK)](https://developers.openai.com/api/docs/guides/agents/running-agents)
- [Cursor — Scaling long-running autonomous coding](https://cursor.com/blog/scaling-agents)
- [Cursor — Best practices for coding with agents](https://cursor.com/blog/agent-best-practices)
- [OpenHands CodeAct agent README](https://github.com/OpenHands/OpenHands/blob/main/openhands/agenthub/codeact_agent/README.md)
- [LangChain — Plan-and-execute agents](https://www.langchain.com/blog/planning-agents)
- [Aider — Edit formats](https://aider.chat/docs/more/edit-formats.html)

Primary papers (arXiv):
- ReAct — [Yao et al., arXiv:2210.03629](https://arxiv.org/abs/2210.03629)
- Reflexion — [Shinn et al., arXiv:2303.11366](https://arxiv.org/abs/2303.11366)
- ReWOO — [Xu et al., arXiv:2305.18323](https://arxiv.org/abs/2305.18323)
- LATS — [Zhou et al., arXiv:2310.04406](https://arxiv.org/pdf/2310.04406)
- OpenHands — [Wang et al., arXiv:2407.16741](https://arxiv.org/html/2407.16741v3)
- OpenHands SDK v2 — [arXiv:2511.03690](https://arxiv.org/html/2511.03690v1)

Industry analyses (≤ 6 months old):
- [Anthropic — How we built our multi-agent research system](https://www.anthropic.com/engineering/built-multi-agent-research-system) (2025)
- [Morph — How AI Coding Agents Work / Build Your Own](https://www.morphllm.com/build-your-own-coding-agent) (2026)
- [Morph — SWE-Bench Pro Leaderboard 2026](https://www.morphllm.com/swe-bench-pro)
- [Augment Code — Agent loop token cost and context constraints](https://www.augmentcode.com/guides/ai-agent-loop-token-cost-context-constraints) (2026)
- [Nutrient — ReWOO vs ReAct](https://www.nutrient.io/blog/rewoo-vs-react-choosing-right-agent-architecture/) (2025)
- [The AI Engineer — The 4 single-agent patterns](https://theaiengineer.substack.com/p/the-4-single-agent-patterns) (2025)
- [Wollen Labs — Navigating modern LLM agent architectures](https://www.wollenlabs.com/blog-posts/navigating-modern-llm-agent-architectures-multi-agents-plan-and-execute-rewoo-tree-of-thoughts-and-react)
- [Steve Kinney — The Anatomy of an Agent Loop](https://stevekinney.com/writing/agent-loops)
- [IBM Think — What is a ReAct Agent?](https://www.ibm.com/think/topics/react-agent)
- [IBM Think — What is ReWOO?](https://www.ibm.com/think/topics/rewoo)
