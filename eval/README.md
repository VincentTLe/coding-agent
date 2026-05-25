# Eval suite

An end-to-end benchmark for the coding agent: **627 programming tasks** spanning easy →
hard. For each task the agent gets a goal, works in a sandboxed copy of the task directory
with its tools, and is scored by an **independent `pytest` run it does not control**.

## What's in the suite

| Namespace | Count | Source | What it tests |
|---|---|---|---|
| `tasks/bench/he_*` | 163 | HumanEval+ (EvalPlus) | function implementation from a docstring spec, hardened tests |
| `tasks/bench/mbpp_*` | 424 | MBPP (sanitized) | short programming problems from a natural-language spec |
| `tasks/curated/*` | 37 | hand-authored | harder, tool-stressing: debugging, refactor, multi-file, DP, graphs, data structures, OOP, parsing, algorithms, recursion |
| `tasks/{01,02,03}_*` | 3 | original demo tasks | multi-bug debug, implement-from-stub, add-feature |

Every task carries `## Category`, `## Difficulty` (easy/medium/hard), and `## Tests`
(visible/hidden) metadata in its `task.md`, so results can be broken down by group.
See `LICENSES.md` for source attribution (HumanEval = MIT, MBPP = CC-BY-4.0, EvalPlus = Apache-2.0).

## How to run

```bash
cd ~/code/coding-agent && source .venv/bin/activate   # needs the vLLM server up

python eval/run.py                                     # all tasks, 1 at a time
python eval/run.py --jobs 8                             # 8 agents in parallel
python eval/run.py --filter bench/he_0 --jobs 4         # only matching tasks
python eval/run.py --filter difficulty=hard             # filter by metadata
python eval/run.py --resume --out eval/results/run.jsonl  # continue an interrupted run
python eval/run.py 01_strings                           # a single task (back-compat)
```

Flags: `--jobs N` (parallel workers), `--max-iters N` (turn cap, default 20),
`--filter EXPR` (repeatable; `key=value` on category/difficulty/task, or a glob/substring on
the task id), `--repeats K` (run each task K times for pass@k), `--agent-timeout S` (per-task
wall-clock cap), `--out PATH` (JSONL results), `--min-pass-rate X` (optional CI gate).

Results are written **incrementally** to `eval/results/<timestamp>.jsonl` (so `--resume` is
lossless) plus a Markdown summary `eval/results/<timestamp>.md` broken down by category and
difficulty. (`eval/results/` is gitignored.)

### Why it's parallel by *process*, not thread
Each task runs in its own process (`ProcessPoolExecutor`, spawn). The workspace is now an explicit
parameter (`run_agent(goal, workspace, ...)`, `execute_tool(name, args, workspace)`), so tasks don't
collide on shared state — but spawned processes still buy us a clean per-worker OpenAI client (no
forked sockets) and fault isolation (one task crashing can't take down the pool). vLLM's continuous
batching lets the concurrent agents share the GPU(s) efficiently.

## Scoring & honest evaluation

- A task **passes** iff `pytest` exits 0 after the agent finishes. Hitting `max_iters` /
  timeout / a crash counts as a fail. Each result records `finish_reason`, `iters_used`,
  `duration_s`, and a `pytest_tail` for debugging.
- **Hidden vs. visible tests** (`## Tests` in `task.md`):
  - `hidden` (all benchmark tasks): the test file is **removed from the agent's workspace
    while it works** and restored only for scoring. The agent implements from the `task.md`
    spec (and docstring examples) and *cannot read the tests to hard-code outputs*. This keeps
    the capability number honest.
  - `visible` (debug / refactor / multi-file tasks): the agent **sees and runs** the tests —
    that's the whole point (use `pytest` as a feedback signal, fix until green). This is the
    "verify your own work" loop the agent is built around.

## Quality gate — every task is provably real

`eval/validate_tasks.py` checks each task before it counts: the **reference solution**
(`eval/solutions/<task>/`, kept outside any agent workspace) must make `pytest` **pass**, and
the **stub** must make it **fail**. Tasks that fail either check are quarantined
(`tasks/_quarantine/`, skipped by discovery).

```bash
python eval/validate_tasks.py --jobs 16                 # validate everything (CPU-only)
python eval/validate_tasks.py --filter curated --quarantine
```

## Regenerating the benchmark tasks

The 587 benchmark task dirs are produced by a converter (no extra dependencies — it uses the
already-installed `huggingface_hub` + `requests`):

```bash
python eval/convert_benchmark.py            # downloads HumanEval+ & MBPP, writes tasks/bench/
python eval/validate_tasks.py --filter bench --jobs 16 --quarantine
```

## Adding your own task

```
eval/tasks/curated/<name>/
├── <module>.py        # stub (or buggy code, for a debugging task)
├── test_<module>.py   # pytest; import the module BY BARE NAME (cwd = task dir, no conftest)
└── task.md            # ## Goal, ## Category, ## Difficulty, ## Tests, ## Source/License
eval/solutions/curated/<name>/<module>.py   # reference solution (mirrors the task; never shown to the agent)
```

`run.py` discovers any directory containing a `task.md` automatically.

## Results

Latest full run — all 627 tasks, full agent loop, Qwen3-14B at temperature 0.6:
**501 / 627 = 79.9% pass.** A clean easy→hard gradient — **easy 93% · medium 83% · hard 63%** — which
is what a real (non-memorized) benchmark looks like. By source: MBPP 85%, HumanEval+ 78%, the
hand-authored hard tier 27%.

Notable finding from the traces: when the agent **actually engages a tool** it's **92% correct**
(501/543). Most remaining failures are the model replying in prose without acting (`no_action`, 84) or
hitting the per-task time cap (`timeout`, 25) — the guardrail mitigates the former. Per-task results +
the full per-category/difficulty breakdown are written to `eval/results/` (timestamped JSONL + Markdown).

## Caveats (read these before quoting a number)

- **HumanEval/MBPP are well-known and partially saturated/contaminated** for modern models.
  Treat the benchmark tier as a breadth + harness sanity signal, not a frontier result; the
  `curated/` hard tier is the more honest stress test.
- Open-weight models are **stochastic** — use `--repeats K` and report pass@1 vs pass@k.
- `--max-iters` bounds turns; genuinely hard tasks that need more count as fails.
- Generated solutions run with `pytest` **on the host** (no container). Tasks here are benign;
  do not point this harness at untrusted task code without isolation.
- Needs the vLLM server (`scripts/start_vllm.sh`), which is **not** kept always-on — start it
  before a run and stop it (Ctrl-C in the tmux pane) afterward; it's a shared GPU.
