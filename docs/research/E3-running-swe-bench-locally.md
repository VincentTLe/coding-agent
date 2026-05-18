# E3 — Running SWE-Bench locally on 2× A6000, May 2026

## TL;DR

Harness = **Docker + CPU + disk**, not GPU. 100-instance Verified subset = **15–30 min** harness wall-clock on our box. Real cost = GPU-hours generating patches with Qwen 3.6-27B. For May 29: **run a 100-instance Verified subset locally**; skip full Verified.

## Why

Demo needs a defensible, reproducible number; C2's self-reported scaffold numbers aren't ours.

## SOTA harness

`SWE-bench/SWE-bench` (was `princeton-nlp/`). `pip install -e .`, Docker since June 2024. Subsets: Lite (300), **Verified (500)**, Full (2294), + Multimodal/Multilingual/SMITH/REBENCH. Predictions: JSONL `{instance_id, model_name_or_path, model_patch}` (unified-diff). Eval = CPU+Docker per instance; **no GPU for harness**. Floor: x86_64, ≥120 GB disk, ≥16 GB RAM, ≥8 CPU — our box clears easily.

## Most-used

**Epoch AI optimized images** (`ghcr.io/epoch-ai/swebench-images`): 30 GB / 500 Verified vs 189 GB vanilla; full Verified in **62–73 min** on 32-CPU/128-GB. **mini-SWE-agent** (100 LOC, >74% Verified): `mini-extra swebench --subset verified --slice :100` emits `preds.json`. **sb-cli**: cloud eval ~20 min, cross-check only.

## Known gotchas

Docker Hub pull limits → Epoch images or `--namespace ''`. `--cache_level=instance` ~2 TB, `env` ~100 GB, `base` smallest/slowest. `PIP_NO_CACHE_DIR=1` breaks legacy-pip envs → set `=0`. Stuck evals = too many workers / disk full; use `--max_workers min(0.75·cpu_count, 24)`. [UNVERIFIED] **SWE-bench Pro** (Scale, 1865 multi-lang) contamination-resistant; top 46% vs 81% Verified — too heavy for student demo.

## Comparison

| | Lite | **Verified** | Full | Pro |
|---|---|---|---|---|
| Instances | 300 | **500** | 2294 | 731 |
| Curated | No | **Yes (OpenAI)** | No | Yes (Scale) |
| Disk opt. | ~20 GB? | **~30 GB** | ~67 GB | n/a |
| Harness (32 CPU) | <40 min? | **~1 h** | ~4–5 h? | unk |
| Canonical | Legacy | **Yes** | Rare | Emerging |
| Contamination | Med | Med-High | High | Low |
| Languages | Py | Py | Py | Multi |

`?` = [UNVERIFIED].

## Recommendation — May 29 demo

**Run a 100-instance Verified subset locally; skip full Verified and Pro.** Freeze `verified-100` instance_ids; reuse across runs. Generate patches via Qwen 3.6-27B + our agent on 2× A6000 (~3–10 min/instance ⇒ 5–17 GPU-h/pass, ~3–9 wall-clock h). Emit `preds.jsonl`, run `python -m swebench.harness.run_evaluation --dataset_name princeton-nlp/SWE-bench_Verified --predictions_path preds.jsonl --max_workers 8 --cache_level env --clean True` → **15–30 min**. Re-run ≥3 times; ~11 days fits.

Full Verified <1 week? Harness yes (1 h); inference no — 5 min × 500 / 2 GPUs ≈ 21 GPU-h × multiple debug passes blows budget. 100-instance cost: harness ~$0, disk ~30–60 GB, own-GPU inference 3–9 h. API-equivalent: **$20–50/pass** [UNVERIFIED, extrapolated from SWE-agent+GPT-4 $0.24/instance].

## Next steps

Today: clone, install, smoke-test `--predictions_path gold --instance_ids <one>`. This week: freeze `verified-100`, pull Epoch images, dry-run `gold` on all 100. Next week: agent→JSONL converter, first scored pass. Pre-demo: same-IDs mini-SWE-agent + Qwen baseline.

## Open questions

`verified-100` = first-100, random, or stratified by repo? Public swebench.com submission (needs trajectories) or internal-only? Lite calibration before Verified-100? [UNVERIFIED] Is Epoch's ghcr.io registry still rate-limit-free?

## Sources

github.com/SWE-bench/SWE-bench; swebench.com/SWE-bench/{guides/evaluation,guides/docker_setup,faq}; epoch.ai/blog/swebench-docker; mini-swe-agent.com/latest/usage/swebench; github.com/SWE-agent/{mini-swe-agent,SWE-agent/issues/1260}; labs.scale.com/leaderboard/swe_bench_pro_public; morphllm.com/swe-bench-pro [UNVERIFIED].
