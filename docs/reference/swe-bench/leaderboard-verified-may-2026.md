# SWE-Bench agents and scaffolds in 2026

## Top "agent + model" entries (Verified)

Source: awesomeagents.ai, codesota, kilo.ai (all aggregators, May 2026).

| Rank | Agent | Base model | Verified | Agent open source |
|------|-------|-----------|----------|-------------------|
| 1 | Augment Code SWE-Agent | Claude Opus 4.6 | 72.0% | No |
| 2 | OpenHands + CodeAct v3 | Claude Opus 4.6 | 68.4% | **Yes** |
| 3 | Cursor Background Agent | Claude Sonnet 4.6 | 65.7% | No |
| 4 | Composio SWE-Kit | Claude Sonnet 4.6 | 62.3% | No |
| 5 | Cline (Autonomous Mode) | Claude Sonnet 4.6 | 59.8% | **Yes** |
| 6 | Factory Droid | GPT-5.3-Codex | 58.1% | No |
| 7 | Devin 2.0 | Proprietary | 45.8% | No |
| 8 | OpenHands + CodeAct v2 | GPT-5.2 | 44.7% | **Yes** |
| 9 | SWE-agent v1 | Claude Sonnet 4.5 | 43.2% | **Yes** |
| 10 | AutoCodeRover v2 | GPT-5.2 | 38.6% | No |

## Open-weight × open agent combos

- OpenHands + Qwen3-Coder-480B-A35B-Instruct: 69.6% Verified (500-turn setting), submitted Aug 2025.
- OpenHands + Qwen3-Coder-Next: 71.3% Verified.
- SWE-agent + Qwen3-Coder-Next: 70.6% Verified.
- mini-SWE-agent + Qwen3-Coder-Next: 71.1% Verified.
- Moatless + Llama 4 Maverick: 14.7% Verified — "best fully self-hosted" per morphllm.com, but very weak relative to API-backed systems. [UNVERIFIED]

## mini-SWE-agent

- 100-line agent, bash-only tool, no native tool-calling required.
- Princeton/Stanford team; same group as the original SWE-bench.
- Reported score: >74% Verified (depends on which frontier model).
- This is the closest "shape" to a from-scratch coding agent.

## SWE-Bench Lite top-10 (May 2026)

| Rank | Model (no agent specified) | Score |
|------|----------------------------|-------|
| 1 | Claude Opus 4.6 (Thinking) | 62.7% |
| 2 | Claude Opus 4.6 | 62.7% |
| 3 | MiniMax M2.5 | 56.3% |
| 4 | GPT-5 | 54.3% |
| 5 | Claude Haiku 4.5 (Thinking) | 54.3% |
| 6 | Claude Haiku 4.5 | 54.3% |
| 7 | GLM-5 (Thinking) | 53.3% |
| 8 | GLM-5 | 53.3% |
| 9 | Claude Opus 4.5 (Thinking) | 49.3% |
| 10 | Claude Opus 4.5 | 49.3% |
| 11 | Qwen3-Coder-480B | 44.7% |
| 12 | Kimi K2 0711 | 42.0% |

Source: pricepertoken.com. Note: Lite is ~300 tasks vs Verified's ~500, easier subset.
</content>
</invoke>