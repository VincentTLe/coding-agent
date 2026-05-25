# Session Handoff — 2026-05-24 (CDT)

Tan Le, Math/Stat 361 Research (Knox College, advisor Prof. Andrew Leahy).
Last updated: 2026-05-24.

## Why this project exists

Started with `examples/01_chat.py` and grew incrementally into a
from-scratch ReAct coding agent. The May-20 checkpoint with Prof. Leahy
is behind us. Since then, three big things landed:

1. **Repo restructure** — the runnable entry points moved out of
   `examples/` into a new `cli/` package (`examples/06_chat.py` →
   `cli/chat.py`, `examples/05_agent_loop.py` → `cli/solve.py`).
   `examples/` is now a pure teaching ladder.
2. **Workspace refactor** — workspace is an explicit parameter
   everywhere; the old global `WORKSPACE`/`set_workspace` is gone.
   Importing `src.agent` is now side-effect-free.
3. **627-task eval harness** — the old "3 demo tasks" eval became a real
   benchmark suite with hidden-test scoring, a validation gate, a no-op
   guardrail, and parallel execution. Plus unit tests under `tests/`.

(10 tools + REPL context compaction were already done at the checkpoint.)

## TL;DR — what works right now

```bash
cd ~/code/coding-agent && source .venv/bin/activate

# Make sure vLLM is up (Qwen3-14B on GPU1, port 8765)
curl -sf http://localhost:8765/v1/models
# If not: tmux attach -t vllm  →  bash scripts/start_vllm.sh
# (Do NOT leave the server always-on — shared GPU. Ctrl-C when done.)

# Primary REPL (interactive chat + tools + /compact, /tokens)
python cli/chat.py                  # workspace defaults to demo_repo/
python cli/chat.py --workspace /tmp/playground

# One-shot task runner
python cli/solve.py "Fix all failing tests in demo_repo/"
# also: python -m src.agent "task" --workspace demo_repo

# Benchmark the agent (627 tasks; parallel)
python eval/run.py --jobs 8 --out eval/results/full_run.jsonl

# Unit tests (sandbox / tools / dispatcher) — run explicitly:
pytest tests/
```

End-to-end verified 2026-05-24: on `demo_repo/`, the agent ran
`run_bash(pytest)` → `read_file` → `apply_patch` → `run_bash(pytest)`
and reached **11/11 passing**.

## Model serving — current config

Single A6000 (**GPU1**), launched via `scripts/start_vllm.sh` inside a
`vllm` tmux session. **Do NOT keep the server always-on** — it is a
shared GPU; Ctrl-C the tmux pane when you're done.

- Model: `Qwen/Qwen3-14B` BF16 (~28 GB, 8 safetensors shards) at
  `~/models/Qwen3-14B`. Downloaded via `hf download` (the new
  HuggingFace CLI; `huggingface-cli` is deprecated).
- `CUDA_VISIBLE_DEVICES=1` → pinned to GPU1 only, GPU0 free for others.
- `--tensor-parallel-size 1`
- `--max-model-len 32768` (**32K**)
- `--gpu-memory-utilization 0.75`
- `--tool-call-parser hermes` (correct for Qwen3-14B; `qwen3_coder` is
  only for the Qwen3-Coder variants).
- `--reasoning-parser qwen3`
- `--enable-auto-tool-choice`
- `--port 8765`
- `VLLM_USE_FLASHINFER_SAMPLER=0` (nvcc still not installed
  system-wide; PyTorch-native sampler used instead).
- `.env` / `.env.example`: `VLLM_MODEL_NAME=Qwen/Qwen3-14B`.

The old Qwen3.6-27B model is still at `~/models/Qwen3.6-27B`. To switch
back: edit `scripts/start_vllm.sh` (path + `tool-call-parser qwen3_coder`
+ `tensor-parallel-size 2`) and update `.env`.

## Roadmap — long-term vision

The user's **self-evolving coding agent** roadmap: web-searches for
ideas, generates new tools into itself, fine-tunes itself on the lab
GPU. Plan written at:

> `/home/tle/.claude/plans/push-i-k-c-gleaming-crystal.md`

Phases:

- **Phase 1** (May 18-29) — basic agent. **DONE** (10 tools + compaction,
  end-to-end verified).
- **Phase 2** (Jun) — Reflexion loop + persistent `MEMORY.md`.
- **Phase 3** (Jul-Aug) — LoRA fine-tuning on collected agent traces
  with Unsloth + Qwen3-14B. DPO on pass/fail pairs. ~30 min per
  training run on 1× A6000.
- **Phase 4** (Aug+, exploratory) — agent generates new tools for
  itself, edits its own prompts, moves toward recursive
  self-improvement. 5-6 month research effort; out of scope for
  May 29.

User decision confirmed: the prof checkpoint covered **Phase 1 only**;
Phase 2-4 shown only as roadmap slides ("future work").

## Toolset — 10 tools (DONE)

All in `src/tools.py`: `TOOLS` dict + `TOOL_SCHEMAS` (10 entries) +
`_safe_path` sandbox. Heavy Vietnamese inline comments throughout.

| Category | Tools |
|---|---|
| File I/O | `read_file`, `write_file`, `apply_patch`, `multi_edit` |
| Discovery | `list_dir`, `glob_files`, `grep_files` |
| Execution | `run_bash`, `run_python` |
| Delegation | `spawn_subagent` (subprocess child agent, timeout 300s, max_iters 8) |

The 7 tools beyond the original 3 (`read_file`, `write_file`,
`run_bash`) are all shipped and used in live runs.

**Workspace is now a parameter, not a global** (the big refactor since
the checkpoint). `_safe_path(path, workspace)`,
`execute_tool(name, arguments, workspace)`, and every tool function take
`workspace` explicitly; the dispatcher injects it as a keyword arg
(`TOOLS[name](**args, workspace=workspace)`). `spawn_subagent` threads
its own workspace down to the child. There is **no** `set_workspace` and
**no** module-level `WORKSPACE` anymore — so `import src.agent` /
`import src.tools` is side-effect-free (no env read, no client built;
that's deferred to `get_client()` in `src/agent.py`).

## Context compaction — DONE (`cli/chat.py`)

The primary REPL auto-compacts conversation history so long sessions
don't blow the 32K window.

- `COMPACT_THRESHOLD_TOKENS = 24000`, `KEEP_RECENT_MESSAGES = 10`.
- Helpers: `estimate_tokens()`, `compact_messages()`.
- Slash commands: `/compact` (force), `/tokens` (alias `/tok`).
- Auto-triggers before the inner loop; wrapped in best-effort
  try/except so it never crashes the REPL.
- The split point must be a **user-role** message — this preserves
  `tool_call_id` pairing (a dangling tool result would be rejected by
  the API).

## Other Phase 1 code

| File | Purpose |
|---|---|
| `src/prompts.py` | `SYSTEM_PROMPT` with explicit JSON-escaping rules — Qwen3-14B was emitting `<tool_call>` blocks with Python triple-quotes; Hermes parser couldn't extract them. Adding "escape `\n` and `\"`, never triple-quote inside JSON" fixed it. |
| `src/agent.py` | `run_agent(goal, workspace, max_iters=15)` — ReAct loop; **workspace is a required param**. Returns `{"finish_reason", "iters_used"}` (`finish_reason ∈ {finished, max_iters, api_error, timeout, no_action}`). Lazy `get_client()` singleton → import is side-effect-free. **no_action guardrail**: if the model replies without a tool call, nudge up to `MAX_NUDGES = 2`, else return `no_action`. Uses `tool_choice="auto"` + `msg.model_dump(exclude_none=True)` to preserve `tool_calls` in history. ANSI-colored logs. Heavy VN comments. |
| `cli/chat.py` | **Primary REPL** (moved from `examples/06_chat.py`). Interactive chat + tools + context compaction + `/compact`, `/tokens`. Takes `--workspace` (default `demo_repo`). |
| `cli/solve.py` | One-shot task runner (moved from `examples/05_agent_loop.py`). Thin argparse wrapper around `run_agent`: positional `task`, optional `--max-iters`, `--workspace`. Kept out of `src/agent.py` so the loop stays importable without argparse/sys.exit. |
| `examples/01_chat.py` | Teaching ladder, step 1 (chat, no tools). `examples/` is now read-to-learn only; runnable entry points live in `cli/`. |
| `demo_repo/calculator.py` + `test_calculator.py` | Tiny demo with `add(a, b)` returning `a - b`. |
| `demo_repo/algorithms.py` + `test_algorithms.py` | Math demo with 2 bugs: `is_prime` uses `range(1, n)`, `factorial` uses `range(1, n)`. Plus a correct `fibonacci`. 11 tests, 5 fail until both bugs are fixed. |
| `README.md` | Quick-start, repo layout, Phase 1-4 roadmap. |
| `.vscode/settings.json` | Pin Python interpreter to project venv so VS Code's terminal stops auto-activating the wrong (`open_deep_research`) env. |

## End-to-end run — PASSED (2026-05-24)

On `demo_repo/`, the agent reached **11/11 passing** via:

```
run_bash("pytest")   → failures across calculator.py + algorithms.py
read_file(...)        → inspect the buggy sources
apply_patch(...)      → surgical fixes (no full-file overwrite)
run_bash("pytest")   → 11 passed
```

`apply_patch` makes the fix path cleaner than the old `write_file`
overwrite approach (which used to clobber docstrings and force a
self-correction loop).

## Eval harness — 627-task benchmark suite (BIG change since checkpoint)

The old "3 demo tasks" eval grew into a real benchmark. **627 tasks**:

```
eval/
├── README.md
├── run.py                 # discovers tasks, snapshots workspace, runs agent, scores
├── validate_tasks.py      # quality gate (ref passes / stub fails → else quarantine)
├── convert_benchmark.py   # regenerates bench/* from HumanEval+ & MBPP (no new deps)
├── LICENSES.md            # HumanEval MIT, MBPP CC-BY-4.0, EvalPlus Apache-2.0
├── solutions/             # reference solutions (NEVER shown to the agent)
├── results/              # <timestamp>.jsonl + <timestamp>.md (gitignored)
└── tasks/
    ├── bench/he_*         # 163  HumanEval+ (implement from spec, hardened tests)
    ├── bench/mbpp_*       # 424  MBPP-sanitized (NL spec)
    ├── curated/*          # 37   hard, tool-stressing: debugging, refactor, multi_file,
    │                      #      dp, graphs, data_structures, oop, parsing, algorithms, recursion
    ├── {01,02,03}_*       # 3    original demo tasks
    └── _quarantine/       #      tasks that failed validation (skipped by discovery)
```

Run:

```bash
python eval/run.py --jobs 8 --out eval/results/run.jsonl   # parallel, all tasks
python eval/run.py --filter difficulty=hard                # filter by metadata
python eval/run.py --filter bench/he_0 --repeats 3         # subset, pass@k
python eval/run.py --resume --out eval/results/run.jsonl   # continue an interrupted run
python eval/run.py 01_strings                              # one task (back-compat)
python eval/validate_tasks.py --jobs 16                    # prove every task is real (CPU-only)
```

`eval/run.py` flags: `--jobs N` (parallel via `ProcessPoolExecutor`,
spawn — each worker re-imports a clean OpenAI client), `--filter` (repeatable),
`--repeats K` (pass@k), `--resume`, `--agent-timeout`, `--temperature`,
`--out` (JSONL), `--min-pass-rate` (CI gate). Writes JSONL incrementally
+ a Markdown summary grouped by category & difficulty.

**Honest scoring:**
- Each task runs in its own snapshot; `pytest` re-runs after the agent
  exits and the score is the test outcome, never the agent's own claim
  (recursive snapshot/restore).
- **Hidden tests** (`## Tests: hidden`, all benchmark tasks): the test
  file is removed from the agent's workspace while it works and restored
  only for grading — it implements from the spec and can't read tests to
  hardcode outputs. Debug/refactor tasks keep tests **visible** (pytest
  is the feedback signal).
- **no_action guardrail** (in `src/agent.py`): the model can't "win" by
  describing code in prose — see the agent.py row above.
- **Validation gate** (`validate_tasks.py`): every task proven real
  (reference passes, stub fails) or quarantined to `tasks/_quarantine/`.

**Pass-rate: not recorded here.** The authoritative clean run lives at
`eval/results/<timestamp>.md` (headline + per-category/difficulty
breakdown). Don't quote a number from this doc.

## Unit tests — `tests/`

`pytest tests/` runs the unit suite (sandbox `_safe_path`, individual
tools, the `execute_tool` dispatcher). **Note:** `pyproject.toml`
deliberately has NO `[tool.pytest.ini_options]` — a repo-level pytest
config would hijack rootdir/collection and clash with the eval harness
(which runs pytest with `cwd=<task dir>` and no path args). So always run
the unit suite explicitly as `pytest tests/`, not bare `pytest`.

## Git history cleanup — Co-Authored-By line removed

User asked: "I don't want `Co-Authored-By: Claude Opus 4.7 ...` on my
public GitHub commits." I had been auto-adding the line per the system
prompt default.

Steps:
1. Saved a memory: `~/.claude/projects/-home-tle/memory/feedback_no_claude_coauthor.md`
   — never add the line in any future commit, across all sessions.
2. `git filter-branch --force --msg-filter 'grep -v "^Co-Authored-By: Claude" | grep -v "^🤖 Generated with"' d5d9b43..HEAD`
3. Deleted the filter-branch backup ref.
4. User force-pushed `main`.

Result: all 4 commits I had touched got new SHAs without the line.

**Open issue**: GitHub's contributor sidebar still shows "claude" because
of (a) GitHub's contributor-graph cache and (b) dangling commits in
GitHub storage (~90-day retention). Two fixes if it doesn't clear by
itself:

1. Hard-refresh + wait 24h.
2. Block the "claude" GitHub user from the repo settings.

## Environment cleanup

- `.vscode/settings.json`: pin Python interpreter to project venv so VS
  Code stops dragging in `open_deep_research`'s venv when opening
  terminals.
- `conda config --set auto_activate_base false` — new shells no longer
  auto-activate `(base)` on start.

## Repo history (checkpoint baseline, May-19)

This is the commit log as of the May-20 checkpoint. Since then: the
`cli/` restructure, the workspace-as-parameter refactor, the 627-task
eval harness + validation gate + guardrail, and `tests/` — run
`git log --oneline` for the current HEAD.

```
HEAD  Add eval framework: 3 task categories testing different agent capabilities
      slides: update slide 4 to match new multi-bug demo trace
      Phase 1 polish: VN comments + colored output + multi-bug demo task
      Phase 1 working agent: ReAct loop + 3 tools + demo task
      Add 01_chat.py + start_vllm.sh; switch default model to Qwen3-14B
      Add 30-topic research survey + 111 cached references
      Verify and fix three flagged claims in knowledge base
      Add knowledge base + cached reference docs
      Refine Rule A/B triggers: replace 'non-trivial' with concrete criteria
      Initial scaffold: structure, AGENTS.md, README, pyproject
```

All commits authored by `lethongtan4@gmail.com`. No `Co-Authored-By:
Claude` lines anywhere.

## What's done / what's next

Done since the May-20 checkpoint:

- [x] **10 tools** in `src/tools.py` (file I/O, discovery, execution,
      delegation) with `TOOL_SCHEMAS` + `_safe_path` sandbox.
- [x] **Context compaction** in `cli/chat.py` (auto-trigger +
      `/compact`, `/tokens`).
- [x] **Workspace refactor** — explicit param everywhere, no global /
      `set_workspace`, side-effect-free imports, lazy `get_client()`.
- [x] **`cli/` restructure** — `chat.py` + `solve.py` moved out of
      `examples/`; `examples/` is now the teaching ladder only.
- [x] **627-task eval harness** — parallel `run.py`, hidden-test scoring,
      `no_action` guardrail, `validate_tasks.py` gate, `convert_benchmark.py`.
- [x] **Unit tests** under `tests/` (`pytest tests/`).
- [x] vLLM config settled at **32K / 0.75 util** on GPU1.
- [x] End-to-end demo re-verified (`apply_patch` path, 11/11 passing).

Next / open:

- [ ] **Authoritative eval run**: do a clean full `eval/run.py` and drop
      the headline into `eval/results/<timestamp>.md` (+ eval/README
      Results placeholder). Docs intentionally quote no pass-rate yet.
- [ ] **Stray file**: `demo_repo/fibonacci.py` is untracked, a duplicate
      standalone fibonacci not imported by any test — leftover. NOT part
      of the demo; clean it up (or just ignore it).
- [ ] **Phase 2** (Jun): Reflexion loop + persistent `MEMORY.md`.
- [ ] (Background) GitHub contributor list — should self-clear.

## How to resume / where things live

| Where | What |
|---|---|
| `~/code/coding-agent/` | The whole project |
| `cli/chat.py` | **Primary REPL** (chat + tools + compaction); `--workspace` |
| `cli/solve.py` | One-shot task runner (`--workspace`, `--max-iters`) |
| `examples/` | Teaching ladder (read-to-learn, e.g. `01_chat.py`) |
| `eval/run.py` | 627-task benchmark runner (`--jobs`, `--filter`, `--resume`, ...) |
| `eval/validate_tasks.py` | Task quality gate (ref passes / stub fails) |
| `tests/` | Unit suite — run as `pytest tests/` |
| `src/agent.py` | ReAct loop `run_agent(goal, workspace, ...)`; `get_client()` |
| `src/tools.py` | 10 tools + `TOOL_SCHEMAS` + `_safe_path(path, workspace)` sandbox |
| `~/code/coding-agent/.env` | `VLLM_BASE_URL`, `VLLM_MODEL_NAME=Qwen/Qwen3-14B`, `VLLM_API_KEY=not-needed`, `LOG_LEVEL=INFO` |
| `~/code/coding-agent/scripts/start_vllm.sh` | The vLLM launch script |
| `~/code/coding-agent/AGENTS.md` | Project rules (A: verify, B: cache docs, C: verbose agent) |
| `~/AGENTS.md` | Global rules |
| `README.md` | Quick-start + repo layout + roadmap |
| `SYSTEM_DEEP_DIVE.md` / `.html` | Very detailed system walkthrough (md + interactive web) |
| `PRESENTATION.html` | reveal.js slide deck for presenting |
| `eval/README.md` | Eval framework docs |
| `~/code/coding-agent/docs/knowledge/` + `docs/reference/` | Research notes / cached official docs (Rule B) |
| `~/.claude/plans/push-i-k-c-gleaming-crystal.md` | Full Phase 1-4 plan |
| `~/.claude/projects/-home-tle/memory/` | Auto-memory (no-Claude-coauthor pref saved here) |
| `~/models/Qwen3-14B/` | Current model weights (28 GB) |
| `~/models/Qwen3.6-27B/` | Old model weights (52 GB), kept in case we switch back |
| tmux session `vllm` | The vLLM server (`tmux attach -t vllm`); not always-on |

## Notes for future sessions

- **Never** add `Co-Authored-By: Claude` or `🤖 Generated with [Claude
  Code]` lines to commits or PRs. Memory saved; applies cross-session.
- Vietnamese inline comments in the user's code are intentional teaching
  notes; English docstrings stay per AGENTS.md. Don't strip them.
- The user has unlimited lab GPU access. Phase 3 fine-tuning (LoRA on
  agent traces) is in the plan for Jul-Aug.
- Note: this is about the *Claude Code harness*, not the project's own
  delegation. The project's `spawn_subagent` tool runs a child agent as a
  **subprocess** (timeout 300s, max_iters 8) and works fine. Separately,
  the Claude Code harness's `Agent` tool fails here ("Cannot create agent
  worktree: not in a git repository") because the parent CWD isn't a git
  repo — workaround there is direct parallel Write/Edit calls.
- The user prefers high-leverage patterns (parallel agents, schedules,
  skills, hooks) but those aren't always available; degrade gracefully.

## Demo runbook

| Step | Command | What it shows |
|---|---|---|
| Start server | `tmux attach -t vllm` → `bash scripts/start_vllm.sh` | Qwen3-14B on GPU1, 32K window |
| Interactive | `python cli/chat.py` | Chat + tools + `/compact`, `/tokens` |
| One-shot fix | `python cli/solve.py "Fix all failing tests in demo_repo/"` | Colored ReAct trace, `apply_patch`, 11/11 pass |
| Benchmark | `python eval/run.py --jobs 8` | 627-task pass/fail summary by category/difficulty |
| Slides | open `PRESENTATION.html` | reveal.js deck |

Reset `demo_repo/` between runs:

```bash
git checkout demo_repo/         # restore the buggy versions
# (note: demo_repo/fibonacci.py is an untracked stray — not part of demo)
```
