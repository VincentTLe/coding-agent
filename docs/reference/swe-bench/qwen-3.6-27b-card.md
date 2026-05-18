# Qwen 3.6-27B SWE-Bench scores

## Official model card (huggingface.co/Qwen/Qwen3.6-27B)

- SWE-Bench Verified: **77.2%**
- SWE-Bench Pro: 53.5%
- SWE-Bench Multilingual: 71.3%
- Terminal-Bench 2.0: 59.3
- SkillsBench: 48.2

## Methodology (from model card)

> "SWE-Bench Series: Internal agent scaffold (bash + file-edit tools); temp=1.0, top_p=0.95, 200K context window. We correct some problematic tasks in the public set of SWE-bench Pro and evaluate all baselines on the refined benchmark."

Key points:
- Used **internal** agent scaffold (NOT OpenHands, NOT SWE-agent, NOT mini-SWE-agent).
- Tools: bash + file-edit only (matches the shape of mini-SWE-agent).
- Temp 1.0, top_p 0.95.
- 200K context window.
- Released April 21, 2026.

## Leaderboard position

- Rank 18 of 46 on the Verified self-reported leaderboard (benchlm.ai).
- Beats Qwen 3.5-397B (76.2%) while 14× smaller.
- Within 3.7 points of Claude Opus 4.6 (80.8%).
- **No public SWE-Bench Lite score** for this specific model.

## Has it been submitted to official leaderboard?

- Self-reported on the model card.
- benchlm.ai and llm-stats.com aggregate it.
- swebench.com viewer dropdown does NOT currently list Qwen3.6-27B (it lists Qwen3-Coder 480B, Qwen2.5-Coder 32B). [UNVERIFIED whether an official submission with reproducible trajectories exists.]
</content>
</invoke>