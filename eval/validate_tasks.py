"""
eval/validate_tasks.py — Cổng kiểm tra chất lượng: đảm bảo MỌI task là "thật".

Với mỗi task dir, kiểm 2 tính chất bắt buộc:
  1. Lời giải tham chiếu (eval/solutions/<rel>/*.py) → pytest PASS.
  2. Stub ban đầu (chưa làm)                          → pytest FAIL.
Nếu cả hai đúng → task hợp lệ (có thật, không vacuous). Ngược lại → quarantine
(chuyển sang eval/tasks/_quarantine/, discovery của run.py sẽ tự bỏ qua dir '_').

MỤC ĐÍCH CỦA BƯỚC VALIDATE NÀY:
  Khi ta viết một task mới cho eval, có hai lỗi thường gặp:
  Lỗi 1 — Task "gãy" (broken): Lời giải đúng (reference solution) vẫn không pass được test.
           Có thể do test viết sai, import path sai, hoặc lời giải thiếu.
           → Nếu không phát hiện, eval sẽ cho điểm thấp giả tạo (agent đúng mà vẫn bị chấm sai).
  Lỗi 2 — Task "rỗng" (vacuous): Stub ban đầu (code chưa làm gì, chỉ `pass` hoặc `return None`)
           đã pass được test. Có thể do test không đủ chặt (test trivial cases, không test gì).
           → Nếu không phát hiện, agent sẽ "pass" mà không cần làm gì, điểm cao nhưng vô nghĩa.
  Chỉ khi stub FAIL VÀ reference PASS → task mới "thật" và xứng đáng vào bộ eval.

Lời giải để ở cây SONG SONG eval/solutions/<rel>/ (mirror task dir theo tên file)
nên hỗ trợ cả task nhiều file: validate ghi đè từng file lời giải vào task rồi chạy.

Chạy (CPU-bound, không đụng GPU → cho --jobs cao):
    python eval/validate_tasks.py --jobs 16                 # tất cả task
    python eval/validate_tasks.py --filter bench --jobs 16  # chỉ bench/
    python eval/validate_tasks.py --filter curated --quarantine
"""

# `from __future__ import annotations` — kích hoạt tính năng type hint hiện đại.
# Xem giải thích chi tiết trong run.py.
from __future__ import annotations

# `import argparse` — thư viện đọc tham số dòng lệnh (--filter, --jobs, --quarantine...).
import argparse

# `import shutil` — thư viện thao tác file/thư mục cấp cao.
# Ở đây dùng shutil.move() để di chuyển task hỏng vào thư mục quarantine.
#
# shutil.move(src, dst): di chuyển file hoặc thư mục từ src đến dst.
# Giống lệnh `mv` trong terminal Unix. Khác os.rename() ở chỗ hoạt động được khi
# src và dst nằm trên các ổ đĩa khác nhau (os.rename() chỉ rename trong cùng filesystem).
import shutil

# `import sys` — trình thông dịch Python: sys.path (đường tìm module), sys.exit() (thoát).
import sys

# `from concurrent.futures import ProcessPoolExecutor, as_completed`
# — xử lý song song qua process pool. Xem giải thích đầy đủ trong run.py.
# Validate dùng process pool vì pytest là CPU-bound (không cần GPU) → tận dụng nhiều core.
from concurrent.futures import ProcessPoolExecutor, as_completed

# `from pathlib import Path` — xử lý đường dẫn file/thư mục theo kiểu hướng đối tượng.
from pathlib import Path

# Thêm thư mục gốc repo vào sys.path để có thể import eval.run và src.agent.
# Path(__file__).resolve() — đường dẫn tuyệt đối của file này (validate_tasks.py).
# .parent.parent — lên 2 cấp: eval/ → repo_root/.
ROOT = Path(__file__).resolve().parent.parent

# Chèn ROOT vào đầu danh sách tìm kiếm module (ưu tiên cao nhất).
sys.path.insert(0, str(ROOT))

# Tái dùng đúng cơ chế chấm/khôi phục của harness chính (cùng đường đi với eval thật).
# `from eval.run import (...)` — import nhiều tên cùng lúc từ module eval.run.
# Dùng lại hàm của run.py thay vì viết lại → đảm bảo validate dùng ĐÚNG logic chấm,
# không phải logic viết tay có thể khác với eval thật.
from eval.run import (  # noqa: E402
    TASKS_DIR,       # hằng số đường dẫn thư mục tasks
    discover_tasks,  # hàm tìm tất cả task
    rel_id,          # hàm lấy ID tương đối của task
    restore_files,   # hàm khôi phục file về trạng thái ban đầu
    run_pytest,      # hàm chạy pytest và trả về (passed, output)
    select_tasks,    # hàm lọc task theo filter
    snapshot_files,  # hàm chụp ảnh nội dung file vào RAM
)

# Thư mục chứa lời giải tham chiếu (reference solutions) — cây song song với tasks/.
# Ví dụ: task tại eval/tasks/bench/he_000/ → lời giải tại eval/solutions/bench/he_000/.
SOLUTIONS_DIR = ROOT / "eval" / "solutions"

# Thư mục "quarantine" — nơi cô lập các task hỏng.
# Tên bắt đầu bằng _ nên discover_tasks() trong run.py sẽ TỰ ĐỘNG BỎ QUA.
QUARANTINE = TASKS_DIR / "_quarantine"


def validate_one(task_path: str) -> dict:
    """Kiểm 1 task: ref PASS và stub FAIL. Trả dict {task, ok, note}.

    Quy trình:
      1. Chạy pytest với code stub gốc → phải FAIL (nếu pass thì task "vacuous"/rỗng).
      2. Ghi đè file lời giải tham chiếu vào thư mục task.
      3. Chạy pytest lại → phải PASS (nếu fail thì lời giải "broken"/hỏng).
      4. LUÔN khôi phục về stub gốc (trong finally).
    """
    # Chuyển chuỗi đường dẫn thành Path object.
    # (ProcessPoolExecutor gửi qua pickle → dùng str cho an toàn, chuyển lại ở đây.)
    task_dir = Path(task_path)

    # Lấy ID tương đối của task (ví dụ "bench/he_000").
    rel = rel_id(task_dir)

    # Tính đường dẫn thư mục lời giải tương ứng với task này.
    # `task_dir.relative_to(TASKS_DIR)` — phần đường dẫn sau eval/tasks/.
    # `SOLUTIONS_DIR / ...` — nối vào eval/solutions/.
    # Ví dụ: task_dir = eval/tasks/bench/he_000 → sol_dir = eval/solutions/bench/he_000.
    sol_dir = SOLUTIONS_DIR / task_dir.relative_to(TASKS_DIR)

    # `sol_dir.is_dir()` — kiểm tra thư mục lời giải có tồn tại không.
    if not sol_dir.is_dir():
        # Trả về dict kết quả với ok=False và note giải thích lý do.
        return {"task": rel, "ok": False, "note": "no solution dir"}

    # `list(sol_dir.glob("*.py"))` — tìm tất cả file .py trong thư mục lời giải.
    # glob("*.py"): glob pattern — * khớp mọi ký tự, .py là phần mở rộng.
    # Path.glob() trả về generator (lazily evaluated iterator), list() chuyển thành list.
    sol_files = list(sol_dir.glob("*.py"))
    if not sol_files:
        return {"task": rel, "ok": False, "note": "empty solution dir"}

    # Chụp ảnh toàn bộ file gốc (stub) vào RAM trước khi làm bất cứ điều gì.
    # Quan trọng: sau validate, task_dir phải trở về đúng stub gốc để lần validate
    # sau (hoặc eval thật) không bị ảnh hưởng.
    snap = snapshot_files(task_dir)

    # `try: ... finally:` — đảm bảo restore_files() luôn được gọi.
    # Dù validate thành công hay thất bại, stub gốc luôn được khôi phục.
    try:
        # BƯỚC 1: Chạy pytest với code STUB (trạng thái ban đầu, chưa giải).
        # run_pytest trả về (bool_passed, str_output).
        # Ký tự _ là tên biến "không quan tâm" — bỏ qua output ở bước này.
        stub_pass, _ = run_pytest(task_dir)            # 1) stub PHẢI fail

        # BƯỚC 2: Ghi đè file lời giải tham chiếu vào thư mục task.
        for sf in sol_files:                            # 2) ghi đè lời giải tham chiếu
            # `sf.name` — tên file (không có đường dẫn), ví dụ "solution.py".
            # `task_dir / sf.name` — đường dẫn đích: eval/tasks/bench/he_000/solution.py.
            # `sf.read_text(encoding="utf-8")` — đọc nội dung file lời giải.
            # `.write_text(...)` — ghi đè vào file tương ứng trong task_dir.
            (task_dir / sf.name).write_text(sf.read_text(encoding="utf-8"), encoding="utf-8")

        # BƯỚC 3: Chạy pytest với code REFERENCE (lời giải đúng).
        # ref_out giữ output để trích thông báo lỗi nếu fail.
        ref_pass, ref_out = run_pytest(task_dir)        #    → PHẢI pass

    finally:
        # LUÔN khôi phục stub gốc, dù bước trên có lỗi hay không.
        # Nếu không restore: task_dir sẽ chứa reference solution, lần chạy sau sẽ bị chấm nhầm.
        restore_files(task_dir, snap)                   # luôn trả về stub ban đầu

    # `ok = ref_pass and not stub_pass` — task hợp lệ KHI VÀ CHỈ KHI:
    #   ref_pass = True: lời giải tham chiếu pass được test.
    #   not stub_pass = True: stub ban đầu KHÔNG pass (tức là stub fail, đúng như mong muốn).
    # `and` — toán tử logic: cả hai vế phải True thì kết quả mới True.
    ok = ref_pass and not stub_pass

    # TIMEOUT phân biệt với BROKEN: nếu reference fail CHỈ vì pytest hết 60s (máy bận, không
    # phải logic sai) thì KHÔNG được quarantine (xoá vĩnh viễn) task tốt. run_pytest đánh dấu
    # "TIMEOUT" trong output cho trường hợp này.
    timed_out = "TIMEOUT" in (ref_out or "")

    if ok:
        note = "ok"
    elif timed_out:
        note = "TIMEOUT: reference run hit the 60s pytest cap (machine busy?) — NOT quarantined"
    elif not ref_pass:
        # Lời giải tham chiếu không pass → task "broken".
        # `ref_out.strip().splitlines()[-1][:160]` — lấy dòng cuối của output (thường là summary
        # của pytest), cắt còn 160 ký tự để không quá dài.
        # [-1]: index âm — Python đếm từ cuối danh sách, -1 là phần tử cuối cùng.
        # [:160]: slice từ đầu đến ký tự thứ 160.
        # `if ref_out.strip() else "BROKEN: reference fails"` — nếu output rỗng thì dùng fallback.
        note = "BROKEN: reference solution does not pass — " + ref_out.strip().splitlines()[-1][:160] if ref_out.strip() else "BROKEN: reference fails"
    else:
        # stub_pass = True → stub đã pass ngay từ đầu → task "vacuous" (rỗng/vô nghĩa).
        note = "VACUOUS: stub already passes (tests too weak)"

    # Trả về dict kết quả. `timeout` để khâu quarantine bỏ qua (không xoá task chỉ vì chậm).
    return {"task": rel, "ok": ok, "note": note, "timeout": timed_out}


def main() -> int:
    # Tạo argument parser cho validate_tasks.py.
    ap = argparse.ArgumentParser(description="Validate that every task is real (ref passes, stub fails).")

    # --filter: lọc task cần validate (giống run.py).
    # action="append": mỗi --filter thêm 1 giá trị vào list. Có thể dùng nhiều lần.
    ap.add_argument("--filter", action="append", default=[],
                    help="glob/substring trên task id hoặc key=value; lặp được")

    # --jobs: số worker process chạy song song.
    # Validate không dùng GPU → có thể đặt cao (8, 16) để tận dụng nhiều CPU core.
    ap.add_argument("--jobs", "-j", type=int, default=8)

    # --quarantine: nếu có flag này → tự động chuyển task hỏng vào thư mục _quarantine/.
    # action="store_true": không cần giá trị, chỉ cần có flag là True.
    ap.add_argument("--quarantine", action="store_true",
                    help="chuyển task hỏng sang eval/tasks/_quarantine/")

    # `ap.parse_args()` — đọc và phân tích tham số dòng lệnh.
    args = ap.parse_args()

    # Tìm và lọc task.
    # discover_tasks(TASKS_DIR): tìm tất cả task trong eval/tasks/ (đệ quy, bỏ qua _ và .).
    # select_tasks(..., args.filter): lọc theo --filter nếu có.
    tasks = select_tasks(discover_tasks(TASKS_DIR), args.filter)
    if not tasks:
        print(f"No tasks matched filters={args.filter}")
        return 2

    print(f"Validating {len(tasks)} tasks with --jobs {args.jobs} ...\n")

    results = []

    # Tạo process pool để validate song song.
    # `with ProcessPoolExecutor(max_workers=args.jobs) as ex:` — tạo pool N worker.
    # Validate là CPU-bound (chạy pytest) → nhiều worker = nhiều task validate đồng thời.
    # Không cần mp_context="spawn" như run.py vì validate không dùng OpenAI client.
    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        # Gửi tất cả task vào pool.
        # `str(t)` — chuyển Path thành string để pickle an toàn qua process boundary.
        # Dict comprehension {future: task_path}: ánh xạ future → task tương ứng.
        futs = {ex.submit(validate_one, str(t)): t for t in tasks}

        # Lấy kết quả theo thứ tự hoàn thành (không phải thứ tự submit).
        # as_completed(): xem giải thích chi tiết trong run.py.
        for fut in as_completed(futs):
            # `fut.result()` — lấy giá trị trả về của validate_one().
            # Nếu worker ném exception → fut.result() re-raise ở đây.
            # (Trong validate, không bắt exception — nếu crash thì muốn biết.)
            r = fut.result()
            results.append(r)
            # In ra ngay các task không hợp lệ để người dùng thấy sớm.
            if not r["ok"]:
                print(f"[INVALID] {r['task']}: {r['note']}")

    # `[r for r in results if not r["ok"]]` — list comprehension: lọc các task không hợp lệ.
    # Tương đương: bad = []; for r in results: if not r["ok"]: bad.append(r)
    bad = [r for r in results if not r["ok"]]

    # `len(results) - len(bad)` — số task hợp lệ = tổng trừ không hợp lệ.
    good = len(results) - len(bad)
    print(f"\nVALID: {good}/{len(results)}   INVALID: {len(bad)}")

    # Chỉ quarantine task HỎNG THẬT (broken/vacuous), KHÔNG quarantine task chỉ bị TIMEOUT
    # (chạy lâu do máy bận ≠ task sai) — nếu không sẽ xoá dần task tốt khỏi suite.
    quarantinable = [r for r in bad if not r.get("timeout")]
    timed_out = [r for r in bad if r.get("timeout")]
    if timed_out:
        print(f"NOTE: {len(timed_out)} task TIMEOUT (không quarantine) — chạy lại lúc máy rảnh.")
    # Nếu có task hỏng thật VÀ người dùng dùng flag --quarantine → di chuyển task hỏng.
    if quarantinable and args.quarantine:
        # `QUARANTINE.mkdir(parents=True, exist_ok=True)` — tạo thư mục _quarantine/ nếu chưa có.
        QUARANTINE.mkdir(parents=True, exist_ok=True)
        for r in quarantinable:
            # `TASKS_DIR / r["task"]` — đường dẫn tuyệt đối của task hỏng.
            # r["task"] ví dụ: "bench/he_000" → TASKS_DIR / "bench" / "he_000".
            src = TASKS_DIR / r["task"]
            # Tên đích trong _quarantine/: thay / bằng __ để tránh tạo thư mục con.
            # Ví dụ: "bench/he_000" → "_quarantine/bench__he_000".
            dst = QUARANTINE / r["task"].replace("/", "__")
            if src.exists():
                # `shutil.move(str(src), str(dst))` — di chuyển thư mục task vào quarantine.
                # shutil.move: di chuyển file/thư mục, hoạt động qua filesystem boundary.
                # str() vì shutil.move có thể không chấp nhận Path trên Python cũ.
                # Sau khi move: src không còn tồn tại, dst là thư mục task cũ.
                # discover_tasks() sẽ bỏ qua _quarantine/ vì tên bắt đầu bằng _.
                shutil.move(str(src), str(dst))
        print(f"Quarantined {len(quarantinable)} tasks → {QUARANTINE} (discovery skips '_' dirs).")
    elif quarantinable:
        # Có task hỏng nhưng không dùng --quarantine → chỉ thông báo, không di chuyển.
        print("Re-run with --quarantine to move the invalid tasks out of the suite.")

    # `return 0 if not bad else 1` — ternary expression:
    # Không có task hỏng (bad rỗng) → exit code 0 (thành công).
    # Có task hỏng → exit code 1 (thất bại).
    # Exit code được các CI system (GitHub Actions, Jenkins...) đọc để mark build pass/fail.
    # Quy ước Unix: 0 = thành công (không có lỗi), khác 0 = thất bại.
    return 0 if not bad else 1


# `if __name__ == "__main__":` — chỉ chạy khi gọi trực tiếp (không chạy khi import).
# Xem giải thích chi tiết trong run.py.
if __name__ == "__main__":
    # `sys.exit(main())` — chạy main() và dùng giá trị trả về làm exit code của chương trình.
    sys.exit(main())
