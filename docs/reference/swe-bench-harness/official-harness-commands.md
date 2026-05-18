# Cache: Official SWE-bench harness commands

Sources:
- https://github.com/SWE-bench/SWE-bench (repo, renamed from princeton-nlp/SWE-bench)
- https://www.swebench.com/SWE-bench/guides/evaluation/
- https://www.swebench.com/SWE-bench/guides/docker_setup/
- https://www.swebench.com/SWE-bench/faq/
Fetched: 2026-05-18

## Install

```bash
git clone https://github.com/SWE-bench/SWE-bench
cd SWE-bench
pip install -e .
```

Docker must be running. Linux: do the docker-group post-install step.

## Run evaluation (Verified, full)

```bash
python -m swebench.harness.run_evaluation \
  --dataset_name princeton-nlp/SWE-bench_Verified \
  --predictions_path preds.jsonl \
  --max_workers 8 \
  --run_id my-run-01
```

Lite uses `princeton-nlp/SWE-bench_Lite`. Full uses `princeton-nlp/SWE-bench`.

## Prediction format

JSONL, one row per instance, three required fields:

```json
{"instance_id": "...", "model_name_or_path": "qwen3.6-27b", "model_patch": "diff --git a/..."}
```

## Useful flags

- `--instance_ids id1 id2 ...` — run a subset only.
- `--max_workers N` — official advice: `min(0.75 * cpu_count(), 24)`. Start at 8.
- `--cache_level {none,base,env,instance}` — disk/time tradeoff.
  - `instance`: ~2 TB, fastest re-runs.
  - `env`: ~100 GB, default-ish.
  - `base`: smallest, slowest.
- `--clean True` — remove instance images after use (smaller disk, slower).
- `--namespace ''` — build images locally instead of pulling from DockerHub (needed for ARM/M-series; useful to avoid pull rate limits).

## Resource floor (official)

- x86_64.
- ≥ 16 GB RAM, ≥ 8 CPU cores.
- ≥ 120 GB free disk (baseline; way more for `cache_level=instance`).

## Sanity check

Run with `--predictions_path gold` to feed the gold patches as predictions — should resolve 100% of instances. If not, environment is broken.
