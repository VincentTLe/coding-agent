#!/usr/bin/env bash
# Multi-seed eval: 5 independent runs per arm (empty / seed / optimized) on the locked
# 84-task test split. "Seeds" = independent re-runs; the only variation is vLLM's temp=0
# batching nondeterminism (the noise floor we measured at ~6 flips). 5 runs/arm lets us
# report mean ± std and decide if any arm's distribution is separable from the others.
#
# Reuses the 4 single runs already done (empty x2, seed x1, optimized x1). Sequential by
# design (eval/run.py hides+restores files inside eval/tasks/ in place → concurrent races).
# Unattended-safe: skip-if-complete (restart-safe), per-run 90-min SIGINT timeout, and a
# `git checkout -- eval/tasks/` after every run to force a clean state so one bad/killed
# run can't corrupt the next one's hidden-test scoring.
set -uo pipefail
cd /home/tle/code/coding-agent
PY=.venv/bin/python3
MS=skillopt/runs/v1/multiseed
mkdir -p "$MS"
LOG=$MS/multiseed.log
TASKS=skillopt/runs/v1/test.txt
COMMON="--tasks-file $TASKS --jobs 8 --temperature 0 --max-iters 20 --agent-timeout 420"

# Pre-populate run #1/#2 slots from the single runs already on disk (don't waste ~1.5h).
cp -n skillopt/runs/v1/test_empty.jsonl        "$MS/empty_r1.jsonl"     2>/dev/null || true
cp -n skillopt/runs/v1/test_empty_rerun.jsonl  "$MS/empty_r2.jsonl"     2>/dev/null || true
cp -n skillopt/runs/v1/test_seed.jsonl         "$MS/seed_r1.jsonl"      2>/dev/null || true
cp -n skillopt/runs/v1/test_optimized.jsonl    "$MS/optimized_r1.jsonl" 2>/dev/null || true

run_one () {  # $1=arm  $2=run_idx  $3=skill flag(s) (may be empty)
  local arm=$1 idx=$2 skill=$3
  local out="$MS/${arm}_r${idx}.jsonl"
  if [ -f "$out" ] && [ "$(wc -l < "$out")" -eq 84 ]; then
    echo "SKIP ${arm}_r${idx} (already 84 lines)" | tee -a "$LOG"; return
  fi
  echo "RUN  ${arm}_r${idx} start $(date -Is)" | tee -a "$LOG"
  rm -f "$out"
  # shellcheck disable=SC2086
  timeout -s INT 5400 $PY eval/run.py $COMMON $skill --out "$out" >> "$LOG" 2>&1
  git checkout -- eval/tasks/ 2>/dev/null || true   # force-clean between runs (safety net)
  local n=0; [ -f "$out" ] && n=$(wc -l < "$out")
  echo "DONE ${arm}_r${idx} -> ${n} lines $(date -Is)" | tee -a "$LOG"
}

rm -f "$MS/.multiseed_DONE"
echo "=== MULTISEED start $(date -Is) (target 5/arm) ===" | tee -a "$LOG"
for i in 1 2 3 4 5; do run_one empty     "$i" ""; done
for i in 1 2 3 4 5; do run_one seed      "$i" "--skill-path skills/seed_skill.md"; done
for i in 1 2 3 4 5; do run_one optimized "$i" "--skill-path skillopt/runs/v1/best_skill.md"; done

echo "=== line counts ===" | tee -a "$LOG"
for f in "$MS"/*.jsonl; do echo "$(basename "$f"): $(wc -l < "$f") lines" | tee -a "$LOG"; done
echo "=== eval/tasks clean? ===" | tee -a "$LOG"
git status --porcelain eval/tasks/ | head | tee -a "$LOG"
echo "=== MULTISEED ALL DONE $(date -Is) ===" | tee -a "$LOG"
touch "$MS/.multiseed_DONE"
