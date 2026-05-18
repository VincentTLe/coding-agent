# Reflexion — Shinn et al., NeurIPS 2023

Cached: 2026-05-18. Canonical sources:
- arXiv: https://arxiv.org/abs/2303.11366
- Reference impl: https://github.com/noahshinn/reflexion (MIT)
- OpenReview: https://openreview.net/forum?id=vAElhFcKW6

## Idea (one line)
Outer retry loop: Actor attempts, Evaluator scores, Self-Reflector writes a verbal critique into memory, Actor retries with that memory.

## Algorithm
```
memory = []
for trial in range(max_trials):
    trajectory = Actor(task, memory)         # internally a ReAct loop
    score = Evaluator(trajectory)            # tests / heuristic / LLM judge
    if score is perfect: return trajectory
    critique = SelfReflector(trajectory, score)
    memory.append(critique)
return best_trajectory
```

## Key results from the paper
- HumanEval pass@1: 80% → 91% (GPT-4 → GPT-4 + Reflexion).
- AlfWorld: +22 absolute points over baseline in 12 iterative learning steps.
- HotPotQA: +20 absolute points.

## Strengths
- Best when a *clean automatic verifier* exists (unit tests, compile success, exact match).
- Critique is human-readable — debuggable.

## Weaknesses (2025-2026 follow-up evidence)
- Every retry is a full task run → expensive.
- Same-model judge: a 2025 replication noted that single-agent Reflexion "consistently repeats earlier misconceptions across retries because the same model generates both the output and the critique."
- **Hallucinated task specifications**: a documented failure mode where the self-reflector confidently redefines the task and the actor then optimizes against the wrong objective.
- Local minima: in WebShop, a 2-shot ReAct + Reflexion agent showed no improvement after 4 trials.

## Production use 2026
- Not used as the core loop by any major coding agent.
- The *shape* (actor + critic) is occasionally used as a subagent inside a larger ReAct system — e.g. a "verify" subagent invoked once after the main agent finishes.

## When to use
- You have a perfect verifier (a passing test suite).
- Latency is not critical and budget allows N×retries.
- The task is bounded enough that "redefine the task" hallucination is unlikely.

## When to avoid
- Open-ended coding tasks without a verifier — high risk of confidently wrong critiques.
- Latency-bound interactive UX.
