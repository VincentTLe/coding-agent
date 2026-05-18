# Plan-and-Execute (and LLMCompiler)

Cached: 2026-05-18. Canonical sources:
- LangChain blog (canonical framing): https://www.langchain.com/blog/planning-agents
- LLMCompiler (Kim et al., ICML 2024) — paper ID arXiv:2312.04511 [UNVERIFIED — inferred ID; sources cited indirectly]
- BabyAGI / Plan-and-solve lineage: BabyAGI (Nakajima, 2023) and Plan-and-Solve (Wang et al., ACL 2023, arXiv:2305.04091)

## Idea (one line)
A *planner* LLM emits a multi-step plan up front; an *executor* (model or code) carries it out; an optional *replanner* updates it when execution diverges.

## Algorithm
```
plan = PlannerLLM(task)            # 1 call
for step in plan:
    obs = execute(step)             # often cheap model or pure code
    if diverged: plan = ReplannerLLM(task, plan, history)   # optional
return Solver(history)
```

## LLMCompiler variant
- Planner emits a *DAG* of tool calls, not a linear list.
- Independent nodes run in parallel.
- Reported 3.6× speedup over sequential ReAct on planning benchmarks; up to 9× cost savings.

## Strengths
- Fewer expensive LLM turns on long-horizon tasks.
- Parallel tool execution (LLMCompiler).
- The plan itself is auditable artifact (good for governance/safety reviews).

## Weaknesses
- Brittle when reality doesn't match the plan — typical in coding (a `pytest` failure changes everything).
- Two-LLM architecture: double the prompt surface, double the failure surface.
- Replanner is a non-trivial loop in itself; how often to replan is a tunable with no good default.

## Production use 2026
- **Anthropic's multi-agent research system** uses an orchestrator/lead-agent that plans and delegates to subagent workers in parallel — closest production analogue to plan-and-execute. (Not coding-focused.)
- **Claude Code does NOT use a separate planner LLM.** Its "plan mode" is a permission setting on the same ReAct loop that restricts the agent to read-only tools and asks it to produce a plan first. Same model, same loop.
- No major coding agent (Claude Code, Cursor, Codex, Aider, OpenHands) uses a true planner/executor split for the coding loop.

## When to use
- Plan is *stable* (no surprises expected at execution time).
- Latency dominates (parallelizable tool calls).
- A governance/audit requirement makes the plan-artifact valuable.
