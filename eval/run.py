"""
eval/run.py — Run the coding agent against every task in eval/tasks/.

For each subdirectory in eval/tasks/, this script:
  1. Reads task.md for the goal description.
  2. Points the agent at that subdirectory as its workspace.
  3. Snapshots the task's source files (so the run is repeatable).
  4. Runs the agent.
  5. After the agent finishes, runs `pytest` to score pass/fail.
  6. Restores the snapshot so the fixtures are clean for the next run.
  7. Prints a summary table at the end.

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
    """Lấy TOÀN BỘ phần mô tả dưới mục '## Goal' trong task.md.

    Trước đây chỉ trả về DÒNG đầu tiên — làm hỏng task có goal nhiều dòng
    (vd task 03 mô tả gcd + lcm trên nhiều dòng, agent chỉ nhận được dòng 1).
    Giờ gom mọi dòng từ sau '## Goal' tới heading '##' tiếp theo.
    """
    md = (task_dir / "task.md").read_text(encoding="utf-8")
    goal_lines: list[str] = []
    in_goal = False
    for line in md.splitlines():
        if line.startswith("## Goal"):
            in_goal = True
            continue
        if in_goal:
            # Heading '##' kế tiếp = hết phần Goal → dừng.
            if line.startswith("##"):
                break
            goal_lines.append(line)

    goal = "\n".join(goal_lines).strip()
    if goal:
        return goal
    # Fallback: use directory name as a generic goal.
    return f"Fix all failing tests in eval/tasks/{task_dir.name}/."


def snapshot_files(task_dir: Path) -> dict[Path, str]:
    """Đọc nội dung mọi file *.py + task.md vào RAM trước khi agent chạy.

    LÝ DO (đây là bug nghiêm trọng nếu thiếu): agent sửa file NGAY TRONG
    task_dir (task_dir CHÍNH LÀ workspace của agent). Nếu không restore,
    lần `python eval/run.py` thứ 2 sẽ chấm điểm trên code ĐÃ được fix sẵn
    → pass rate giả, fixtures bẩn trong git. Snapshot + restore làm eval
    idempotent: chạy bao nhiêu lần kết quả cũng như nhau.

    Chỉ snapshot source files, KHÔNG đụng tới thư mục con như __pycache__/
    (pytest tự tạo lại, không phải fixture cần giữ).
    """
    snap: dict[Path, str] = {}
    for f in task_dir.iterdir():
        if f.is_file():
            # errors="replace": phòng file có byte lạ — không cho snapshot crash eval.
            snap[f] = f.read_text(encoding="utf-8", errors="replace")
    return snap


def restore_files(task_dir: Path, snap: dict[Path, str]) -> None:
    """Khôi phục fixtures về đúng trạng thái trước khi agent chạy.

    - File nào agent SỬA → ghi lại nội dung gốc.
    - File nào agent TẠO MỚI (không có trong snapshot) → xóa đi, nếu không
      lần sau pytest có thể nhặt phải test rác do agent đẻ ra.
    """
    for f, content in snap.items():
        f.write_text(content, encoding="utf-8")
    # Dọn file lạ agent tạo thêm (vd test tự sinh) để task_dir sạch như cũ.
    for f in task_dir.iterdir():
        if f.is_file() and f not in snap:
            f.unlink()


def run_pytest(task_dir: Path) -> tuple[bool, str]:
    """Return (passed, output). passed is True iff exit code == 0."""
    # `sys.executable -m pytest` thay vì bare `pytest`: chắc chắn dùng đúng
    # pytest của venv đang chạy, không phụ thuộc PATH (bare `pytest` có thể
    # trỏ vào interpreter khác hoặc không tồn tại).
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--tb=short"],
            cwd=task_dir,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        # pytest treo (vd agent viết test có infinite loop). KHÔNG để
        # TimeoutExpired bubble lên crash cả eval — chấm task này là FAIL.
        return False, "ERROR: pytest timed out after 60s"
    return result.returncode == 0, result.stdout + result.stderr


def run_one(task_dir: Path) -> dict:
    """Run the agent on one task, then evaluate. Return a result dict."""
    print(f"\n{'#' * 70}")
    print(f"# TASK: {task_dir.name}")
    print(f"{'#' * 70}\n")

    set_workspace(task_dir)
    goal = read_goal(task_dir)
    print(f"GOAL: {goal}\n")

    # Chụp ảnh fixtures TRƯỚC khi agent đụng vào. `finally` bên dưới đảm bảo
    # luôn restore — kể cả khi agent crash hay pytest treo.
    snap = snapshot_files(task_dir)
    try:
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
    finally:
        # Trả fixtures về nguyên trạng → eval lặp lại được, git không bẩn.
        restore_files(task_dir, snap)


def main() -> int:
    if not TASKS_DIR.exists():
        print(f"No tasks dir at {TASKS_DIR}")
        return 1

    # Either run all tasks, or one named on the command line.
    if len(sys.argv) > 1:
        target = TASKS_DIR / sys.argv[1]
        # Validate trước khi chạy: nếu tên task sai, báo lỗi rõ ràng thay vì
        # để read_goal() ném FileNotFoundError giữa chừng (traceback khó hiểu).
        if not target.is_dir():
            print(f"No such task: {sys.argv[1]} (looked in {TASKS_DIR})")
            return 1
        targets = [target]
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
