# τ-bench (TAU-bench) reference

Source: sierra-research/tau-bench (https://github.com/sierra-research/tau-bench), τ²-bench (https://github.com/sierra-research/tau2-bench), τ-bench paper (https://arxiv.org/pdf/2406.12045)

## What it tests
Tool-Agent-User Interaction: agent must use API tools AND converse with an LLM-simulated user to complete enterprise domain tasks (retail, airline, telecom). Multi-turn. Evaluates pass^k (consistency across multiple trials), not just pass@1. Programmatic grading: database state comparison after task.

## Domains
- τ-retail: ~115 tasks
- τ-airline: ~50 tasks
- τ²-telecom: dual-control (agent + user both have tools)
- τ³ in progress (2026)

## Setup
- Pure Python pip install. No Docker needed.
- Set OpenAI/Anthropic/Google/Mistral/AnyScale API keys as env vars.
- For local model: launch via vLLM, point as OpenAI-compatible base_url.
- Historical trajectories in ./historical_trajectories for cheap re-grading.

## Cost
- τ-retail one trial / task with gpt-4o + gpt-4 user-sim: ~$200 (one full run).
- τ²-bench all domains, 1 trial: ~$40.
- 95.9% of cost is INPUT prompt (long domain policy + function defs).
- For local Qwen via vLLM: ~free except electricity; user-sim still costs API $.

## Leaderboard (May 2026)
- τ-retail top: Claude Sonnet 4.5 = 0.862; Step-3.5-Flash = 0.882 (LLM-Stats).
- BenchLM overall: Claude Mythos Preview = 89.2%.
- τ²-telecom top: JT-35B-Flash = 99.1%, GLM-4.7-Flash = 98.8%.

## Realistic vs synthetic
Synthetic environment (Python state DB + simulated user) but tasks are written from real enterprise policies. More "realistic" than AgentBench/AgentBoard because policies are dense and tasks require negotiation, not just tool dispatch.

## Critical
- User-simulator quality matters: if user-LLM weaker than agent-LLM, scores noisy.
- Pass^k decay (consistency) often more important than pass^1.
