# Project Dossier — A Local ReAct Coding Agent with Hidden-Test Evaluation

> **Purpose of this file.** This is a complete, self-contained description of the project, written so
> that a language model (or a reader) with no access to the repository can understand every part of it
> and write or repair the paper. It restates only facts that are verified in the code, the eval result
> files, and the slide decks. Every number here is sourced. Do not invent numbers; if something is not
> here, mark it as unknown rather than guessing.
>
> **Author / context.** Vincent Le, Math/Stat 361 Research, Knox College. Advisor: Prof. Andrew Leahy.
> Final demo: 2026-05-29. The paper is `docs/paper/paper.tex` (compiles to `paper.pdf`).
> The honest headline number is **67.3%**.

---

## 0. One-paragraph summary

I built a coding agent from scratch around a local Qwen3-14B model served by vLLM, with no agent
framework: only the OpenAI Python SDK, vLLM, and `python-dotenv`. The agent runs a standard ReAct loop
(reason, act with a tool, observe the result, repeat) and has eleven tools for file I/O, search, shell
and Python execution, subagent delegation, and explicit completion. Every file path is confined to a
workspace by one function, `_safe_path`. I evaluated it on 627 coding tasks with hidden tests. While
hardening the project I found a leak I had built into my own MBPP conversion script: for about 93% of
the 424 MBPP tasks, 2 of the 3 graded asserts had been copied into the prompt the agent could read. That
leak had inflated an earlier score of 79.9%. After regenerating those tasks as spec-only prompts, the
honest score was 67.3% (422/627, 95% Wilson CI 64–71%). I also reproduced the SkillOpt method (Yang et
al., 2026) on my own agent: it optimizes a natural-language skill document while the model weights stay
frozen. On an 84-task held-out split the empty, seed, and optimized skills scored 0.786, 0.738, and
0.774; no paired McNemar test was significant, and re-running the empty arm alone flipped about 6 of 84
tasks, so I report that experiment as inconclusive and under-powered. The project's claim is not that it
beats Claude or Codex. The claim is that it is small, transparent, and honestly measured.

---

## 1. Motivation and goal

The owner's prior pain point was AI-generated codebases that he could not explain. The whole point of
this project was the opposite: a coding agent where every line of source is understandable and
defensible at the source-code level. That is why there is no agent framework. A framework would have
been faster and would have handled some edge cases better, but it would also have hidden the agent
behind abstractions, which is exactly the failure mode the project exists to avoid.

So the target was modest and concrete: take a natural-language task, operate on a local repository, edit
files, run code, and stop when the task is done. The research questions are narrow:

1. How far does a small, local, from-scratch ReAct implementation get on real coding tasks?
2. What breaks when you evaluate such an agent carefully?
3. Can a frozen model be improved by optimizing a natural-language skill document instead of weights?

The answers, in short: (1) 67.3% on a 627-task hidden-test benchmark; (2) the evaluation itself is the
easiest thing to get wrong — I leaked test asserts into my own prompts and had to catch it; (3) on my
small setup the skill-optimization result was inconclusive.

---

## 2. Related work (with relevance and arXiv ids)

- **ReAct** (Yao et al., 2023; arXiv 2210.03629). The agent loop is ReAct: the model alternates between
  reasoning in text and acting through tools. This is the structural backbone, reused, not invented.
- **Reflexion** (Shinn et al., 2023; arXiv 2303.11366). Verbal self-feedback and retry. Related to the
  agent's run-fix-rerun behavior and to the `no_action` guardrail idea.
- **Toolformer** (Schick et al., 2023; arXiv 2302.04761). Models learning to call tools. Background for
  tool-calling agents.
- **Voyager** (Wang et al., 2023; arXiv 2305.16291). Stores and reuses skills (as executable code) in an
  agent. Closest prior idea to the SkillOpt skill document.
- **OPRO** (Yang et al., 2023; arXiv 2309.03409), **TextGrad** (Yuksekgonul et al., 2024; arXiv
  2406.07496), **GEPA** (Agrawal et al., 2025; arXiv 2507.19457). Optimizing text/prompts instead of
  weights. The family the SkillOpt method belongs to.
- **SkillOpt** (Yang et al., 2026; arXiv 2605.23904; a Microsoft / Shanghai Jiao Tong / Tongji / Fudan
  collaboration; code github.com/microsoft/SkillOpt, MIT).
  The exact method my skill-optimization experiment reproduces: a controllable text-space optimizer that
  turns scored rollouts into bounded add/delete/replace edits on a single skill document, accepting an
  edit only when it strictly improves a held-out validation score. My `skillopt/` code is a faithful
  port of its core (skill doc + edit ops + protected slow-update region, contrastive reflect,
  failure-first merge, clip-to-budget textual learning rate, strict-`>` validation gate, rejected-edit
  buffer, epoch slow-update). Deferred (decorative per the paper's own ablations): optimizer meta-skill,
  parallel hierarchical merge, autonomous learning rate, cosine schedule, rewrite mode.
- **Benchmarks.** HumanEval / Codex (Chen et al., 2021; arXiv 2107.03374), MBPP (Austin et al., 2021;
  arXiv 2108.07732), EvalPlus / HumanEval+ (Liu et al., 2023; arXiv 2305.01210). LiveCodeBench (Jain et
  al., 2024; arXiv 2403.07974) is the reference for contamination-free code evaluation, relevant to the
  leak section.
- **Serving and model.** vLLM / PagedAttention (Kwon et al., 2023; arXiv 2309.06180); Qwen3 technical
  report (Qwen Team, 2025; arXiv 2505.09388).
- **Statistics.** McNemar's paired test (McNemar, 1947, *Psychometrika*); Wilson score interval (Wilson,
  1927, *JASA*).

---

## 3. System design

### 3.1 Stack and dependencies
- **Model:** Qwen3-14B (BF16), served locally by **vLLM** on a single GPU (GPU1), OpenAI-compatible
  endpoint at `http://localhost:8765/v1`.
- **vLLM flags** (`scripts/start_vllm.sh`): `--served-model-name Qwen/Qwen3-14B`,
  `--tensor-parallel-size 1`, `--max-model-len 32768` (32K context), `--gpu-memory-utilization 0.75`,
  `--reasoning-parser qwen3` (emits `<think>…</think>`), `--enable-auto-tool-choice`,
  `--tool-call-parser hermes`, `--port 8765`. Launched in a tmux session; not kept always-on.
- **Client:** OpenAI Python SDK. Runtime deps are only `openai`, `python-dotenv` (and `httpx`); eval
  adds `requests` and `huggingface_hub`. No agent framework.
- **Config:** `models.json` (base_url, model `Qwen/Qwen3-14B`, max_tokens 2048, temperature 0.0,
  context_window 32768), with `.env` fallback (`VLLM_BASE_URL`, `VLLM_MODEL_NAME`).
- **Code size (core):** `src/agent.py` ~963 lines (the loop), `src/tools.py` ~1276 lines (11 tools +
  sandbox + dispatcher), `src/prompts.py` ~139 lines (system prompt + skill injection), `cli/solve.py`
  ~352 lines (one-shot runner), `cli/chat.py` ~1283 lines (streaming REPL + context compaction).

### 3.2 The ReAct loop: `run_agent(goal, workspace, max_iters=15)`
Lives in `src/agent.py`. Each iteration:
1. **Reason.** Send the current message history plus `TOOL_SCHEMAS` to the local endpoint:
   `chat.completions.create(model, messages, tools=TOOL_SCHEMAS, tool_choice="auto", max_tokens=2048,
   temperature=0.0)` (eval uses greedy decoding for reproducibility).
2. **Act.** If the model returns `tool_calls`, execute each one. If it returns plain text with no tool
   call, the task is not considered done (see `finish` and `no_action` below).
3. **Observe.** Append the result of each tool call to the history as a `role="tool"` message, then loop.

Termination: the loop is capped at **15 iterations**. The agent ends by calling the `finish` tool
(`finish_reason="finished"`), by exhausting iterations (`max_iters`), by replying in prose without ever
acting (`no_action`), or by a caught API problem (`api_error`) or time budget (`timeout`).

Load-bearing implementation details (these are the paper's "the loop is easy, the details are not"
lesson):
- **Store the assistant tool-call message verbatim.** When the model returns an assistant message with
  `tool_calls`, that exact message must go into the history. If it does not, the next request references
  tool calls that no longer exist and the API rejects it with a 400.
- **Explicit timeouts.** The client uses a 120-second timeout and one retry, instead of the SDK's much
  longer default, because a local model on a shared GPU can stall and hang a whole turn. One retry
  tolerates a transient failure without hiding repeated ones.
- **`finish` is a tool, not prose.** Plain text is ambiguous ("done" could be a final answer or
  commentary), so completion is an explicit tool call. Replying in prose does not end the task.
- **`no_action` guardrail.** If the model answers without calling any tool, the runtime nudges it to act
  (up to 2 nudges); if it still refuses, the run ends as `no_action`. This was the single most common
  failure mode (see results).
- **Empty responses** (`resp.choices` empty) are caught and recorded as `api_error` rather than
  crashing.

### 3.3 The eleven tools (`src/tools.py`)
Exposed via the `TOOLS` dict and `TOOL_SCHEMAS` (OpenAI function-calling format), dispatched by
`execute_tool(name, arguments, workspace)`. Every tool returns a string; errors are returned as strings
beginning with `ERROR:` so the model can read and recover, rather than throwing.

File I/O:
1. `read_file(path)` — read a text file inside the sandbox (UTF-8, `errors="replace"`).
2. `write_file(path, content)` — create or overwrite a file (makes parent dirs).
3. `apply_patch(path, old_text, new_text)` — surgical replace; **refuses unless `old_text` matches
   exactly once** (atomic, no half-applied edit).
4. `multi_edit(path, edits)` — apply several edits to one file **all-or-nothing**; validates every edit
   before writing any.

Discovery:
5. `list_dir(path=".")` — clean directory listing with sizes (hides dotfiles).
6. `glob_files(pattern, path=".")` — shell-glob match (`**` recursive), truncated at 50 entries.
7. `grep_files(pattern, path=".", file_glob="")` — regex search via `grep -rnE` (args passed as a list,
   so no shell injection), truncated at 50 lines.

Execution:
8. `run_bash(command, timeout=600)` — run a shell command with `cwd=workspace`; returns exit code +
   stdout + stderr.
9. `run_python(code, timeout=60)` — run a Python snippet via `python -c`.

Delegation and completion:
10. `spawn_subagent(goal, max_iters=8)` — run an independent child agent in a separate process, sharing
    the same workspace; returns the child's final answer. Used rarely.
11. `finish(summary="")` — explicit task-completion signal.

### 3.4 The sandbox: `_safe_path(path, workspace)`
```python
def _safe_path(path: str, workspace: Path) -> Path:
    p = (workspace / path).resolve()           # resolve .. and symlinks to a real location
    if workspace not in p.parents and p != workspace:
        raise ValueError(f"path {p} escapes workspace {workspace}")
    return p
```
Every file tool routes its path through this one function before touching disk. The model never sees the
`workspace` argument; it can ask to read `src/main.py`, but it cannot choose the root that path is
resolved against, because the runtime passes that root explicitly. A request like `../../etc/passwd`
resolves to `/etc/passwd`, which does not have the workspace as an ancestor, so it raises. The workspace
is an explicit parameter threaded through `run_agent(goal, workspace, …)` and `execute_tool(name, args,
workspace)`; there is no global `WORKSPACE`. This is **not** a complete security sandbox: `run_bash` and
`run_python` can still execute arbitrary code, so they remain dangerous and a real deployment would need
process isolation. `_safe_path` solves one narrower problem — file operations should not read or write
outside the assigned repository.

### 3.5 CLI and context compaction
- `cli/solve.py` — one-shot runner: `python cli/solve.py "task" --workspace dir --max-iters N`.
- `cli/chat.py` — interactive streaming REPL with color-coded thinking, step-by-step tool display, and
  slash commands (`/compact`, `/tokens`, `/think`, `/nothink`, etc.). It auto-summarizes history at
  `COMPACT_THRESHOLD_TOKENS = 24000` (~75% of the 32K window), keeping the last 10 messages verbatim,
  and splits at a clean `user` boundary so no `tool` message is orphaned.
- **Verbose by design.** The runtime logs each model call, tool invocation, tool result, and the model's
  reasoning when available. A silent agent destroys the evidence trail, and the trail is the point of the
  project.

---

## 4. Evaluation methodology (`eval/`)

### 4.1 The benchmark
627 tasks: **163 HumanEval+**, **424 MBPP** (sanitized), **37 hand-written hard tasks**, **3 legacy
demos**. HumanEval+ and MBPP are regenerated by `eval/convert_benchmark.py`. Each task is a directory
with a goal (the spec the agent sees), a reference solution, a stub, and tests.

### 4.2 Hidden-test scoring (`eval/run.py`)
The core honesty mechanism. For tasks marked `## Tests: hidden`:
1. **Snapshot** all task fixtures into memory before the agent runs.
2. **Hide** the test files by deleting them from the workspace, so the agent solving from the spec cannot
   read its own grader (an agent with shell access could otherwise `cat` the tests and hard-code outputs).
3. **Run** the agent in an isolated `workspace/task_N/` directory.
4. **Restore** the tests from the snapshot only after the agent stops.
5. **Score** with an independent pytest the agent never controls. A task passes iff
   `returncode == 0 AND (count of "N passed") >= 1 AND not (any "failed"/"error")`. This prevents a false
   pass from a skipped or zero-collected test session.

`pass@1` is the first-attempt result (the harness keeps `repeat_idx == 0` only, so a lucky later run
cannot inflate the score). Runs are parallel (`--jobs N`).

### 4.3 Validation gate (`eval/validate_tasks.py`)
Before scoring, each task is checked: the reference solution must pass pytest and the stub must fail. A
task that fails either check is quarantined (`tasks/_quarantine/`) as broken, so the benchmark only
contains tasks that actually discriminate a correct solution from an empty one.

---

## 5. The evaluation leak (the central finding)

**What it was.** The MBPP converter (`eval/convert_benchmark.py`) was supposed to turn each MBPP task
into a spec-only goal while keeping the graded tests hidden. It did not. For about **93% of the 424 MBPP
tasks**, it copied **2 of the 3 graded asserts** straight into the prompt the agent could read. The agent
still had to write code, but it could see most of its own grader.

**The inflated number.** The earlier full-benchmark score was **501/627 = 79.9%**, and it was inflated by
this leak.

**How it was found.** While hardening the project, I ran a multi-agent audit and cross-checked the
evaluation setup with a second model (Codex / GPT-5.5). The audit forced me to read the data path
instead of staring at pass rates. Once I looked at a generated MBPP prompt next to its hidden test, the
leak was obvious.

**The fix and the honest number.** I regenerated all 424 MBPP tasks with spec-only goals and reran the
full benchmark. The corrected score was **422/627 = 67.3%** (95% Wilson CI 64–71%).

**The control that makes it credible.** HumanEval+ had never leaked, and it stayed at about **79.8%**
across both runs. That acted as a consistency check: if HumanEval+ had also collapsed, I would have
suspected a broader benchmark change; instead the drop stayed exactly where the leak had been (MBPP). The
lower number is the one that fits the system I actually built.

This is the project's main research lesson: agent evaluation is easy to fool by accident; a result can
look stable while a data pipeline quietly leaks information. Hidden tests, a validation gate, and
adversarial review are the difference between a measurement and a number.

---

## 6. Results (de-leaked 627-task benchmark)

Source file: `skillopt/runs/clean/headline_empty_full.md` (run 20260528-233845).

**Overall: 422/627 = 67.3%**, 95% Wilson CI ≈ [63.5%, 70.9%] (rounded 64–71%).

### 6.1 By source
| Source | Pass@1 | n |
|---|---|---|
| HumanEval+ (never leaked) | 79.8% | 163 |
| MBPP (de-leaked) | 66.7% | 424 |
| Hand-written hard | 21.6% | 37 |
| **Overall** | **67.3%** | **627** |

### 6.2 By difficulty
| Difficulty | Pass | Total | Rate |
|---|---|---|---|
| easy | 153 | 207 | 73.9% |
| medium | 162 | 219 | 74.0% |
| hard | 106 | 198 | 53.5% |
| unknown | 1 | 3 | 33.3% |

(Easy and medium landing at the same rate is real, not a typo: the difficulty labels are coarse, and some
"easy" tasks hide a trap while some "medium" tasks are direct once the spec points at the behavior.)

### 6.3 By category
| Category | Pass | Total | Rate |
|---|---|---|---|
| dp | 4 | 4 | 100.0% |
| math | 66 | 87 | 75.9% |
| strings | 81 | 113 | 71.7% |
| arrays | 89 | 125 | 71.2% |
| algorithms | 110 | 160 | 68.8% |
| regex | 20 | 30 | 66.7% |
| recursion | 27 | 45 | 60.0% |
| data_structures | 20 | 35 | 57.1% |
| uncategorized | 1 | 3 | 33.3% |
| graphs | 1 | 4 | 25.0% |
| multi_file | 1 | 4 | 25.0% |
| refactor | 1 | 4 | 25.0% |
| debugging | 1 | 5 | 20.0% |
| oop | 0 | 4 | 0.0% |
| parsing | 0 | 4 | 0.0% |

(The 0% and 25% categories each have only 4–5 tasks, so those rates are noisy; they point at where a 14B
local model struggles — OOP, parsing, multi-file, debugging — not at a precise rate.)

### 6.4 Finish reasons (all 627)
- finished: 556 (of which 422 passed the hidden tests; 134 finished but were wrong)
- no_action: 66 (model answered in prose without calling a tool — the most common failure)
- max_iters: 3
- timeout: 2

The `no_action` failure is not a coding mistake: the model described what to do and then stopped, which
is useless to the runtime. The guardrail (nudge the model to act) recovered most of these cases. It is
closer to adding a sign that says "use the tools" than to a deep algorithmic fix, but it mattered,
because tool use is the one behavior the whole system depends on.

### 6.5 A caution on determinism
A single benchmark run gives one number, but the local stack is **not deterministic even at temperature
0** (vLLM batching produces run-to-run differences). So 67.3% should be read as a measurement of this
implementation under this benchmark, not as a property of Qwen3-14B or of ReAct in general. This
non-determinism becomes concrete in the SkillOpt experiment.

---

## 7. SkillOpt experiment (reproduction of Yang et al., 2026)

### 7.1 The method
SkillOpt keeps the model weights frozen and optimizes a natural-language **skill document** that is
prepended to the prompt. An optimizer edits the document with append/insert/replace/delete operations; a
candidate edit is kept only if it scores higher on a held-out validation split (strict `>` gate). There
is a textual "learning rate" (clip edits to a budget L), a rejected-edit buffer, and an epoch-wise
slow-update region. My implementation in `skillopt/` is a faithful port of the method's core, with the
decorative components deferred (see §2). The point of the experiment is question (3): can a frozen model
be improved by optimizing text instead of weights, on my agent and my benchmark slice?

### 7.2 Design
Three skill documents are scored once each on a **locked 84-task test split**: **empty** (no skill),
**seed** (a human-written skill), and **optimized** (the skill after the loop). Optimization uses only
the train and a small validation split (**12 tasks**), never the test split. Statistics: Wilson 95% CIs,
paired **McNemar exact-binomial** tests, and a single re-run of the empty arm to estimate run-to-run
instability. All pure-stdlib (`skillopt/report.py`).

### 7.3 Results (test split, scored once)
| Arm | Pass@1 | k/n | Wilson 95% CI |
|---|---|---|---|
| empty | 0.786 | 66/84 | [0.687, 0.860] |
| seed | 0.738 | 62/84 | [0.635, 0.820] |
| optimized | 0.774 | 65/84 | [0.674, 0.850] |

By difficulty (empty / seed / optimized): easy 26/28, 24/28, 25/28; medium 21/29, 20/29, 22/29; hard
19/27, 18/27, 18/27.

Paired McNemar (exact binomial), vs optimized:
- optimized vs empty: 1 task improved, 2 regressed (n_discordant = 3, **p = 1.000**).
- optimized vs seed: 5 tasks improved, 2 regressed (n_discordant = 7, **p = 0.453**).

Run-to-run instability: re-running the **empty** arm with the same skill and settings flipped **6 of 84
tasks** (about 7 points). This is one draw, an estimate of instability, not a formal noise floor. Flips
between arms: empty–seed = 8, empty–optimized = 3, seed–optimized = 7. Validation signal: seed val 0.667
→ best val 0.750 (Δ = +0.083, but on 12 tasks that is exactly one task).

### 7.4 Verdict: inconclusive / under-powered
The differences between arms (empty↔optimized = 3, empty↔seed = 8, seed↔optimized = 7 flips) are the same
size as the run-to-run instability (6 flips), and no pairwise McNemar test reaches p < 0.05. The optimized
arm did not beat the empty baseline; it edged the seed, but inside the noise. This does not show that
skill optimization fails. It shows that this setup cannot tell. A better version needs a larger
validation set, more test tasks, several runs per arm, and tighter control over inference
non-determinism. Reporting a null/inconclusive result honestly is the correct outcome here.

---

## 8. Limitations
- One model, served one way, on one GPU. No comparison across model sizes, serving stacks, or commercial
  APIs.
- The ReAct loop is standard (implemented from scratch, not invented here). The agent does not exceed
  Claude or Codex, and no such claim is made.
- The benchmark is better after the leak fix but still small in its hard parts: 37 hand-written hard
  tasks, an 84-task SkillOpt test split, a 12-task validation set. These catch large effects, not subtle
  ones.
- The main conditions were scored once each, which is weak given the temperature-0 non-determinism; a
  stronger study would repeat each condition and report the variation.
- The sandbox is narrow: `_safe_path` protects the file tools, but shell execution stays powerful and a
  real deployment would need process isolation.
- The agent has no browser, no separate planner, and no memory beyond the message history and the files
  it writes.

## 9. What is mine vs reused
- **Reused:** the ReAct pattern (Yao et al., 2023); the benchmark tasks (HumanEval+, MBPP, via EvalPlus);
  the idea of optimizing text instead of weights (OPRO, TextGrad, GEPA); the SkillOpt method itself (Yang
  et al., 2026), which my experiment reproduces; the notion of reusable agent skills (Voyager). The model
  (Qwen3-14B), the serving engine (vLLM), and the client (OpenAI SDK, `python-dotenv`) are external.
- **Mine:** the runtime around them — the `run_agent` loop, the tool wiring and dispatch, the workspace
  sandbox, the benchmark harness with its validation gate and hidden-test scoring, the SkillOpt
  experiment code (a port of the published method onto my agent), and the MBPP leak fix. The teaching
  shape (small source, verbose runtime, an examples ladder from a chat script to a sandboxed loop) is
  deliberate. The leak discovery is part of the result: I did not plan it, but the evaluation is stronger
  for throwing the bad number out.

## 10. Reproduction
1. Serve the model: `bash scripts/start_vllm.sh` (Qwen3-14B on GPU1, port 8765); confirm with
   `curl -s http://localhost:8765/v1/models`.
2. One task: `python cli/solve.py "…task…" --workspace /tmp/ws --max-iters 18`.
3. Full benchmark: `python eval/run.py --jobs N` (hidden-test scoring, validation gate). Headline result
   in `skillopt/runs/clean/headline_empty_full.md`.
4. SkillOpt A/B: run the three arms, then `python skillopt/report.py --empty … --seed … --optimized …
   --empty-rerun …` to regenerate `docs/SKILLOPT_RESULTS.md`.

---

## 11. Every number in one place (for cross-checking the paper)
| Quantity | Value | Source |
|---|---|---|
| Total tasks | 627 (163 HumanEval+, 424 MBPP, 37 hard, 3 legacy) | eval, README |
| Honest accuracy | 422/627 = 67.3% | headline_empty_full.md |
| 95% Wilson CI | ≈ [63.5%, 70.9%], rounded 64–71% | report.py wilson_ci(422,627) |
| Inflated (leaked) accuracy | 501/627 = 79.9% | final_run.md, paper |
| Leak extent | ~93% of 424 MBPP, 2 of 3 graded asserts | paper, audit |
| HumanEval+ (control, both runs) | ~79.8% (163) | paper, README |
| MBPP de-leaked | 66.7% (424) | paper |
| Hand-written hard | 21.6% (37) | paper |
| Difficulty easy/medium/hard | 73.9% / 74.0% / 53.5% | headline_empty_full.md |
| Finish: finished/no_action/max_iters/timeout | 556 / 66 / 3 / 2 | headline_empty_full.md |
| SkillOpt empty/seed/optimized | 0.786 (66/84) / 0.738 (62/84) / 0.774 (65/84) | SKILLOPT_RESULTS.md |
| SkillOpt Wilson CIs | [.687,.860] / [.635,.820] / [.674,.850] | SKILLOPT_RESULTS.md |
| McNemar opt-vs-empty / opt-vs-seed | p = 1.000 (3 disc.) / p = 0.453 (7 disc.) | SKILLOPT_RESULTS.md |
| Run-to-run flips (empty rerun) | 6/84 (single draw) | SKILLOPT_RESULTS.md |
| SkillOpt validation set | 12 tasks (seed 0.667 → best 0.750) | SKILLOPT_RESULTS.md |
| Context window | 32768 (32K) | start_vllm.sh, models.json |
| Max iterations | 15 | agent.py |
| Compaction threshold | 24000 tokens | cli/chat.py |
| Core code size | agent.py ~963, tools.py ~1276 lines | repo |

## 12. Suggested paper outline (if rewriting from scratch)
Abstract → Introduction (motivation, research questions, the honest 67.3% headline) → System (loop, 11
tools, `_safe_path`, serving stack) → Evaluation methodology (627 tasks, hidden-test scoring, validation
gate) → The Leak (what, how found, before/after, the HumanEval+ control) → Results (overall + by source +
by difficulty + finish reasons, the determinism caution) → SkillOpt (method = Yang et al. 2026
reproduction, design, results, inconclusive verdict) → Limitations → What is mine vs reused → Conclusion.
Figures that carry weight: Pass@1 by source with the overall CI; the leak before/after with HumanEval+
flat as a control; the SkillOpt three arms with Wilson CI error bars overlapping. Tone: plain, first
person, let the numbers and the leak story carry it; do not oversell; the strength is rigor, not raw
score.

## 13. References (verified)
See `docs/paper/paper.tex` bibliography for the formatted numbered list. Keys and ids:
ReAct 2210.03629 · Reflexion 2303.11366 · Toolformer 2302.04761 · Voyager 2305.16291 · OPRO 2309.03409 ·
TextGrad 2406.07496 · GEPA 2507.19457 · SkillOpt 2605.23904 · Qwen3 2505.09388 · vLLM/PagedAttention
2309.06180 · HumanEval/Codex 2107.03374 · MBPP 2108.07732 · EvalPlus 2305.01210 · LiveCodeBench
2403.07974 · McNemar (Psychometrika, 1947) · Wilson (JASA, 1927).
