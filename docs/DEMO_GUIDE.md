# Live Demo Guide — coding agent (Friday talk)

> One-liner while it runs: *"I give it an English spec — no tests. It writes the code, then writes its own check and runs it to confirm. Every step is on screen, and it's all local, on our GPU."*

## How the agent really works (say this if anyone asks)
You give it a natural-language **spec**. It reasons → writes code → **runs the code itself** to check → fixes → calls `finish`. In the benchmark the grading tests are **hidden** from the agent the whole time (moved out of the workspace, restored only to score), so the 67.3% is solving-from-spec, not test-peeking.

## 0. Pre-flight (before the talk)
```bash
cd /home/tle/code/coding-agent
tmux attach -t vllm                         # vLLM (Qwen3-14B) should already be serving on :8765
# Ctrl-b d to detach. If it isn't up:  bash scripts/start_vllm.sh
curl -s http://localhost:8765/v1/models     # confirm Qwen/Qwen3-14B
bash scripts/demo.sh                         # one throwaway warm-up run so the first on-stage call isn't cold
```

## 1. MAIN demo — spec in, NO tests given ✅ verified 2/2 live, correct on all 1-3999
One command. The workspace is empty, so the agent builds everything from one English sentence.
```bash
bash scripts/demo.sh
```
Spec it gets: *"Write int_to_roman and roman_to_int for 1 to 3999, with no tests. Add your own round-trip check (number to numeral and back), run it, and finish only when it passes."*

**Trace you'll see:** `write_file roman.py` (both functions + a round-trip check) → `run_bash python roman.py` → `4, 9, 58, 1994, 3999: all PASS` → `finish`. It writes both directions of the conversion plus its own way to verify them.

**What to narrate:** "It never saw a test. From one sentence it wrote both directions of the conversion, then wrote its own check: convert a number to Roman and back, and confirm they match. It ran that, saw it pass, and stopped. All local, on our GPU, with every step on screen." The alternatives below are also tested.

### Swap in any spec (same one command)
```bash
bash scripts/demo.sh "Create flatten.py with flatten(x) that flattens an arbitrarily nested list of ints into a flat list. No tests given — run it on [[1,[2,3]],4,[5]] to confirm you get [1,2,3,4,5], then finish."
bash scripts/demo.sh "Create brackets.py with is_balanced(s) returning True iff (), [], {} are balanced. No tests given — check '([]{})' is True and '(]' is False before finishing."
```
All single-function specs in this shape are the reliable sweet spot for Qwen-14B (~80% on HumanEval-style tasks).

## 2. SECONDARY (optional) — fix a bug in existing code
A real scenario: an existing repo with a **red test suite** (like a failing CI). This is the one case where tests are visible — say so honestly. ~45–60s, deterministic.
```bash
rm -rf /tmp/demo_calc && cp -r demo_repo /tmp/demo_calc && rm -rf /tmp/demo_calc/__pycache__
.venv/bin/python cli/solve.py "Run test_calculator.py with pytest to see what fails, read calculator.py to find the bug, fix it, and re-run pytest to confirm before finishing." --workspace /tmp/demo_calc --max-iters 15
```
⚠️ Always the `/tmp` copy, never the real `demo_repo` (otherwise the bug is already fixed next run).

## 3. If something breaks live
- Re-run `bash scripts/demo.sh` (fresh workspace every time — always safe to repeat).
- vLLM down and unrecoverable: narrate from the slides — architecture (ReAct loop, 11 tools, `_safe_path` sandbox) and the integrity story (found & fixed my own benchmark leak, 79.9% → honest 67.3%). No live model needed.

## Honesty guardrail (say it proactively)
It does **not** beat Claude/Codex on raw capability. The pitch is: **local + transparent + built-from-scratch + honestly-measured (67.3% on 627 hidden-test tasks).**
