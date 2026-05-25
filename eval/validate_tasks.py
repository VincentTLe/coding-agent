"""
eval/validate_tasks.py — Cổng kiểm tra chất lượng: đảm bảo MỌI task là "thật".

Với mỗi task dir, kiểm 2 tính chất bắt buộc:
  1. Lời giải tham chiếu (eval/solutions/<rel>/*.py) → pytest PASS.
  2. Stub ban đầu (chưa làm)                          → pytest FAIL.
Nếu cả hai đúng → task hợp lệ (có thật, không vacuous). Ngược lại → quarantine
(chuyển sang eval/tasks/_quarantine/, discovery của run.py sẽ tự bỏ qua dir '_').

Lời giải để ở cây SONG SONG eval/solutions/<rel>/ (mirror task dir theo tên file)
nên hỗ trợ cả task nhiều file: validate ghi đè từng file lời giải vào task rồi chạy.

Chạy (CPU-bound, không đụng GPU → cho --jobs cao):
    python eval/validate_tasks.py --jobs 16                 # tất cả task
    python eval/validate_tasks.py --filter bench --jobs 16  # chỉ bench/
    python eval/validate_tasks.py --filter curated --quarantine
"""

from __future__ import annotations

import argparse
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Tái dùng đúng cơ chế chấm/khôi phục của harness chính (cùng đường đi với eval thật).
from eval.run import (  # noqa: E402
    TASKS_DIR,
    discover_tasks,
    rel_id,
    restore_files,
    run_pytest,
    select_tasks,
    snapshot_files,
)

SOLUTIONS_DIR = ROOT / "eval" / "solutions"
QUARANTINE = TASKS_DIR / "_quarantine"


def validate_one(task_path: str) -> dict:
    """Kiểm 1 task: ref PASS và stub FAIL. Trả dict {task, ok, note}."""
    task_dir = Path(task_path)
    rel = rel_id(task_dir)
    sol_dir = SOLUTIONS_DIR / task_dir.relative_to(TASKS_DIR)
    if not sol_dir.is_dir():
        return {"task": rel, "ok": False, "note": "no solution dir"}
    sol_files = list(sol_dir.glob("*.py"))
    if not sol_files:
        return {"task": rel, "ok": False, "note": "empty solution dir"}

    snap = snapshot_files(task_dir)
    try:
        stub_pass, _ = run_pytest(task_dir)            # 1) stub PHẢI fail
        for sf in sol_files:                            # 2) ghi đè lời giải tham chiếu
            (task_dir / sf.name).write_text(sf.read_text(encoding="utf-8"), encoding="utf-8")
        ref_pass, ref_out = run_pytest(task_dir)        #    → PHẢI pass
    finally:
        restore_files(task_dir, snap)                   # luôn trả về stub ban đầu

    ok = ref_pass and not stub_pass
    if ok:
        note = "ok"
    elif not ref_pass:
        note = "BROKEN: reference solution does not pass — " + ref_out.strip().splitlines()[-1][:160] if ref_out.strip() else "BROKEN: reference fails"
    else:
        note = "VACUOUS: stub already passes (tests too weak)"
    return {"task": rel, "ok": ok, "note": note}


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate that every task is real (ref passes, stub fails).")
    ap.add_argument("--filter", action="append", default=[],
                    help="glob/substring trên task id hoặc key=value; lặp được")
    ap.add_argument("--jobs", "-j", type=int, default=8)
    ap.add_argument("--quarantine", action="store_true",
                    help="chuyển task hỏng sang eval/tasks/_quarantine/")
    args = ap.parse_args()

    tasks = select_tasks(discover_tasks(TASKS_DIR), args.filter)
    if not tasks:
        print(f"No tasks matched filters={args.filter}")
        return 2
    print(f"Validating {len(tasks)} tasks with --jobs {args.jobs} ...\n")

    results = []
    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        futs = {ex.submit(validate_one, str(t)): t for t in tasks}
        for fut in as_completed(futs):
            r = fut.result()
            results.append(r)
            if not r["ok"]:
                print(f"[INVALID] {r['task']}: {r['note']}")

    bad = [r for r in results if not r["ok"]]
    good = len(results) - len(bad)
    print(f"\nVALID: {good}/{len(results)}   INVALID: {len(bad)}")

    if bad and args.quarantine:
        QUARANTINE.mkdir(parents=True, exist_ok=True)
        for r in bad:
            src = TASKS_DIR / r["task"]
            dst = QUARANTINE / r["task"].replace("/", "__")
            if src.exists():
                shutil.move(str(src), str(dst))
        print(f"Quarantined {len(bad)} tasks → {QUARANTINE} (discovery skips '_' dirs).")
    elif bad:
        print("Re-run with --quarantine to move the invalid tasks out of the suite.")

    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
