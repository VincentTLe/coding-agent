"""
eval/run.py — Run the coding agent against every task in eval/tasks/.

For each subdirectory in eval/tasks/, this script:
  1. Reads task.md for the goal description.
  2. Points the agent at that subdirectory as its workspace.
  3. Runs the agent.
  4. After the agent finishes, runs `pytest` to score pass/fail.
  5. Prints a summary table at the end.

Run from the repo root:
    cd ~/code/coding-agent && source .venv/bin/activate
    python eval/run.py                 # all tasks
    python eval/run.py 01_strings      # one task by directory name

The agent's verbose log appears inline. The final summary is the eval result.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Make `from src.agent import run_agent` work when running from anywhere.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.agent import run_agent  # noqa: E402
from src.tools import set_workspace  # noqa: E402


TASKS_DIR = ROOT / "eval" / "tasks"


def read_goal(task_dir: Path) -> str:
    """Pull the goal line from task.md (first non-heading non-empty line under '## Goal')."""
    md = (task_dir / "task.md").read_text()
    lines = md.splitlines()
    in_goal = False
    for line in lines:
        if line.startswith("## Goal"):
            in_goal = True
            continue
        if in_goal:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                return stripped
    # Fallback: use directory name as a generic goal.
    return f"Fix all failing tests in eval/tasks/{task_dir.name}/."


def run_pytest(task_dir: Path) -> tuple[bool, str]:
    """Return (passed, output). passed is True iff exit code == 0."""
    result = subprocess.run(
        ["pytest", "--tb=short"],
        cwd=task_dir,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return result.returncode == 0, result.stdout + result.stderr


def run_one(task_dir: Path) -> dict:
    """Run the agent on one task, then evaluate. Return a result dict."""
    print(f"\n{'#' * 70}")
    print(f"# TASK: {task_dir.name}")
    print(f"{'#' * 70}\n")

    set_workspace(task_dir)
    goal = read_goal(task_dir)
    print(f"GOAL: {goal}\n")

    try:
        run_agent(goal, max_iters=20)
    except Exception as e:
        # Don't crash the whole eval if one task errors.
        print(f"AGENT CRASHED: {e}")
        return {"task": task_dir.name, "passed": False, "note": f"agent crash: {e}"}

    passed, output = run_pytest(task_dir)
    print(f"\n--- pytest result for {task_dir.name} ---")
    print(output[-500:])  # tail only, to keep terminal readable
    return {"task": task_dir.name, "passed": passed}


def main() -> int:
    if not TASKS_DIR.exists():
        print(f"No tasks dir at {TASKS_DIR}")
        return 1

    # Either run all tasks, or one named on the command line.
    if len(sys.argv) > 1:
        targets = [TASKS_DIR / sys.argv[1]]
    else:
        targets = sorted([p for p in TASKS_DIR.iterdir() if p.is_dir()])

    results = [run_one(p) for p in targets]

    # Summary at the end — what graders look at.
    print(f"\n\n{'=' * 60}")
    print("EVAL SUMMARY")
    print(f"{'=' * 60}")
    for r in results:
        mark = "PASS" if r["passed"] else "FAIL"
        note = f"  ({r['note']})" if r.get("note") else ""
        print(f"  [{mark}] {r['task']}{note}")
    passed = sum(1 for r in results if r["passed"])
    print(f"\n  TOTAL: {passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
