# ReWOO — Xu et al., 2023

Cached: 2026-05-18. Canonical sources:
- arXiv: https://arxiv.org/abs/2305.18323
- IBM Think summary: https://www.ibm.com/think/topics/rewoo

## Idea (one line)
"Reasoning WithOut Observation": the planner emits the entire chain (with placeholders for tool outputs) in *one* prompt; workers execute tools (potentially in parallel); a solver synthesizes the final answer.

## Algorithm
```
plan = PlannerLLM(task)              # emits steps like:
                                     # Step 1: Search[query] -> #E1
                                     # Step 2: Calc[#E1.population/2] -> #E2
                                     # ...
observations = {}
for step in plan:                    # workers execute, often in parallel
    observations[step.id] = run_tool(step, observations)
answer = SolverLLM(task, plan, observations)   # final synthesis
```

Two LLM calls total: Planner + Solver.

## Key claims from the paper
- 5× token efficiency vs ReAct on HotpotQA.
- 4% accuracy gain on HotpotQA.
- "Robust under tool-failure scenarios" (relative to ReAct's vulnerability to bad observations cascading).

## Strengths
- Massive token savings (no re-serialization of full history every turn).
- Tool calls can run in parallel by design.
- Clear separation of concerns: plan / execute / solve.

## Weaknesses
- Plan is committed at step 1. **If a tool returns something unexpected, downstream placeholders are wrong and the Solver hallucinates around them.**
- Fundamentally unsuitable for coding agents where the *next* action depends on the *previous* tool's output (e.g. you grep, see N results, then decide which file to read).
- Brittle to tool failure — paper's robustness claim is relative to ReAct, not absolute.

## Production use 2026
- None for coding agents (the search did not surface a single shipping coding agent that uses ReWOO).
- Educational / reference architectures only (IBM Think, agent-patterns library).

## When to use
- Read-only, research-style workflows where the answer is a synthesis of independent tool queries.
- Latency- and cost-bound batch workflows where you can predict tool dependencies up front.
- NEVER for interactive coding where exploration is path-dependent.
