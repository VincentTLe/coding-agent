# Cache: mini-SWE-agent SWE-bench runner

Source: https://mini-swe-agent.com/latest/usage/swebench/
Fetched: 2026-05-18

## What it is

Princeton's 100-LOC bash-only agent. Wraps inference + harness eval. Useful as a same-machine baseline alongside our own scaffold.

## Run

```bash
mini-extra swebench \
  --model anthropic/claude-sonnet-4-5-20250929 \
  --subset verified \
  --split test \
  --workers 4
```

## `--subset` values

`lite` (default, 300) · `verified` (500) · `full` (2294) · `multimodal` · `multilingual` · `smith` · `rebench` · or a custom HF/local path.

## Subsetting

`--slice` uses Python slice syntax against the dataset.

- `--slice :100` — first 100 instances (handy for the "sample-of-N subset" we want).
- `--slice 10:20` — items 10–19.
- `--slice -10:` — last 10.

For a *random* 100-instance subset, add `--shuffle=True` (or pre-pick instance_ids and pass them to the harness via `--instance_ids`).

## Output

Writes `preds.json` with `{instance_id: {model_name_or_path, instance_id, model_patch}}`.

## Eval the predictions

Cloud (sb-cli, ~20 min, no local Docker):

```bash
sb-cli submit swe-bench_verified test \
  --predictions_path preds.json --run_id my-run-01
```

Local (our case, no internet sends):

```bash
python -m swebench.harness.run_evaluation \
  --dataset_name princeton-nlp/SWE-bench_Verified \
  --predictions_path preds.jsonl \
  --max_workers 8 --run_id my-run-01
```

mini-swe-agent's headline open-agent number: **>74% on Verified** with a strong backing model.
