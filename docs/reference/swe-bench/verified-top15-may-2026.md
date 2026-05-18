# SWE-Bench Verified — top 15 model-only / self-reported (May 2026)

Source: benchlm.ai (May 13, 2026 snapshot).

| Rank | Model | Org | Type | Verified |
|------|-------|-----|------|----------|
| 1 | Claude Mythos Preview | Anthropic | Closed | 93.9% |
| 2 | Claude Opus 4.7 (Adaptive) | Anthropic | Closed | 87.6% |
| 3 | GPT-5.3 Codex | OpenAI | Closed | 85.0% |
| 4 | Claude Opus 4.5 | Anthropic | Closed | 80.9% |
| 5 | Claude Opus 4.6 | Anthropic | Closed | 80.8% |
| 6 | **DeepSeek V4 Pro (Max)** | DeepSeek | **Open** | 80.6% |
| 7 | **Kimi K2.6** | Moonshot AI | **Open** | 80.2% |
| 8 | GPT-5.2 | OpenAI | Closed | 80.0% |
| 9 | Claude Sonnet 4.6 | Anthropic | Closed | 79.6% |
| 10 | **DeepSeek V4 Pro (High)** | DeepSeek | **Open** | 79.4% |
| 11 | **DeepSeek V4 Flash (Max)** | DeepSeek | **Open** | 79.0% |
| 12 | Qwen3.6 Plus | Alibaba | Closed (API) | 78.8% |
| 13 | **DeepSeek V4 Flash (High)** | DeepSeek | **Open** | 78.6% |
| 14 | MiMo-V2-Pro | Xiaomi | Closed | 78.0% |
| 15 | **GLM-5** | Z.AI | **Open** | 77.8% |
| 16 | **Mistral Medium 3.5 128B** | Mistral | **Open** | 77.6% |
| 17 | Muse Spark | Meta | Closed | 77.4% |
| **18** | **Qwen3.6-27B** | **Alibaba** | **Open** | **77.2%** |
| 19 | Claude Sonnet 4.5 | Anthropic | Closed | 77.2% |
| 20 | Kimi K2.5 (Reasoning) | Moonshot AI | Closed | 76.8% |
| 21 | **Kimi K2.5** | Moonshot AI | **Open** | 76.8% |
| 23 | **Qwen3.5 397B** | Alibaba | **Open** | 76.2% |
| 30 | **Qwen3.6-35B-A3B** | Alibaba | **Open** | 73.4% |
| 35 | **Qwen3.5-27B** | Alibaba | **Open** | 72.4% |

## Top open-weight (no agent assist disclaimer)

1. DeepSeek V4 Pro (Max) — 80.6%
2. Kimi K2.6 — 80.2%
3. DeepSeek V4 Pro (High) — 79.4%
4. DeepSeek V4 Flash (Max) — 79.0%
5. DeepSeek V4 Flash (High) — 78.6%
6. GLM-5 — 77.8%
7. Mistral Medium 3.5 128B — 77.6%
8. **Qwen3.6-27B — 77.2%** ← our model

## Important caveats

- These are **self-reported** numbers, mostly with internal agent scaffolds, not all submitted to swebench.com with trajectories.
- [UNVERIFIED] llm-stats.com cites contamination concerns: "OpenAI has stopped reporting Verified scores after audits found that every frontier model tested (GPT-5.2, Claude Opus 4.5, Gemini 3 Flash) could reproduce verbatim gold patches or problem statement specifics for certain SWE-Bench Verified tasks." OpenAI recommends SWE-Bench Pro instead.
- Agent harness matters: same Claude Sonnet 4.5 can swing 15+ percentage points across different scaffolds (awesomeagents.ai).
</content>
</invoke>