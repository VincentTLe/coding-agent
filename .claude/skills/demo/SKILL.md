---
name: demo
description: Run the canonical coding-agent demo end-to-end — the agent fixes the failing tests in demo_repo/ by reading failures, patching source, and re-running pytest until green. Use when the user wants to show off or sanity-check the agent on its reference scenario.
disable-model-invocation: true
---

# Run the canonical demo (agent fixes failing tests in demo_repo/)

This runs the reference scenario from the README/HANDOFF: the from-scratch ReAct
agent is given a buggy `demo_repo/`, and it loops `run_bash(pytest)` → `read_file`
→ `apply_patch` → `run_bash(pytest)` until the suite is green — fixing only the
source, never the tests. The known-good outcome is **11/11 tests passing**.

Run the steps in order. Do not skip the pre-checks.

## Step 1 — Pre-check: is the vLLM server up?

The agent cannot run without the model server. Verify the endpoint first:

```bash
curl -sf http://localhost:8765/v1/models
```

- If this returns JSON listing `Qwen/Qwen3-14B`, continue to Step 2.
- If it fails (connection refused), STOP and tell the user to start the server
  first with the **`/start-vllm`** skill (or `bash scripts/start_vllm.sh`). Do not
  try to run the demo against a dead endpoint — it will just error.

## Step 2 — Reset demo_repo to its buggy starting state

The demo only works if `demo_repo/` starts buggy. If a previous run already fixed
it, the agent has nothing to do. Restore the tracked buggy versions:

```bash
git checkout -- demo_repo/
```

(Note: `demo_repo/fibonacci.py` is a known untracked stray and is not part of the
demo — leave it alone. Do not `git clean`.)

Optionally confirm the suite starts red (5 of 11 tests fail until the two bugs in
`algorithms.py` — `is_prime` and `factorial` both using `range(1, n)` — are fixed):

```bash
.venv/bin/python -m pytest demo_repo/ -q
```

## Step 3 — Run the agent one-shot on the demo task

This is the canonical demo command (verified entrypoint — `cli/solve.py` is a thin
argparse wrapper around `run_agent`, workspace defaults to `demo_repo/`):

```bash
.venv/bin/python cli/solve.py "Fix all failing tests in demo_repo/"
```

Let it run to completion. You will see a verbose, colored ReAct trace: each model
turn, every tool call (`run_bash`, `read_file`, `apply_patch`, …) and its result.
That verbosity is intentional (project Rule C) — it is how the run is observed and
explained. The one-shot runner defaults to `--max-iters 15`.

Equivalent invocation if needed: `.venv/bin/python -m src.agent "Fix all failing tests in demo_repo/" --workspace demo_repo`.

## Step 4 — Verify the suite is green

Confirm the agent actually fixed it (don't trust the trace alone — re-run the
tests independently):

```bash
.venv/bin/python -m pytest demo_repo/ -q
```

Report the result to the user. Success = **11 passed** (the agent edited only
`demo_repo/algorithms.py`, never the test files).

## Notes

- To reset again for a repeat run: `git checkout -- demo_repo/`.
- For an interactive variant instead of one-shot: `.venv/bin/python cli/chat.py`
  (streaming REPL with `/think`, `/compact`, `/tokens`).
- If the agent stalls or replies without acting, that is the project's documented
  `no_action` behavior — re-running usually succeeds (the 14B model is stochastic).
