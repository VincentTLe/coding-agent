# C5 — Agent benchmarks landscape, May 2026

## TL;DR

For a from-scratch Qwen 3.6-27B agent on 2× A6000 with a May 29 demo, the only realistically runnable benchmarks are **τ-bench (retail+airline)** and **GAIA validation (Level 1)**. SWE-Bench is covered separately (C2). OSWorld, SWE-Lancer, WebArena need either multimodal/VLM, heavy infra, or Docker per-task. AgentBench/AgentBoard are runnable but the field has largely moved on.

## Why this matters

We need a **single number** (or small table) for the demo deck that lets reviewers compare our agent to public results. The bench must (1) be runnable in days on our 2× A6000, (2) tolerate a text-only Qwen via OpenAI-compatible vLLM endpoint, (3) have credible 2026 leaderboard entries to compare against.

## SOTA & most-cited (May 2026)

| Bench | Top 2026 | Score | Open-weight best | Notes |
|---|---|---|---|---|
| τ-retail | Claude Sonnet 4.5 | 0.862 | n/a published | Step-3.5-Flash 0.882 [llm-stats] |
| τ²-telecom | JT-35B-Flash | 99.1% | JT-35B-Flash | GLM-4.7-Flash 98.8% |
| GAIA val | OpenAI Deep Research | 72.57% | n/a in top-10 | Trase 70.3% val, 67% test |
| OSWorld-Verified | Claude Mythos Preview | 79.6% | Qwen3-VL-235B 66.7% | Multimodal-required |
| WebArena | OpAgent / DeepSeek v3.2 | 71.6-74% | DeepSeek v3.2 | Claude Mythos 68.7%; human 78% |
| SWE-Lancer | GPT-5.1 Codex | 0.663 | no entries | Only 4 models reported |
| AgentBench | (stale; ICLR'24) | — | — | Field moved on |
| AgentBoard | (stale; NeurIPS'24) | — | — | Useful progress-rate metric |

[UNVERIFIED] Berkeley RDI 2026 audit: 8 agent benchmarks (incl. WebArena, OSWorld, GAIA) gameable to near-perfect — treat aggregator scores with caution.

## Most-used in 2026 papers

τ-bench (retail + airline) and GAIA dominate citations for tool-using agents; SWE-bench dominates code; OSWorld dominates computer-use. AgentBench/AgentBoard are still cited but rarely as the primary number.

## Comparison table — runnability on our box

| Bench | Modality | Infra | $ / run | Local-LLM ok? | Days to first number |
|---|---|---|---|---|---|
| **τ-retail** | text + tools | pip only | $40-200 user-sim API | yes via vLLM | **1-2** |
| **GAIA L1 (val)** | text + web | Docker | tokens only | yes via vLLM | **2-3** |
| AgentBoard | text | conda+Docker | tokens only | yes | 2-3 |
| AgentBench | text | Docker per env | tokens only | yes | 3-5 |
| WebArena | text + browser | Docker × 4 sites, 1 TB | tokens only | yes | 5-7 |
| OSWorld | **vision** + GUI | KVM/AWS VMs | $60-1800 | **no** (text-only Qwen) | weeks |
| SWE-Lancer | text + repo | Docker (heavy) | high tokens | yes but slow | weeks |

## Recommendation

**Primary: τ-bench retail + airline.** Pure Python, no Docker, OpenAI-compatible client → drop in our vLLM endpoint. Run on `historical_trajectories` first for zero-cost regrade, then live run. Quote pass^1 + pass^4 (consistency is the headline metric).

**Secondary (stretch): GAIA Level 1 validation.** 53 questions; runs in inspect_ai; gives an "is it a real assistant" signal. Skip Levels 2-3 (too long for demo timeline).

Skip OSWorld (text-only Qwen blocks it), SWE-Lancer (Docker-heavy, no comparable open entries), WebArena (1 TB hosting + browser stack adds days). SWE-Bench Lite is the third number — see C2.

## Next steps

1. **Day 1**: pip install tau-bench; run retail w/ Claude-as-user-sim, gpt-4o-mini as user is cheaper; capture 11 task subset for smoke test (~$2).
2. **Day 2**: full retail (~115 tasks) pass^1 + pass^4 with Qwen 3.6-27B agent + cheap user sim. Budget ~$40-80.
3. **Day 3-4**: GAIA L1 val (53 q) via inspect_ai; add a `web_search` + `fetch` tool to our agent.
4. **Day 5**: deck table — τ-retail / τ-airline / GAIA-L1 / SWE-Bench-Lite (from C2).

## Open questions

- Which user-simulator model is cheap **and** strong enough to not bias τ-bench downward? (Claude Haiku vs gpt-4o-mini.)
- Do we report pass^1 only, or both pass^1 and pass^4 (consistency) for τ-bench?
- GAIA needs HF dataset access form — does tle@knox.edu already have it? [UNVERIFIED]
- Berkeley RDI gameability finding — does it materially affect τ-bench? (Their study covered other benches.) [UNVERIFIED]

## Sources

- https://github.com/sierra-research/tau-bench — τ-bench code
- https://github.com/sierra-research/tau2-bench — τ²-bench
- https://arxiv.org/pdf/2406.12045 — τ-bench paper (costs, pass^k)
- https://artificialanalysis.ai/evaluations/tau2-bench — τ²-bench leaderboard
- https://llm-stats.com/benchmarks/tau-bench — TAU leaderboard
- https://llm-stats.com/benchmarks/tau-bench-retail — TAU-retail leaderboard
- https://huggingface.co/spaces/gaia-benchmark/leaderboard — GAIA HF leaderboard
- https://ukgovernmentbeis.github.io/inspect_evals/evals/assistants/gaia/ — Inspect AI GAIA
- https://huggingface.co/learn/agents-course/unit4/what-is-gaia — GAIA intro
- https://os-world.github.io/ — OSWorld project
- https://github.com/xlang-ai/OSWorld — OSWorld code
- https://xlang.ai/blog/osworld-verified — OSWorld-Verified
- https://llm-stats.com/benchmarks/osworld-verified — OSWorld-Verified leaderboard
- https://github.com/web-arena-x/webarena — WebArena
- https://benchlm.ai/benchmarks/webArena — WebArena aggregator
- https://github.com/openai/SWELancer-Benchmark — SWE-Lancer
- https://openai.com/index/swe-lancer/ — SWE-Lancer blog
- https://llm-stats.com/benchmarks/swe-lancer — SWE-Lancer leaderboard
- https://github.com/THUDM/AgentBench — AgentBench
- https://arxiv.org/abs/2308.03688 — AgentBench paper
- https://github.com/hkust-nlp/AgentBoard — AgentBoard
- https://hkust-nlp.github.io/agentboard/ — AgentBoard site + leaderboard
- https://www.spheron.network/blog/ai-agent-benchmarking-gpu-cloud-swebench-gaia/ — infra cost guide
- https://www.marktechpost.com/2026/04/08/meet-osgym-a-new-os-infrastructure-framework-that-manages-1000-replicas-at-0-23-day-for-computer-use-agent-research/ — OSGym cost data
