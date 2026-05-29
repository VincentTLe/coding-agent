# A From-Scratch ReAct Coding Agent on a Local Qwen3-14B: Honest Measurement, a Self-Inflicted Benchmark Leak, and a Frozen-Weight Skill-Optimization Experiment

**Math/Stat 361 Undergraduate Research, Knox College**
**Advisor: Prof. Andrew Leahy**

---

## Abstract

This paper reports an undergraduate research project: a coding agent built from scratch — no agent framework — that drives a *local* open-weight language model (Qwen3-14B, served by vLLM on a single GPU) through a ReAct loop with 11 tools and a path-traversal sandbox. The agent reads, edits, runs, and verifies code inside a confined workspace. The contribution is **not** the loop itself, which is a faithful reimplementation of well-established ideas (ReAct; tool-using agents). The contributions are (1) an honestly measured evaluation on a 627-task benchmark with hidden-test scoring, (2) the discovery and correction of a benchmark-integrity bug **in my own harness** — graded test assertions were leaking into the prompt the agent could read, which had inflated an earlier headline of 79.9% — and the honest re-measurement at **67.3%** (422/627, 95% CI 64–71%), (3) an empirical failure-mode finding from the eval traces (the dominant failure was the model replying in prose without calling a tool; a guardrail recovered most of it), and (4) **SkillOpt**, an exploratory experiment in optimizing a natural-language *skill document* while the model weights stay frozen — reported with a fully honest, **under-powered / inconclusive** statistical verdict. Throughout, the methodological honesty is treated as the result, not as a disclaimer.

---

## 1. Introduction and Motivation

Cloud coding assistants such as Claude Code and Codex are powerful, but they are black boxes: the loop, the prompt, the tool layer, and the scoring are all hidden behind an API, and the code and data leave the machine. My prior experience with AI-generated codebases left me with software I could not explain. The motivating goal of this project was the opposite: **build a coding agent I can explain line by line**, run it entirely on my own hardware, and measure it honestly enough to defend the numbers to a skeptic.

So this is a personal-scale reimplementation with three deliberate properties that distinguish it from the cloud tools — not in raw capability, but in *transparency*:

1. **Local.** The model is Qwen3-14B (BF16, ~28 GB) served by vLLM on one GPU, exposed over an OpenAI-compatible endpoint at `localhost:8765`. No hosted API; data never leaves the machine.
2. **Transparent.** The runtime is verbose by design: every tool call, every tool result, and the model's reasoning are logged so I (and the reader) can watch the agent work and read its failures in the traces.
3. **From scratch.** No LangChain, LangGraph, or CrewAI. The ReAct loop, the tool registry, the sandbox, and the eval harness are hand-written against the raw chat-completions protocol. The only substantive third-party pieces are the OpenAI SDK (HTTP transport) and vLLM (model serving), plus `python-dotenv` for config.

I want to be explicit about scope at the outset. **The agent does not beat Claude or Codex on raw capability, and I do not claim it does.** The ReAct loop is not novel research. What is mine is the from-scratch implementation I fully understand, the honest measurement methodology, and the discovery and correction of my own benchmark leak.

---

## 2. System Design

### 2.1 The ReAct loop

The agent uses the standard ReAct pattern (Yao et al., 2023): **reason → act → observe**, interleaved. `run_agent(goal, workspace, ...)` in `src/agent.py` initializes a message list with one frozen system prompt and the user's goal, then loops up to `max_iters` (default 15) times. Each turn:

1. **Reason / Act.** Send the full message history plus the tool schemas to the model with `tool_choice="auto"`. The model responds either with plain content (it believes the task is done) or with one or more `tool_calls`.
2. **Observe.** If there are tool calls, execute each one, append the result back as a `role="tool"` message, and loop. If there are none, terminate.
3. **Safety net.** Stop after `max_iters` turns.

The model runs under vLLM with `--reasoning-parser qwen3` (which splits out the model's `<think>` block) and `--tool-call-parser hermes` (which turns the model's Hermes-format tool calls into structured `tool_calls`). Tools are a registry (`name → function` plus a JSON-schema list), so adding a tool is append-only: the loop never changes. A subtle but load-bearing correctness detail is that an assistant message carrying `tool_calls` must be appended verbatim (via `model_dump(exclude_none=True)`) so each tool call is paired with its result — orphaning a tool call causes the API to reject the next request with a 400 error.

The loop is also defensive about real-world failure on a shared GPU. The OpenAI client is constructed with an **explicit per-request timeout (120 s) and `max_retries=1`** rather than the SDK defaults (a 600 s per-request timeout with automatic retries), because a single stalled vLLM call could otherwise hang one turn for many minutes — a hazard found during the audit (§3). API errors and empty `choices` are caught and returned as a clean `finish_reason`, so a transient failure records an outcome rather than crashing the run.

### 2.2 The 11 tools

All tools live in `src/tools.py` — implementation, JSON schema, and a single `execute_tool()` dispatcher side by side — in five groups:

| Group | Tools |
|---|---|
| **File I/O** | `read_file`, `write_file`, `apply_patch`, `multi_edit` |
| **Discovery** | `list_dir`, `glob_files`, `grep_files` |
| **Execution** | `run_bash` (600 s timeout), `run_python` (60 s timeout) |
| **Delegation** | `spawn_subagent` (separate process, 300 s + 8-iteration cap) |
| **Completion** | `finish(summary)` |

Edits are **safe by construction**: `apply_patch` refuses to apply unless `old_text` matches exactly once (it rejects ambiguous edits), and `multi_edit` validates all edits before writing, so a failed edit never leaves a half-modified file. `spawn_subagent` runs in a *separate process* for context isolation, crash containment, and bounded recursion. The `finish` tool is an explicit completion signal that complements the "no tool calls" termination convention.

### 2.3 The `_safe_path` sandbox

Every file operation routes through `_safe_path(path, workspace)`, a CWE-22 path-traversal defense. It resolves the requested path against the workspace (`(workspace / path).resolve()`, which collapses `..` and follows symlinks) and raises `ValueError` unless the resolved path is the workspace itself or a descendant of it. Crucially, the workspace is an **explicit parameter** threaded through `run_agent(goal, workspace, ...)` and `execute_tool(name, args, workspace)` — there is no global workspace state and no `set_workspace`. The model never sees a `workspace` argument (it is deliberately absent from the tool schemas and injected by the dispatcher), so it cannot read or write outside its sandbox. A registry-vs-schema assertion (`set(TOOLS) == {names in TOOL_SCHEMAS}`) prevents the function table and the model-visible schemas from silently drifting apart.

---

## 3. Evaluation Methodology — and the Leak It Surfaced

### 3.1 The harness

The benchmark (`eval/run.py`) comprises **627 tasks**: 163 from HumanEval+, 424 from a de-leaked MBPP conversion, 37 hand-authored hard tasks (debugging, refactor, multi-file, dynamic programming, graphs, data structures, OOP, parsing), and 3 legacy demos. It runs agents in parallel (`--jobs N`), and for each task it snapshots the fixtures, runs the agent, then scores with an **independent `pytest` the agent never controls** and restores the fixtures afterward.

Two design choices make the number trustworthy:

- **Hidden tests.** For benchmark tasks, the test files are physically removed from the workspace before the agent runs and restored only at grading time. The agent implements from the *spec*, not by reading and hard-coding the graded assertions. (Debug/refactor tasks intentionally keep tests visible so the agent can use `pytest` as a feedback signal.)
- **Validation gate.** `eval/validate_tasks.py` proves every task is real before it counts: the reference solution must pass and an empty stub must fail. Malformed tasks are excluded, so each of the 627 is a well-formed problem.

The harness also records `no_action` (the model replied without acting) as a distinct outcome rather than silently failing — which turned out to matter (§4).

### 3.2 The benchmark leak — found, diagnosed, fixed

An earlier full run scored **79.9% (501/627)**. While hardening the project with a multi-agent audit, I found that this number was **inflated by a bug in my own benchmark converter**.

The MBPP converter (`eval/convert_benchmark.py`) built each task's goal as the problem text followed by `Example checks:\n` plus `"\n".join(test_list[:2])` — i.e. the **first two raw `assert` statements from the graded test list, verbatim**, embedded directly in the agent-visible `## Goal`. Meanwhile the task metadata declared `## Tests: hidden` and the harness deleted the test files. So the anti-cheat claim was materially false for the MBPP half: most MBPP tasks have exactly three graded asserts, meaning **two of the three graded assertions (exact inputs *and* expected outputs) were handed to the agent** for roughly 93% of the 424 MBPP tasks. HumanEval, by contrast, exposed only the natural docstring — so the two halves of the benchmark were not even measuring the same thing, and aggregate comparisons were inconsistent.

The bug was surfaced by an **adversarial multi-agent audit** and cross-checked with an independent cross-provider review (a separate model, Codex / GPT-5.5-class). The audit cross-read the converter against the harness — the leak was invisible from either file alone — and confirmed it against the cached dataset (every MBPP task embedded two real asserts).

**The fix** was to stop placing raw graded asserts in the goal: MBPP goals became **spec-only**, matching HumanEval, and all 424 MBPP tasks were regenerated. Re-running clean gave the honest **67.3%**.

I treat finding and fixing my own leak as a primary result, not a footnote. The audit also catalogued a cluster of related substrate weaknesses I subsequently addressed or documented — e.g. a snapshot/restore that corrupted binary fixtures, a scoring `pytest` timeout (60 s) far shorter than the agent's own (600 s) that could fail correct-but-slow solutions, an all-tests-skipped session scoring as PASS, an infra-failure-vs-real-0.0 ambiguity in the SkillOpt rollout, and a pervasive lack of run-provenance (model/temperature/iters/git-SHA) in result files. The honest position is that **the agent and harness were individually reasonable, but the surrounding evaluation substrate was not yet self-describing enough to defend a number to a skeptic** — and that is exactly why the audit mattered.

---

## 4. Results

### 4.1 The honest headline

On the clean, de-leaked, hardened re-run, the agent solved **422 / 627 = 67.3%** (95% CI 64–71%), with tests hidden the whole time. The per-slice breakdown:

| Slice | Pass rate | k / n |
|---|---|---|
| HumanEval+ (never leaked) | **79.8%** | 130 / 163 |
| MBPP (de-leaked) | **66.7%** | 283 / 424 |
| Curated hard (hand-written) | **21.6%** | 8 / 37 |
| **Overall** | **67.3%** | **422 / 627** |

By difficulty, there is a clean and sensible gradient: **easy 74% / medium 74% / hard 54%**. Note that the never-leaked HumanEval slice is essentially unchanged from before the fix (~80%), while MBPP fell from inflated to its true ~67% — exactly the signature you would expect if the leak was confined to MBPP. The curated hard tier is the honest stress test, and the 21.6% there is the most sobering and most informative number: hand-written, multi-step problems are where a local 14B agent is genuinely weak.

**Honest caveats on the headline.** HumanEval/MBPP are well-known and partially saturated, so the benchmark tier is best read as a breadth + harness-sanity signal, while the curated hard tier is the real stress test. The model is an open-weight 14B at temperature 0, but vLLM batching at temperature 0 is **not** bitwise deterministic, so pass rates carry run-to-run noise (quantified in §5). Wilson confidence intervals are reported rather than naive proportions because *n* per slice is moderate and the intervals are asymmetric near the extremes.

### 4.2 The empirical finding: prose instead of action

The genuinely useful contribution from this evaluation came from *reading the traces*, which the from-scratch, verbose design made possible. The dominant failure mode was not bad code — it was the model **replying in prose without ever calling a tool** (`no_action`), accounting for **66 of the 627** tasks. The model would describe the fix, or even write the code as text, and then stop, leaving the disk unchanged so the task was scored as a failure.

The remedy was a **guardrail, not a smarter model**: a `NUDGE` message (capped at two nudges) that, when the model answers with text but no tool call before it has acted, explicitly tells it that nothing has changed on disk and that it must call `write_file` / `apply_patch` / `multi_edit` now. This recovered most of those cases. The lesson — and the most important thing the from-scratch approach taught me — is that **agent reliability at this scale is mostly engineering** (the sandbox, the verify loop, the error contract, the guardrail) wrapped around a model that is already capable, and that the failure modes only became concrete because I could read them in the traces of code I wrote myself.

---

## 5. The SkillOpt Experiment

### 5.1 Idea and design

SkillOpt is the research-flavored, exploratory part of the project. The question: **can the agent improve by learning a natural-language *skill document* while the model weights stay frozen?** Instead of fine-tuning, the optimizer performs something like "gradient descent on text" — proposing edits to a prose skill that is concatenated onto the system prompt — gated by held-out validation.

The loop (`skillopt/loop.py`) works as an **optimize → eval → gate** cycle. Each step:

1. **Rollout** the current skill on the train split (via `eval/run.py`).
2. **Reflect**: an optimizer LLM reads the failure and success cases and proposes edits (append / insert / replace / delete).
3. **Merge** (failures prioritized) and **clip** to at most `L` edits — `L` acts as a textual "learning rate."
4. **Apply** the edits to a candidate skill, preserving a protected "slow-update" region.
5. **Gate**: score the candidate on the validation split and accept **only if strictly better** (ties reject). A new best is checkpointed to `best_skill.md`.

At each epoch boundary, a "slow update" compares the epoch's start vs. end skill across four buckets (improved / regressed / persistent-fail / stable-success) and writes a durable "executive-strategy" block into the protected region. Rollouts are cached by `(skill_hash, split)` to save GPU. Critically — as a direct consequence of the audit — an infra-failed rollout (timeout / incomplete) returns `None`, **not** `0.0`, so a transient failure cannot fabricate a phantom baseline or auto-accept the first non-zero candidate; the seed rollout failing aborts the run rather than optimizing against a fake 0%.

### 5.2 The honest result: under-powered, inconclusive

I evaluated three arms on a **locked 84-task held-out test split, scored once**: an **empty** skill (none), the **seed** (a hand-written starting skill), and the **optimized** skill (the loop's output). Optimization used only train + val.

| Arm | pass@1 | k / n | Wilson 95% CI |
|---|---|---|---|
| empty | 0.786 | 66 / 84 | [0.687, 0.860] |
| seed | 0.738 | 62 / 84 | [0.635, 0.820] |
| optimized | 0.774 | 65 / 84 | [0.674, 0.850] |

The honest verdict is **INCONCLUSIVE (under-powered)**, and the statistics are the point:

- **Paired exact-binomial McNemar** (the right test for paired pass/fail data on the same tasks) reached significance for **none** of the comparisons. Optimized vs. empty: 1 task improved, 2 regressed (3 discordant, **p = 1.000**). Optimized vs. seed: 5 improved, 2 regressed (7 discordant, **p = 0.453**). All comparisons are p ≥ 0.29.
- **Run-to-run instability is the same size as the effects.** Re-running the *identical* empty config gave 0.786 vs. 0.738 — **6 of 84 tasks flipped purely from vLLM nondeterminism** at temperature 0. The between-arm flip counts (empty–seed = 8, empty–optimized = 3, seed–optimized = 7) are at or near that instability. I am careful to call this a single-draw *estimate* of run-to-run noise, **not** a formal "noise floor" — a heuristic, flagged as such in the cross-provider methodology review, sitting alongside the exact McNemar tests rather than replacing them.
- **The mechanism signal is weak.** On validation, seed 0.667 → best 0.750, but |val| is tiny (12 tasks, so one task ≈ 0.083). On test, seed 0.738 → optimized 0.774 is directionally positive (Δ = +0.036) but does not reach p < 0.05, so I cannot claim the learned edits "transfer."

**What SkillOpt does and does not show.** It *does* demonstrate a working, validation-gated, checkpointed, auditable frozen-weight skill-optimization pipeline with honest statistics — Wilson CIs, exact McNemar, and an explicit instability estimate. It does **not** show that the optimized skill helps (or hurts): the observed differences are smaller than or comparable to the measured run-to-run noise, and no test reaches significance. A real verdict would need ≥3–5 runs per arm (averaged) or a much larger test set. The honest reporting *is* the contribution here.

---

## 6. Limitations and Honesty

- **Single model.** Everything is measured on one model (Qwen3-14B). I make no claim about generalization to other models or sizes.
- **Small N, noisy estimator.** SkillOpt's 84-task test split is small, and temperature-0 vLLM is not deterministic, so single-draw point estimates are noisy. This is why the result is inconclusive rather than positive.
- **Local optimizer.** SkillOpt is a hill-climbing, validation-gated text optimizer, not a principled global one; the strict-`>` gate can reject ties that were real improvements lost to noise.
- **Not novel.** The ReAct loop and tool-using-agent paradigm are established prior work. This is a reimplementation; the originality is in implementation, honest measurement, and the leak story.
- **Does not beat Claude/Codex.** On raw capability it does not, and I do not claim it does. Its edge is being local, transparent, fully explainable, and honestly measured.
- **Toy-to-moderate task scale.** HumanEval/MBPP/curated tasks are single-file or small; this is not SWE-Bench-scale repository surgery. There is no real tool parallelism and a single shared workspace, not isolated concurrent environments.

---

## 7. What Is Genuinely Mine vs. Reused

**Reused (and credited):** the ReAct paradigm; the OpenAI SDK as HTTP transport; vLLM for model serving; Qwen3-14B as the model; HumanEval+ and MBPP as benchmark sources; the conceptual lineage of text-as-optimization-target (TextGrad, OPRO, GEPA) and skill-learning agents (Voyager) behind SkillOpt.

**Genuinely mine:** the from-scratch ReAct loop and message-pairing correctness handling; the 11-tool registry with the registry-vs-schema drift guard; the `_safe_path` sandbox as an explicit-parameter (not global) design; the safe-by-construction edit tools; the 627-task harness with hidden-test scoring and the validation gate; the **discovery, diagnosis, and fix of my own MBPP assert leak** (79.9% → 67.3%); the empirical `no_action` finding and the nudge guardrail recovered from reading the traces; and the SkillOpt pipeline with its honest statistics (Wilson CIs, exact McNemar, instability estimate, infra-failure-vs-real-0.0 handling). AI assistants helped write and audit the code, but every line is one I can explain — the explicit goal of the project.

---

## 8. Conclusion

I built a coding agent from scratch that runs a local Qwen3-14B through a ReAct loop with 11 sandboxed tools, and I measured it honestly: **67.3%** on a 627-task benchmark with hidden-test scoring and a validation gate. The headline I am proudest of is not that number but the story behind it — I found a benchmark-integrity bug in my own harness (graded MBPP asserts leaking into the prompt), which had inflated an earlier 79.9%, surfaced it through an adversarial multi-agent + cross-provider audit, fixed it, and re-ran clean. From the traces I identified the dominant failure mode (prose instead of action, 66/627) and recovered most of it with a guardrail — a tool-use fix, not a smarter model. Finally, SkillOpt explored frozen-weight skill optimization and returned an honest *inconclusive* verdict, backed by exact McNemar tests and an explicit account of run-to-run noise. The agent does not out-muscle Claude or Codex; its value, and the value of doing it from scratch, is that it is local, transparent, fully explainable, and honestly measured — and that doing it from scratch is precisely what made the failure modes, and my own mistakes, legible.

---

## References

- Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. (2023). *ReAct: Synergizing Reasoning and Acting in Language Models.* ICLR. (arXiv:2210.03629)
- Wang, G., Xie, Y., Jiang, Y., Mandlekar, A., Xiao, C., Zhu, Y., Fan, L., & Anandkumar, A. (2023). *Voyager: An Open-Ended Embodied Agent with Large Language Models.* (arXiv:2305.16291)
- Yuksekgonul, M., et al. (2024). *TextGrad: Automatic "Differentiation" via Text.* (arXiv:2406.07496)
- Agrawal, L. A., et al. (2025). *GEPA: Reflective Prompt Evolution Can Outperform Reinforcement Learning.* (arXiv:2507.19457)
- Yang, C., Wang, X., Lu, Y., Liu, H., Le, Q. V., Zhou, D., & Chen, X. (2023). *Large Language Models as Optimizers (OPRO).* (arXiv:2309.03409)
- Chen, M., et al. (2021). *Evaluating Large Language Models Trained on Code (HumanEval).* (arXiv:2107.03374)
- Liu, J., Xia, C. S., Wang, Y., & Zhang, L. (2023). *Is Your Code Generated by ChatGPT Really Correct? (EvalPlus / HumanEval+).* NeurIPS. (arXiv:2305.01210)
- Austin, J., et al. (2021). *Program Synthesis with Large Language Models (MBPP).* (arXiv:2108.07732)

*Note on prior art:* I cite ReAct, Voyager, TextGrad, GEPA, and OPRO as the established conceptual lineage for the agent loop and for SkillOpt's "optimize text under an evaluation gate" idea. I have **not** independently verified a single canonical "SkillOpt" paper citation; the name here refers to this project's own pipeline, and any external SkillOpt-titled reference should be treated as unverified.
