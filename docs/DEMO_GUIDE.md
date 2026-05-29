# Live Demo Guide — coding agent (Friday talk)

> One-liner to say while it runs: *"This is a coding agent I built from scratch. It runs on **our own GPU** (no cloud), and you can **watch every step** — it reads, runs tests, edits code, and re-checks itself. It doesn't out-code Claude or Codex; the point is it's local, transparent, and I can explain every line."*

## 0. Pre-flight (do BEFORE the talk)
```bash
cd /home/tle/code/coding-agent
bash scripts/start_vllm.sh                 # start Qwen3-14B on GPU1 (NOT always-on)
curl -s http://localhost:8765/v1/models    # confirm it's serving Qwen/Qwen3-14B
# WARM-UP run so the first on-stage call isn't cold/slow (throwaway copy):
rm -rf /tmp/demo_calc && cp -r demo_repo /tmp/demo_calc && rm -rf /tmp/demo_calc/__pycache__
.venv/bin/python cli/solve.py "Run test_calculator.py, find why it fails, fix calculator.py, then re-run it to confirm." --workspace /tmp/demo_calc --max-iters 15
```
⚠️ ALWAYS run on a **/tmp copy** (`--workspace /tmp/...`), never on the real `demo_repo` — otherwise the bug gets fixed and the next run has nothing to show. **Re-copy before each run.**

## 1. MAIN demo (recommended — ~45–60s, clean & legible) ✅ VERIFIED 2/2
A single, unambiguous bug. The audience sees the full loop: see the failure → read the source → fix → re-verify.
**Verified twice (deterministic at temp 0):** exact trace `run_bash → read_file → apply_patch → run_bash → finish`, **3/3 calculator tests pass** both times. This is the one to demo.
```bash
rm -rf /tmp/demo_calc && cp -r demo_repo /tmp/demo_calc && rm -rf /tmp/demo_calc/__pycache__
.venv/bin/python cli/solve.py "First run test_calculator.py with pytest to see what's failing. Then read calculator.py to find the bug, fix it, and run pytest again to confirm all tests pass before you finish." --workspace /tmp/demo_calc --max-iters 15
```
**What to narrate as it streams:** "It's running the tests itself… now it's read the source and spotted that `add` returns `a - b`… it's patching the file… and re-running to confirm — green. It decided it was done and called `finish`." Point out: **every tool call + its reasoning is on screen** (vs Claude/Codex black box), and **this is local** (our GPU).

## 2. STRETCH (optional — ⚠️ NOT RELIABLE, ~3–4 min)
Multi-bug autonomy across two files (calculator + algorithms).
**⚠️ Honest reliability: INCONSISTENT.** In testing it passed 11/11 on one run but on another it made 9 patches, never re-verified, and left tests failing — Qwen-14B doesn't reliably converge on the multi-bug task. **Do NOT promise it passes live.** Only attempt it if you want to *show ambition* ("watch it tackle several bugs at once") and you're comfortable narrating a partial result. If it stalls, cut back to MAIN.
```bash
rm -rf /tmp/demo_all && cp -r demo_repo /tmp/demo_all && rm -rf /tmp/demo_all/__pycache__
.venv/bin/python cli/solve.py "Every test in this repo is failing. Run the tests, find every bug, fix them all, and re-run pytest to confirm all pass before finishing." --workspace /tmp/demo_all --max-iters 20
```
**Recommendation: stick with MAIN.** It's the verified, deterministic, legible one.

## 3. Interactive flavor (optional, ~30s) — "the conversational version"
```bash
rm -rf /tmp/demo_chat && cp -r demo_repo /tmp/demo_chat && rm -rf /tmp/demo_chat/__pycache__
.venv/bin/python cli/chat.py --workspace /tmp/demo_chat
# then type a task, e.g.: Fix the failing test in calculator.py and confirm it passes.
```
⚠️ Known rough edge: `chat.py` doesn't special-case `finish`, so after the model finishes it loops one extra turn — the ending looks less crisp than `solve.py`. Use this only as a brief "here's the chat version" flourish, not the core demo.

## 4. If something breaks live (recovery)
- **Anything weird / a run drags:** re-copy `demo_repo` to `/tmp` and re-run the **MAIN** `solve.py` command — it's the most reliable artifact (temperature 0, re-runnable indefinitely).
- **vLLM down / can't recover:** narrate from the slides — the architecture (ReAct loop, 11 tools, `_safe_path` sandbox) and the integrity story (found & fixed my own benchmark leak, 79.9% → honest 67.3%). No live model needed.

## Honesty guardrail (say it proactively)
It does **not** beat Claude/Codex on raw capability. The pitch is: **local + transparent + built-from-scratch + honestly-measured (67.3% on 627 tasks).**
