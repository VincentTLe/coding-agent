# Eval set

A small benchmark of coding tasks the agent should handle end-to-end.
Each subdirectory under `tasks/` is one scenario with its own `task.md`,
source files, and pytest suite.

## Tasks today (3 categories — different capabilities tested)

| ID | Task | Capability tested |
|----|------|-------------------|
| `01_strings` | Fix 2 bugs in string utility functions | Multi-bug debug |
| `02_implement` | Implement 4 stub functions from docstrings | Code generation |
| `03_add_feature` | Add `gcd` + `lcm` functions + tests | Multi-step planning + multi-file write |

## How to run

```bash
cd ~/code/coding-agent && source .venv/bin/activate

# Run agent against ALL tasks and print pass/fail summary
python eval/run.py

# Run a single task
python eval/run.py 01_strings
```

The runner (`eval/run.py`) does, for each task directory:
1. Loads `task.md` for the goal.
2. Pins the agent's workspace to the task directory.
3. Snapshots the task's source files (so the run is repeatable).
4. Runs the agent (`max_iters = 20`).
5. Runs `pytest --tb=short` in the task directory to score.
6. Restores the snapshot so the fixtures are clean for the next run.
7. Prints a summary table.

**Pass/fail:** a task **passes** only if `pytest` exits 0 (all tests green) after
the agent finishes; otherwise it **fails**. The agent never sees the tests — it
works only from `task.md` and the source. Hitting `max_iters` without a green
suite counts as a fail.

## Adding a new task

```
eval/tasks/04_<name>/
├── source.py        # broken/stub code
├── test_source.py   # pytest suite
└── task.md          # goal + setup + capability description
```

That's it — `run.py` discovers new subdirs automatically.

## Caveats

- These tasks are toy-scale (~10-30 lines each). The bar is "an open-weight
  model (Qwen3-14B) with simple tools can handle these"; not SOTA SWE-Bench
  performance.
- Some tasks may flake — open-weight models are stochastic. Re-run a
  few times for an honest pass rate.
- `max_iters` is set to 20 in `run.py`; tasks needing more turns
  count as fails.
- The benchmark needs the vLLM server up (see `scripts/start_vllm.sh`); it is
  not kept always-on, so start it before running.
