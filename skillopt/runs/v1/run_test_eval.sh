#!/usr/bin/env bash
# 3-arm SkillOpt test eval — empty / seed / optimized on the locked 84-task test split.
# Sequential by design: eval/run.py hides+restores files inside eval/tasks/ in place,
# so two concurrent eval processes would race on that shared state and corrupt scoring.
# Each arm uses --resume so a mid-run kill is recoverable. Config mirrors the training
# rollouts EXACTLY (--jobs 8 --temperature 0 --max-iters 20 --agent-timeout 420) so the
# optimized skill is measured under the same conditions it was optimized under.
set -uo pipefail
cd /home/tle/code/coding-agent
PY=.venv/bin/python3
RUN=skillopt/runs/v1
LOG=$RUN/test_eval.log
COMMON="--tasks-file $RUN/test.txt --jobs 8 --temperature 0 --max-iters 20 --agent-timeout 420 --resume"

rm -f "$RUN/.test_eval_DONE"
echo "=== 3-ARM TEST EVAL start $(date -Is) ===" | tee -a "$LOG"

echo "--- ARM 1/3: EMPTY (base prompt, no skill) $(date -Is) ---" | tee -a "$LOG"
$PY eval/run.py $COMMON --out "$RUN/test_empty.jsonl" >> "$LOG" 2>&1
echo "--- ARM 1 done $(date -Is) ---" | tee -a "$LOG"

echo "--- ARM 2/3: SEED (human TDD skill) $(date -Is) ---" | tee -a "$LOG"
$PY eval/run.py $COMMON --skill-path skills/seed_skill.md --out "$RUN/test_seed.jsonl" >> "$LOG" 2>&1
echo "--- ARM 2 done $(date -Is) ---" | tee -a "$LOG"

echo "--- ARM 3/3: OPTIMIZED (gate's best_skill.md) $(date -Is) ---" | tee -a "$LOG"
$PY eval/run.py $COMMON --skill-path "$RUN/best_skill.md" --out "$RUN/test_optimized.jsonl" >> "$LOG" 2>&1
echo "--- ARM 3 done $(date -Is) ---" | tee -a "$LOG"

# Sanity: confirm all three wrote results, and eval/tasks restored clean.
for f in test_empty test_seed test_optimized; do
  n=$(wc -l < "$RUN/$f.jsonl" 2>/dev/null || echo 0)
  echo "RESULT $f.jsonl: $n lines" | tee -a "$LOG"
done
echo "=== ALL 3 ARMS DONE $(date -Is) ===" | tee -a "$LOG"
touch "$RUN/.test_eval_DONE"
