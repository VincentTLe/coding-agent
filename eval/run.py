"""
eval/run.py — Run the coding agent against tasks in eval/tasks/ and score it.

Trước đây: chạy tuần tự 3 task, in summary, không lưu gì. Giờ harness này scale
lên 500+ task:
  - chạy SONG SONG qua process pool (--jobs N),
  - lưu kết quả TĂNG DẦN ra JSONL (--resume tiếp tục được sau khi gián đoạn),
  - chấm pass-rate theo từng category/difficulty,
  - và GIẤU file test khỏi agent trong lúc nó làm việc (chỉ trả lại để chấm)
    → điểm số trung thực, agent không thể đọc test rồi hard-code đáp án.

Chạy từ repo root (cần vLLM server đang chạy — scripts/start_vllm.sh):
    cd ~/code/coding-agent && source .venv/bin/activate
    python eval/run.py                                  # tất cả task, 1 process
    python eval/run.py --jobs 8                          # 8 agent song song
    python eval/run.py --filter bench/he_0 --jobs 4      # chỉ task khớp filter
    python eval/run.py --filter difficulty=hard          # lọc theo metadata
    python eval/run.py --resume --out eval/results/full_run.jsonl
    python eval/run.py 01_strings                        # 1 task (tương thích cũ)

VÌ SAO PROCESS CHỨ KHÔNG THREAD: src/tools.py giữ WORKSPACE là biến GLOBAL của
module. Hai thread chạy 2 task sẽ tranh nhau global này → ghi nhầm workspace.
Mỗi process có bản global riêng → cô lập tuyệt đối, không phải sửa tools.py.
Dùng start method "spawn" để mỗi worker re-import sạch (OpenAI client riêng,
tránh chia sẻ socket khi fork).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from fnmatch import fnmatch
from multiprocessing import get_context
from pathlib import Path

# Make `from src.agent import run_agent` work when running from anywhere.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.agent import run_agent  # noqa: E402


TASKS_DIR = ROOT / "eval" / "tasks"
RESULTS_DIR = ROOT / "eval" / "results"


# ---------------------------------------------------------------------------
# ĐỌC METADATA TỪ task.md  (Goal / Category / Difficulty)
# ---------------------------------------------------------------------------

def read_section(task_dir: Path, heading: str, default: str = "") -> str:
    """Trả về text dưới '## <heading>' cho tới heading '##' kế tiếp.

    Tổng quát hoá read_goal cũ: dùng chung để đọc Goal / Category / Difficulty.
    """
    md_path = task_dir / "task.md"
    if not md_path.exists():
        return default
    lines: list[str] = []
    in_section = False
    for line in md_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("## ") and line[3:].strip().lower() == heading.lower():
            in_section = True
            continue
        if in_section:
            if line.startswith("##"):  # heading kế tiếp = hết section
                break
            lines.append(line)
    text = "\n".join(lines).strip()
    return text if text else default


def read_goal(task_dir: Path) -> str:
    """Mô tả nhiệm vụ cho agent (toàn bộ phần dưới '## Goal')."""
    goal = read_section(task_dir, "Goal")
    if goal:
        return goal
    return f"Fix all failing tests in eval/tasks/{task_dir.name}/."


def read_meta(task_dir: Path) -> tuple[str, str]:
    """(category, difficulty) — để gộp pass-rate theo nhóm. Default nếu task.md thiếu."""
    cat = read_section(task_dir, "Category", "uncategorized")
    dif = read_section(task_dir, "Difficulty", "unknown")
    cat = cat.splitlines()[0].strip().lower() if cat else "uncategorized"
    dif = dif.splitlines()[0].strip().lower() if dif else "unknown"
    return cat or "uncategorized", dif or "unknown"


def read_hide_tests(task_dir: Path) -> bool:
    """Có GIẤU file test khỏi agent không?
    '## Tests: hidden' → giấu (đo khả năng implement từ SPEC, chống agent đọc test
    rồi hard-code đáp án). MẶC ĐỊNH KHÔNG giấu → task kiểu debug/sửa-test-fail giữ
    nguyên workflow dùng pytest làm feedback (chính là khả năng 'agent tự verify'
    mà ta muốn chứng minh). Converter set 'hidden' cho mọi benchmark task.
    """
    return read_section(task_dir, "Tests", "visible").strip().lower().startswith("hidden")


# ---------------------------------------------------------------------------
# DISCOVERY — tìm mọi task dir (đệ quy), bỏ qua dir bắt đầu bằng _ hoặc .
# ---------------------------------------------------------------------------

def discover_tasks(root: Path) -> list[Path]:
    """Task = thư mục chứa task.md. Đệ quy để bắt cả bench/he_000, curated/...,
    lẫn 01_strings (cấu trúc cũ). Bỏ qua dir có thành phần bắt đầu bằng '_'
    (quarantine) hoặc '.' (cache).
    """
    out: list[Path] = []
    for md in sorted(root.rglob("task.md")):
        d = md.parent
        rel = d.relative_to(root)
        if any(part.startswith(("_", ".")) for part in rel.parts):
            continue
        out.append(d)
    return out


def rel_id(task_dir: Path) -> str:
    """ID ổn định cho task = đường dẫn tương đối dưới eval/tasks ('bench/he_000')."""
    return task_dir.relative_to(TASKS_DIR).as_posix()


# ---------------------------------------------------------------------------
# SNAPSHOT / RESTORE / PYTEST  (giữ nguyên ý nghĩa bản cũ)
# ---------------------------------------------------------------------------

def snapshot_files(task_dir: Path) -> dict[Path, str]:
    """Đọc nội dung mọi file dưới task_dir (ĐỆ QUY) vào RAM trước khi agent chạy.

    LÝ DO: agent sửa file NGAY TRONG task_dir (task_dir CHÍNH LÀ workspace). Không
    restore → lần chạy sau chấm trên code đã fix sẵn (pass rate giả) + git bẩn.
    Snapshot + restore làm eval idempotent.

    ĐỆ QUY (rglob) thay vì chỉ top-level: agent có thể tạo subdir (vd tự lập venv/,
    tests/) — phải nắm được TOÀN BỘ cây để restore xoá sạch chúng về sau, không để
    rò rỉ sang lần chạy sau.
    """
    snap: dict[Path, str] = {}
    for f in task_dir.rglob("*"):
        if f.is_file():
            snap[f] = f.read_text(encoding="utf-8", errors="replace")
    return snap


def remove_extras(task_dir: Path, snap: dict[Path, str]) -> None:
    """Xoá MỌI path dưới task_dir KHÔNG có trong snapshot (file hoặc thư mục).

    Dùng trước khi chấm: pytest chỉ được thấy fixtures GỐC (+ edit của agent lên
    chính các file đó), không thấy file/dir lạ agent tạo ra (đáp án phụ, venv/,
    tests/ rò rỉ...) → tránh pytest collect nhầm test khác hoặc chấm sai.

    KHÔNG động vào nội dung file đã có trong snap — edit của agent lên file gốc
    chính là thứ ta chấm. Chỉ xoá path nằm NGOÀI snapshot. shutil.rmtree cho dir lạ
    (đệ quy), unlink cho file lạ. Bỏ qua path đã biến mất (parent dir bị rmtree
    trước rồi) để khỏi nổ.
    """
    for f in task_dir.rglob("*"):
        if not f.exists():  # cha đã bị rmtree ở vòng trước
            continue
        if f.is_file():
            if f not in snap:
                f.unlink()
        elif f.is_dir():
            # Dir lạ (không chứa file gốc nào) → xoá cả cây. Dir vẫn chứa file
            # snapshot sẽ được giữ; file lạ bên trong nó được nhánh is_file() ở trên dọn.
            if not any(s == f or f in s.parents for s in snap):
                shutil.rmtree(f, ignore_errors=True)


def restore_files(task_dir: Path, snap: dict[Path, str]) -> None:
    """Khôi phục fixtures về trạng thái gốc + xoá MỌI path lạ agent tạo ra (ĐỆ QUY).

    Ghi lại nội dung gốc cho từng file trong snap (parent có thể đã bị xoá → tạo lại),
    rồi xoá mọi file/dir dưới task_dir không thuộc snapshot. Đệ quy (rglob) để dọn
    cả subdir rò rỉ như venv/ hay tests/ — bản cũ chỉ xử lý top-level nên các thư mục
    này còn sót, làm bẩn lần chạy sau. Đây là lưới an toàn cuối trong `finally`.
    """
    for f, content in snap.items():
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content, encoding="utf-8")
    remove_extras(task_dir, snap)


def run_pytest(task_dir: Path) -> tuple[bool, str]:
    """Return (passed, output). passed True iff exit code == 0.

    `sys.executable -m pytest` để chắc chắn dùng pytest của venv đang chạy
    (không phụ thuộc PATH). cwd=task_dir → pytest auto-collect test_*.py và
    import source bằng tên trần.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--tb=short", "-p", "no:cacheprovider"],
            cwd=task_dir,
            capture_output=True,
            text=True,
            timeout=60,
            # PYTHONDONTWRITEBYTECODE: KHÔNG ghi .pyc. Khi validate ta ghi đè cùng 1
            # file (stub→reference) rồi chạy lại; nếu .pyc cũ còn đó và mtime trùng
            # giây, Python có thể nạp BYTECODE CŨ → kết quả sai (vd stub "pass" nhầm
            # vì chạy lại bytecode của reference). Tắt .pyc → mỗi import compile lại
            # từ source, luôn đúng. `-p no:cacheprovider`: khỏi rải .pytest_cache.
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
    except subprocess.TimeoutExpired:
        return False, "ERROR: pytest timed out after 60s"
    return result.returncode == 0, result.stdout + result.stderr


# ---------------------------------------------------------------------------
# 1 ĐƠN VỊ CÔNG VIỆC — chạy trong worker process (phải ở module level để pickle)
# ---------------------------------------------------------------------------

def evaluate_task(payload: tuple) -> dict:
    """Chạy agent trên 1 task rồi chấm điểm. Trả về result dict.

    Các bước (mọi thứ bọc trong finally để fixtures luôn được khôi phục):
      1. snapshot fixtures.
      2. GIẤU file test (xoá khỏi workspace) → agent không thể đọc test để gian lận.
      3. chạy agent (stdout/stderr redirect ra log riêng cho gọn terminal).
      4. trả file test lại → chấm bằng pytest độc lập.
      5. restore fixtures.
    """
    task_path, max_iters, time_budget, repeat_idx, log_dir, temperature = payload
    task_dir = Path(task_path)
    tid = rel_id(task_dir)
    category, difficulty = read_meta(task_dir)
    goal = read_goal(task_dir)

    # Tắt log INFO (HTTP request spam của openai/httpx) trong worker → terminal sạch.
    logging.getLogger().setLevel(logging.WARNING)

    snap = snapshot_files(task_dir)
    # GIẤU TEST (chỉ khi task.md ghi '## Tests: hidden'): với task implement-từ-spec
    # (benchmark), nếu để nguyên test_*.py trong workspace agent có thể đọc rồi
    # hard-code đáp án → điểm ảo. Cất bytes, xoá lúc agent chạy, trả lại đúng trước
    # khi pytest chấm. Spec nằm ở task.md (+ ví dụ trong docstring) nên giấu test
    # không làm agent thiếu thông tin. Task debug/sửa-test (mặc định 'visible')
    # KHÔNG giấu — agent cần chạy pytest thấy lỗi để sửa.
    hide = read_hide_tests(task_dir)
    hidden_tests = ({f: c for f, c in snap.items()
                     if f.name.startswith("test_") and f.suffix == ".py"}
                    if hide else {})

    finish_reason = "agent_crash"
    iters_used = 0
    passed = False
    output = ""
    log_path = Path(log_dir) / f"{tid.replace('/', '__')}.r{repeat_idx}.log"
    t0 = time.monotonic()
    try:
        with open(log_path, "w", encoding="utf-8") as lf, redirect_stdout(lf), redirect_stderr(lf):
            for f in hidden_tests:
                if f.exists():
                    f.unlink()
            try:
                res = run_agent(goal, workspace=task_dir, max_iters=max_iters,
                                time_budget_s=time_budget, temperature=temperature)
                finish_reason = res.get("finish_reason", "unknown")
                iters_used = int(res.get("iters_used", 0))
            except Exception as e:  # noqa: BLE001  (1 task lỗi không được giết cả run)
                finish_reason = "agent_crash"
                print(f"AGENT CRASHED: {e!r}")
            for f, content in hidden_tests.items():  # trả test lại để chấm
                f.write_text(content, encoding="utf-8")
        # Trước khi chấm: dọn mọi path lạ (file/dir agent tạo, vd lời giải phụ hay
        # venv/ rò rỉ) → pytest chỉ collect đúng test gốc + edit của agent lên file gốc.
        # Test ẩn vừa được trả lại ở trên đã nằm trong snap nên remove_extras GIỮ chúng.
        remove_extras(task_dir, snap)
        passed, output = run_pytest(task_dir)
    finally:
        restore_files(task_dir, snap)

    return {
        "task": tid,
        "category": category,
        "difficulty": difficulty,
        "passed": bool(passed),
        "iters_used": iters_used,
        "finish_reason": finish_reason,
        "duration_s": round(time.monotonic() - t0, 1),
        "pytest_tail": output[-1000:],
        "repeat_idx": repeat_idx,
    }


# ---------------------------------------------------------------------------
# LỌC TASK + RESUME
# ---------------------------------------------------------------------------

def select_tasks(all_tasks: list[Path], filters: list[str]) -> list[Path]:
    """Lọc theo --filter. Mỗi filter là 'key=value' (so metadata: category/
    difficulty/task) hoặc glob/substring trên task id. Chọn task nếu khớp TẤT CẢ.
    """
    if not filters:
        return all_tasks
    selected = []
    for t in all_tasks:
        tid = rel_id(t)
        cat, dif = read_meta(t)
        meta = {"category": cat, "difficulty": dif, "task": tid}
        ok = True
        for flt in filters:
            if "=" in flt:
                k, v = flt.split("=", 1)
                if meta.get(k.strip().lower(), "") != v.strip().lower():
                    ok = False
                    break
            elif any(c in flt for c in "*?[]"):
                if not fnmatch(tid, flt):
                    ok = False
                    break
            elif flt not in tid:
                ok = False
                break
        if ok:
            selected.append(t)
    return selected


def load_done(out_path: Path) -> tuple[set, list]:
    """Đọc JSONL đã có → (set (task,repeat) đã chạy, list result cũ) cho --resume."""
    done: set = set()
    prior: list = []
    if out_path.exists():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            done.add((r["task"], r.get("repeat_idx", 0)))
            prior.append(r)
    return done, prior


# ---------------------------------------------------------------------------
# TỔNG HỢP KẾT QUẢ
# ---------------------------------------------------------------------------

def _group_rate(results: list, key: str) -> dict:
    agg: dict = defaultdict(lambda: [0, 0])  # key -> [passed, total]
    for r in results:
        g = agg[r.get(key, "?")]
        g[1] += 1
        if r["passed"]:
            g[0] += 1
    return agg


def write_summary(results: list, md_path: Path, ts: str) -> str:
    """Sinh báo cáo markdown: tổng quan + pass@1/pass@any + theo category/difficulty."""
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    L = [f"# Eval results — {ts}", ""]
    L.append(f"**Overall:** {passed}/{total} runs passed "
             f"({100 * passed / max(total, 1):.1f}%).")
    L.append("")

    # Gộp các lần repeat của cùng 1 task: pass@1 (lần đầu) vs pass@any (bất kỳ lần nào).
    by_task: dict = defaultdict(list)
    for r in results:
        by_task[r["task"]].append(r)
    n = len(by_task)
    pass1 = sum(1 for rs in by_task.values()
                if any(x["passed"] for x in rs if x["repeat_idx"] == 0))
    passk = sum(1 for rs in by_task.values() if any(x["passed"] for x in rs))
    L.append(f"**Tasks:** {n}  |  pass@1: {pass1}/{n} ({100 * pass1 / max(n, 1):.1f}%)"
             f"  |  pass@any: {passk}/{n} ({100 * passk / max(n, 1):.1f}%)")
    L.append("")

    for key, title in [("category", "By category"), ("difficulty", "By difficulty")]:
        L += [f"## {title}", "", f"| {key} | pass | total | rate |", "|---|---|---|---|"]
        agg = _group_rate(results, key)
        for g in sorted(agg):
            p, t = agg[g]
            L.append(f"| {g} | {p} | {t} | {100 * p / max(t, 1):.1f}% |")
        L.append("")

    fr: dict = defaultdict(int)
    for r in results:
        fr[r.get("finish_reason", "?")] += 1
    L += ["## Finish reasons", ""]
    L += [f"- {k}: {fr[k]}" for k in sorted(fr)]
    L.append("")

    md = "\n".join(L)
    md_path.write_text(md, encoding="utf-8")
    return md


def pass_rate(results: list) -> float:
    return sum(1 for r in results if r["passed"]) / len(results) if results else 0.0


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Run the coding agent over eval tasks.")
    ap.add_argument("filter_pos", nargs="?", help="(compat) tên 1 task, vd 01_strings")
    ap.add_argument("--jobs", "-j", type=int, default=1, help="số agent chạy song song")
    ap.add_argument("--max-iters", type=int, default=20, help="trần số turn mỗi agent")
    ap.add_argument("--filter", action="append", default=[],
                    help="key=value (category/difficulty/task) hoặc glob/substring; lặp được")
    ap.add_argument("--repeats", type=int, default=1, help="chạy mỗi task K lần (pass@k)")
    ap.add_argument("--resume", action="store_true",
                    help="bỏ qua (task,repeat) đã có trong --out")
    ap.add_argument("--agent-timeout", type=float, default=None,
                    help="trần wall-clock mỗi task, giây (None = không giới hạn)")
    ap.add_argument("--temperature", type=float, default=None,
                    help="sampling temperature (0 = greedy/deterministic — khuyến nghị cho eval: "
                         "tool-call ổn định + kết quả tái lập)")
    ap.add_argument("--out", type=Path, default=None, help="file JSONL kết quả")
    ap.add_argument("--min-pass-rate", type=float, default=None,
                    help="nếu đặt: exit !=0 khi pass-rate dưới ngưỡng (CI gate)")
    args = ap.parse_args()

    if not TASKS_DIR.exists():
        print(f"No tasks dir at {TASKS_DIR}")
        return 2

    filters = list(args.filter)
    if args.filter_pos:
        filters.append(args.filter_pos)

    all_tasks = discover_tasks(TASKS_DIR)
    tasks = select_tasks(all_tasks, filters)
    if not tasks:
        print(f"No tasks matched (discovered {len(all_tasks)} total, filters={filters})")
        return 2

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = args.out or (RESULTS_DIR / f"run-{ts}.jsonl")
    log_dir = RESULTS_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    done: set = set()
    results: list = []
    if args.resume:
        done, results = load_done(out_path)
        print(f"Resume: {len(done)} (task,repeat) already done — skipping those.")

    # Danh sách công việc: mỗi (task, repeat_idx) chưa có trong `done`.
    work = []
    for t in tasks:
        tid = rel_id(t)
        for r in range(args.repeats):
            if (tid, r) not in done:
                work.append((str(t), args.max_iters, args.agent_timeout, r, str(log_dir),
                             args.temperature))

    total = len(work)
    print(f"Discovered {len(all_tasks)} tasks; selected {len(tasks)}; "
          f"{total} runs to do (repeats={args.repeats}, jobs={args.jobs}).")
    print(f"Results → {out_path}   (per-task logs → {log_dir})\n")

    if total:
        ctx = get_context("spawn")  # mỗi worker re-import → OpenAI client riêng (an toàn fork).
        n_done = 0
        # Kết quả ghi NGAY khi mỗi task xong → crash giữa chừng vẫn còn file hợp lệ,
        # --resume đọc lại được. Chế độ "a" khi --resume (nối tiếp file cũ đã load ở
        # load_done); ngược lại "w" để GHI ĐÈ — tránh âm thầm nối kết quả run trước
        # vào file mặc định cùng tên (làm summary đếm trùng).
        mode = "a" if args.resume else "w"
        with open(out_path, mode, encoding="utf-8") as out_f, \
                ProcessPoolExecutor(max_workers=args.jobs, mp_context=ctx) as ex:
            futs = {ex.submit(evaluate_task, w): w for w in work}
            for fut in as_completed(futs):
                try:
                    r = fut.result()
                except Exception as e:  # noqa: BLE001
                    w = futs[fut]
                    r = {"task": rel_id(Path(w[0])), "category": "?", "difficulty": "?",
                         "passed": False, "iters_used": 0, "finish_reason": "worker_error",
                         "duration_s": 0.0, "pytest_tail": repr(e), "repeat_idx": w[3]}
                results.append(r)
                out_f.write(json.dumps(r) + "\n")
                out_f.flush()
                n_done += 1
                mark = "PASS" if r["passed"] else "FAIL"
                print(f"[{mark}] {r['task']} r{r['repeat_idx']} "
                      f"({r['finish_reason']}, {r['iters_used']}it, {r['duration_s']}s) "
                      f"[{n_done}/{total}]")
    else:
        print("Nothing to run (all selected runs already in --out).")

    summary = write_summary(results, out_path.with_suffix(".md"), ts)
    print("\n" + summary)
    print(f"Full results: {out_path}")
    print("Reminder: stop the vLLM tmux pane when done "
          "(Ctrl-C in `tmux attach -t vllm`) — it's a shared GPU.")

    if args.min_pass_rate is not None:
        return 0 if pass_rate(results) >= args.min_pass_rate else 1
    return 0  # hoàn thành = thành công; pass-rate là tín hiệu chất lượng, không phải exit code


if __name__ == "__main__":
    sys.exit(main())
