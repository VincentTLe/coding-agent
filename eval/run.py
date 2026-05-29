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

# `from __future__ import annotations` — câu lệnh "kích hoạt tính năng tương lai"
# của Python. Ở đây nó cho phép viết type hint như `list[str]` thay vì `List[str]`
# (cú pháp cũ hơn). Không ảnh hưởng logic, chỉ là sugar cho type annotation.
from __future__ import annotations

# `import argparse` — nạp module argparse vào chương trình.
# argparse là thư viện chuẩn của Python để đọc tham số dòng lệnh (--jobs 8, --filter ...).
# Sau lệnh import này ta có thể gọi argparse.ArgumentParser() để tạo parser.
import argparse

# `import json` — nạp module json: đọc/ghi dữ liệu theo định dạng JSON.
# JSON (JavaScript Object Notation) là chuẩn trao đổi dữ liệu dạng text,
# ví dụ: {"task": "he_000", "passed": true}. Module này có hàm json.dumps()
# (chuyển dict Python → chuỗi JSON) và json.loads() (ngược lại).
import json

# `import logging` — nạp module logging: ghi log (thông điệp debug/warning/error)
# ra màn hình hoặc file. Khác print() ở chỗ có cấp độ (DEBUG < INFO < WARNING < ERROR)
# và có thể tắt bật theo cấp độ mà không cần xóa code.
import logging

# `import re` — biểu thức chính quy, dùng phân tích dòng tổng kết của pytest
# ("N passed" / "M failed") để chấm điểm CHẮC CHẮN có test chạy, không chỉ dựa exit code.
import re

# `import os` — nạp module os: tương tác với hệ điều hành.
# Ở đây dùng os.environ để đọc/ghi biến môi trường (environment variables) — các
# cài đặt hệ thống như PATH, HOME, PYTHONDONTWRITEBYTECODE.
import os

# `import shutil` — nạp module shutil (shell utilities): các thao tác file/thư mục
# cấp cao hơn os. Cung cấp shutil.copytree() (sao chép cả cây thư mục),
# shutil.rmtree() (xóa cả cây thư mục đệ quy), shutil.move() (di chuyển file/thư mục).
import shutil

# `import subprocess` — nạp module subprocess: khởi động và giao tiếp với tiến trình con
# (subprocess). Ví dụ: gọi pytest như một chương trình riêng, đọc output của nó về.
# Subprocess = chương trình con chạy song song hoặc nối tiếp với chương trình Python hiện tại.
import subprocess

# `import sys` — nạp module sys: tương tác với trình thông dịch Python (interpreter).
# sys.path: danh sách thư mục Python tìm kiếm khi import module.
# sys.executable: đường dẫn đến file python đang chạy (vd /home/user/.venv/bin/python).
# sys.exit(): thoát chương trình với mã lỗi.
import sys

# `import time` — nạp module time: đo thời gian.
# time.monotonic() trả về số giây từ một mốc cố định (không bị ảnh hưởng bởi
# thay đổi đồng hồ hệ thống) — dùng để đo khoảng thời gian chính xác.
import time

# `from collections import defaultdict` — nạp riêng lớp defaultdict từ module collections.
#
# collections.defaultdict là một dict đặc biệt: khi truy cập key CHƯA TỒN TẠI,
# thay vì ném KeyError như dict thường, nó TỰ ĐỘNG TẠO giá trị mặc định theo hàm
# được truyền vào lúc khởi tạo.
#
# Ví dụ so sánh:
#   dict thường:        d = {}; d["x"] += 1  → KeyError vì "x" chưa có
#   defaultdict(int):   d = defaultdict(int); d["x"] += 1  → d["x"] = 1 (int() = 0)
#   defaultdict(list):  d = defaultdict(list); d["x"].append(1)  → d["x"] = [1]
#
# Trong file này dùng defaultdict(lambda: [0, 0]) để đếm (pass, total) mà không cần
# kiểm tra key tồn tại trước.
from collections import defaultdict

# `from concurrent.futures import ProcessPoolExecutor, as_completed`
# — nạp hai công cụ xử lý song song từ module concurrent.futures:
#
# ProcessPoolExecutor: Trình quản lý "hồ tiến trình" (process pool).
#   - Tạo sẵn N tiến trình con (worker process).
#   - Worker = tiến trình độc lập chạy một hàm Python cụ thể. Mỗi worker có
#     bộ nhớ riêng, không chia sẻ global với nhau và với tiến trình cha.
#   - Khác ThreadPoolExecutor (dùng thread cùng bộ nhớ) ở chỗ process an toàn hơn
#     với code có global state (như src/tools.py WORKSPACE).
#   - Cách dùng: with ProcessPoolExecutor(max_workers=4) as ex: → tạo pool 4 worker.
#     ex.submit(hàm, tham_số) → gửi 1 công việc cho worker rảnh nhất, trả về Future.
#
# as_completed(futs): Hàm lặp qua danh sách Future theo thứ tự HOÀN THÀNH.
#   - Future = "lời hứa kết quả tương lai" — đối tượng đại diện cho một công việc
#     đang chạy (hoặc đã chạy xong) trong worker.
#   - as_completed() CHẶN (block) cho đến khi có ít nhất 1 Future xong, trả về
#     Future đó, rồi chờ tiếp. Không chờ theo thứ tự submit, chờ theo thứ tự XONG.
#   - Ví dụ: nếu task 3 xong trước task 1, ta nhận task 3 trước — tối ưu hơn chờ tuần tự.
from concurrent.futures import ProcessPoolExecutor, as_completed

# `from contextlib import redirect_stderr, redirect_stdout`
# — nạp hai context manager để "chuyển hướng" luồng output.
# redirect_stdout(f): mọi lệnh print() trong khối `with` sẽ ghi vào file f thay vì màn hình.
# redirect_stderr(f): tương tự nhưng cho stderr (thông báo lỗi).
# Dùng để thu gom log của mỗi worker vào file riêng, giữ terminal sạch.
from contextlib import redirect_stderr, redirect_stdout

# `from datetime import datetime` — nạp lớp datetime từ module datetime.
# datetime.now() trả về thời điểm hiện tại; .strftime("%Y%m%d-%H%M%S") định dạng
# thành chuỗi như "20260526-143022" để đặt tên file kết quả theo timestamp.
from datetime import datetime

# `from fnmatch import fnmatch` — nạp hàm fnmatch để so khớp glob pattern.
# Glob pattern: chuỗi dùng ký tự đặc biệt * ? [] để khớp nhiều tên file/chuỗi cùng lúc.
#   * = khớp mọi ký tự (trừ /) bất kỳ số lần
#   ? = khớp đúng 1 ký tự bất kỳ
#   [abc] = khớp 1 trong các ký tự a, b, c
# Ví dụ: fnmatch("bench/he_000", "bench/*") → True
from fnmatch import fnmatch

# `from multiprocessing import get_context` — nạp hàm get_context từ module multiprocessing.
# get_context("spawn") trả về một "ngữ cảnh" (context) để khởi tạo process.
# "spawn" = mỗi worker process được TẠO MỚI HOÀN TOÀN (re-import tất cả module từ đầu),
# thay vì "fork" (sao chép bộ nhớ của tiến trình cha). Spawn an toàn hơn với OpenAI client
# vì tránh chia sẻ socket/kết nối mạng đang mở.
from multiprocessing import get_context

# `from pathlib import Path` — nạp lớp Path để thao tác đường dẫn file/thư mục.
# Path là cách Python hiện đại xử lý đường dẫn (thay cho os.path cũ).
# Ưu điểm: dùng toán tử / để nối đường dẫn (Path("/home") / "user" → Path("/home/user")),
# có các method .exists(), .read_text(), .write_text(), .mkdir(), .rglob(), .name, .suffix.
from pathlib import Path

# Make `from src.agent import run_agent` work when running from anywhere.
# `Path(__file__)` — __file__ là biến đặc biệt Python tự đặt = đường dẫn file đang chạy.
# .resolve() — chuyển đường dẫn tương đối thành tuyệt đối, giải quyết symlink.
# .parent.parent — lên 2 cấp thư mục: từ eval/run.py → eval/ → / (root của repo).
ROOT = Path(__file__).resolve().parent.parent

# `sys.path.insert(0, str(ROOT))` — chèn thư mục ROOT vào đầu danh sách tìm kiếm module.
# Khi Python gặp `import src.agent`, nó tìm trong sys.path theo thứ tự.
# Chèn vào vị trí 0 (đầu danh sách) → ROOT được tìm trước mọi thư mục khác.
# str(ROOT) vì sys.path chứa string, không phải Path object.
sys.path.insert(0, str(ROOT))

# `from src.agent import run_agent` — import hàm run_agent từ file src/agent.py.
# `# noqa: E402` — chỉ thị cho linter bỏ qua cảnh báo E402 ("module level import not at top").
# Import này phải nằm SAU sys.path.insert ở trên nên không thể để trên cùng.
from src.agent import run_agent  # noqa: E402


# Hằng số (constant) — biến VIẾT HOA theo quy ước Python = giá trị không thay đổi.
# `/` toán tử nối Path: ROOT / "eval" / "tasks" = đường dẫn tuyệt đối tới eval/tasks/.
TASKS_DIR = ROOT / "eval" / "tasks"       # thư mục chứa tất cả task
RESULTS_DIR = ROOT / "eval" / "results"  # thư mục lưu kết quả chạy
EVAL_LOCK = RESULTS_DIR / ".eval.lock"   # lock 1-eval-1-lúc (xem _acquire_eval_lock)


# ---------------------------------------------------------------------------
# ĐỌC METADATA TỪ task.md  (Goal / Category / Difficulty)
# ---------------------------------------------------------------------------

# `def read_section(task_dir: Path, heading: str, default: str = "") -> str:`
# Định nghĩa hàm (function).
#   def — từ khóa bắt đầu định nghĩa hàm.
#   read_section — tên hàm.
#   (task_dir: Path, heading: str, default: str = "") — danh sách tham số với type hint:
#     task_dir: Path — tham số nhận đường dẫn thư mục task (kiểu Path)
#     heading: str — tiêu đề section cần đọc (kiểu chuỗi)
#     default: str = "" — tham số tùy chọn, mặc định là chuỗi rỗng
#   -> str — hàm trả về chuỗi (return type annotation)
def read_section(task_dir: Path, heading: str, default: str = "") -> str:
    """Trả về text dưới '## <heading>' cho tới heading '##' kế tiếp.

    Tổng quát hoá read_goal cũ: dùng chung để đọc Goal / Category / Difficulty.
    """
    # Tạo đường dẫn tới file task.md trong thư mục task_dir.
    # / toán tử nối Path, tương đương os.path.join(task_dir, "task.md").
    md_path = task_dir / "task.md"

    # `.exists()` — phương thức của Path, trả về True nếu file/thư mục tồn tại.
    # `if not md_path.exists():` — nếu file KHÔNG tồn tại thì...
    # `return default` — thoát hàm ngay, trả về giá trị mặc định.
    if not md_path.exists():
        return default

    # `lines: list[str] = []` — khai báo biến lines với type hint list[str] (danh sách chuỗi).
    # `[]` là danh sách rỗng. Ta sẽ dần thêm các dòng text vào đây.
    lines: list[str] = []

    # `in_section = False` — biến cờ (flag) theo dõi ta đang đọc trong section mục tiêu chưa.
    # False = chưa vào section. Sẽ đổi thành True khi gặp heading cần tìm.
    in_section = False

    # `.read_text(encoding="utf-8", errors="replace")` — đọc toàn bộ nội dung file dạng text.
    #   encoding="utf-8" — dùng bảng mã UTF-8 (hỗ trợ tiếng Việt, emoji...).
    #   errors="replace" — nếu gặp ký tự không đọc được, thay bằng ? thay vì ném lỗi.
    # `.splitlines()` — tách chuỗi thành danh sách các dòng (tách tại \n, \r\n).
    # `for line in ...:` — vòng lặp, biến line nhận lần lượt từng dòng.
    for line in md_path.read_text(encoding="utf-8", errors="replace").splitlines():

        # `line.startswith("## ")` — True nếu dòng BẮT ĐẦU bằng "## " (heading Markdown cấp 2).
        # `line[3:]` — cắt chuỗi từ vị trí 3 trở đi (bỏ "## ").
        # `.strip()` — xóa khoảng trắng/tab ở hai đầu chuỗi.
        # `.lower()` — chuyển thành chữ thường để so sánh không phân biệt hoa thường.
        # `== heading.lower()` — kiểm tra heading có khớp không.
        # `and` — toán tử logic: cả hai vế phải True.
        if line.startswith("## ") and line[3:].strip().lower() == heading.lower():
            # Tìm thấy heading cần tìm: bật cờ vào section.
            in_section = True
            # `continue` — bỏ qua phần còn lại của vòng lặp, chuyển sang dòng tiếp theo.
            # Không thêm dòng heading vào kết quả.
            continue

        # Chỉ xử lý tiếp nếu đang trong section mục tiêu.
        if in_section:
            # `line.startswith("##")` — gặp heading ## tiếp theo = kết thúc section hiện tại.
            if line.startswith("##"):  # heading kế tiếp = hết section
                # `break` — thoát khỏi vòng lặp for ngay lập tức.
                break
            # `lines.append(line)` — thêm dòng này vào cuối danh sách lines.
            lines.append(line)

    # `"\n".join(lines)` — nối tất cả phần tử trong danh sách lines thành 1 chuỗi,
    # dùng ký tự xuống dòng \n làm dấu phân cách.
    # `.strip()` — xóa khoảng trắng thừa ở đầu và cuối chuỗi kết quả.
    text = "\n".join(lines).strip()

    # Biểu thức điều kiện một dòng (ternary expression):
    # `giá_trị_nếu_true if điều_kiện else giá_trị_nếu_false`
    # Nếu text không rỗng → trả về text, ngược lại trả về default.
    return text if text else default


def read_goal(task_dir: Path) -> str:
    """Mô tả nhiệm vụ cho agent (toàn bộ phần dưới '## Goal')."""
    # Gọi hàm read_section để đọc section "Goal" từ task.md.
    goal = read_section(task_dir, "Goal")
    # `if goal:` — Python xem chuỗi rỗng "" là False, chuỗi có nội dung là True.
    # Nếu tìm được goal → trả về nó.
    if goal:
        return goal
    # Nếu task.md không có section Goal → tạo câu mô tả mặc định.
    # f"..." — f-string (formatted string): {task_dir.name} được thay thế bằng giá trị thực.
    # task_dir.name — tên thư mục cuối (ví dụ: "01_strings" từ đường dẫn eval/tasks/01_strings).
    return f"Fix all failing tests in eval/tasks/{task_dir.name}/."


def read_meta(task_dir: Path) -> tuple[str, str]:
    """(category, difficulty) — để gộp pass-rate theo nhóm. Default nếu task.md thiếu."""
    # Đọc section "Category" và "Difficulty" từ task.md.
    # Nếu không có → dùng giá trị mặc định "uncategorized" / "unknown".
    cat = read_section(task_dir, "Category", "uncategorized")
    dif = read_section(task_dir, "Difficulty", "unknown")

    # Lấy dòng đầu tiên của section (có thể có nhiều dòng, ta chỉ cần dòng đầu).
    # `cat.splitlines()` — tách thành danh sách dòng.
    # `[0]` — lấy phần tử đầu tiên (index 0).
    # `.strip().lower()` — chuẩn hóa: bỏ khoảng trắng, chuyển thường.
    # `if cat else "uncategorized"` — nếu cat rỗng thì dùng giá trị mặc định.
    cat = cat.splitlines()[0].strip().lower() if cat else "uncategorized"
    dif = dif.splitlines()[0].strip().lower() if dif else "unknown"

    # `cat or "uncategorized"` — nếu cat là chuỗi rỗng (falsy) thì dùng "uncategorized".
    # Toán tử `or` trong Python: trả về vế trái nếu nó "truthy", ngược lại trả về vế phải.
    # Trả về tuple (2 giá trị) — caller nhận bằng: cat, dif = read_meta(task_dir)
    return cat or "uncategorized", dif or "unknown"


def read_hide_tests(task_dir: Path) -> bool:
    """Có GIẤU file test khỏi agent không?
    '## Tests: hidden' → giấu (đo khả năng implement từ SPEC, chống agent đọc test
    rồi hard-code đáp án). MẶC ĐỊNH KHÔNG giấu → task kiểu debug/sửa-test-fail giữ
    nguyên workflow dùng pytest làm feedback (chính là khả năng 'agent tự verify'
    mà ta muốn chứng minh). Converter set 'hidden' cho mọi benchmark task.
    """
    # Đọc section "Tests", mặc định "visible" nếu không có.
    # .strip().lower().startswith("hidden") — True nếu nội dung bắt đầu bằng "hidden".
    # Trả về kiểu bool (True/False).
    return read_section(task_dir, "Tests", "visible").strip().lower().startswith("hidden")


# ---------------------------------------------------------------------------
# DISCOVERY — tìm mọi task dir (đệ quy), bỏ qua dir bắt đầu bằng _ hoặc .
# ---------------------------------------------------------------------------

def discover_tasks(root: Path) -> list[Path]:
    """Task = thư mục chứa task.md. Đệ quy để bắt cả bench/he_000, curated/...,
    lẫn 01_strings (cấu trúc cũ). Bỏ qua dir có thành phần bắt đầu bằng '_'
    (quarantine) hoặc '.' (cache).
    """
    # `out: list[Path] = []` — danh sách kết quả, ban đầu rỗng.
    out: list[Path] = []

    # `root.rglob("task.md")` — tìm kiếm ĐỆ QUY (recursive glob) tất cả file tên
    # "task.md" trong mọi thư mục con của root.
    # `sorted(...)` — sắp xếp kết quả theo thứ tự bảng chữ cái để thứ tự ổn định.
    for md in sorted(root.rglob("task.md")):
        # `md.parent` — thư mục chứa file task.md = thư mục task.
        d = md.parent

        # `d.relative_to(root)` — đường dẫn TƯƠNG ĐỐI của d so với root.
        # Ví dụ: d = /tasks/bench/he_000, root = /tasks → rel = bench/he_000.
        rel = d.relative_to(root)

        # `rel.parts` — tuple các thành phần đường dẫn: ("bench", "he_000").
        # `any(...)` — trả về True nếu ÍT NHẤT MỘT phần tử thỏa điều kiện.
        # `part.startswith(("_", "."))` — bắt đầu bằng _ hoặc . (tuple viết tắt của or).
        # Bỏ qua các thư mục như _quarantine/, .cache/...
        if any(part.startswith(("_", ".")) for part in rel.parts):
            continue  # bỏ qua, sang task tiếp theo

        # Thư mục hợp lệ → thêm vào danh sách kết quả.
        out.append(d)
    return out


def rel_id(task_dir: Path) -> str:
    """ID ổn định cho task = đường dẫn tương đối dưới eval/tasks ('bench/he_000')."""
    # `.relative_to(TASKS_DIR)` — đường dẫn tương đối so với TASKS_DIR.
    # `.as_posix()` — chuyển Path thành chuỗi dùng dấu / (chuẩn POSIX/Unix),
    # thay vì dấu \ (Windows). Đảm bảo ID nhất quán trên mọi hệ điều hành.
    return task_dir.relative_to(TASKS_DIR).as_posix()


def heal_corrupted_tasks() -> int:
    """Chữa lành fixtures bị một run trước HARD-KILL (SIGKILL/OOM/reboot) làm bẩn: test bị xoá
    chưa kịp trả lại, hoặc file bị agent sửa còn sót. Fixtures được git track nên
    `git checkout -- eval/tasks/` trả MỌI file tracked về HEAD — phục cả test ẩn LẪN code agent
    đã sửa (mạnh hơn chỉ phục test). Trả số file đã chữa. Best-effort: không phải git repo →
    bỏ qua. Gọi 1 lần ở đầu main(), SAU khi đã lấy lock (xem _eval_lock) để không giẫm lên một
    eval khác đang chạy dở. Chỉ chạy khi có thay đổi chưa-commit dưới eval/tasks (bình thường
    sạch → no-op; chỉ hard-kill mới để lại bẩn).
    """
    try:
        st = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--", str(TASKS_DIR)],
                            capture_output=True, text=True, timeout=30)
        if st.returncode != 0:
            return 0                            # không phải git repo / git lỗi → bỏ qua
        dirty = [ln for ln in st.stdout.splitlines() if ln.strip()]
        if not dirty:
            return 0
        subprocess.run(["git", "-C", str(ROOT), "checkout", "--", str(TASKS_DIR)],
                       capture_output=True, text=True, timeout=120, check=False)
        for ln in dirty[:10]:                   # in ra để người dùng thấy đã chữa gì
            print(f"  healed: {ln.strip()}")
        return len(dirty)
    except Exception:
        return 0                                # heal KHÔNG được làm hỏng eval


def _pid_alive(pid: int) -> bool:
    """True nếu tiến trình pid còn sống (signal 0 = chỉ kiểm tra, không gửi gì)."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _acquire_eval_lock() -> bool:
    """Khoá độc quyền 1-eval-1-lúc trên repo này (hide/restore tại chỗ không an toàn khi 2 eval
    chạy song song — Codex review #4). True nếu lấy được. Lock cũ mà pid đã chết = stale → ghi
    đè. Tự gỡ khi tiến trình thoát (atexit)."""
    if EVAL_LOCK.exists():
        try:
            old = int((EVAL_LOCK.read_text(encoding="utf-8").strip() or "0"))
        except Exception:
            old = 0
        if old and old != os.getpid() and _pid_alive(old):
            print(f"ERROR: một eval khác (pid {old}) đang chạy trên repo này (lock {EVAL_LOCK}). "
                  "Chờ nó xong, hoặc xoá lock nếu chắc chắn nó đã chết.")
            return False
    EVAL_LOCK.parent.mkdir(parents=True, exist_ok=True)
    EVAL_LOCK.write_text(str(os.getpid()), encoding="utf-8")
    import atexit
    atexit.register(lambda: EVAL_LOCK.unlink(missing_ok=True))
    return True


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
    # `snap: dict[Path, str] = {}` — khai báo biến snap là dict (từ điển) rỗng.
    # dict ánh xạ key → value: ở đây Path → str (đường dẫn file → nội dung file).
    # Dấu {} tạo dict rỗng (khác với set() cũng dùng {}).
    snap: dict[Path, str] = {}

    # `task_dir.rglob("*")` — tìm kiếm đệ quy TẤT CẢ file và thư mục (*: khớp mọi tên).
    for f in task_dir.rglob("*"):
        # `f.is_file()` — True nếu f là file (không phải thư mục).
        if not f.is_file():
            continue
        # Bỏ qua build artifact BINARY tái sinh được (.pyc / __pycache__): đọc text với
        # errors="replace" rồi write_text lại sẽ HỎNG nội dung binary khi restore. Không cần
        # snapshot (pytest tự tạo lại; lúc chấm đã set PYTHONDONTWRITEBYTECODE).
        if "__pycache__" in f.parts or f.suffix == ".pyc":
            continue
        # `snap[f] = ...` — thêm entry vào dict: key là Path f, value là nội dung file (text).
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
    # Duyệt lại tất cả file/thư mục hiện có trong task_dir (có thể đã thay đổi sau khi agent chạy).
    for f in task_dir.rglob("*"):
        # `f.exists()` — kiểm tra path còn tồn tại không (có thể đã bị xóa bởi rmtree trước đó).
        if not f.exists():  # cha đã bị rmtree ở vòng trước
            continue  # bỏ qua nếu đã biến mất

        if f.is_file():
            # `f not in snap` — kiểm tra key f có trong dict snap không.
            # `not in` — toán tử phủ định in: True nếu KHÔNG có trong snap.
            if f not in snap:
                # `f.unlink()` — xóa file (chỉ file, không xóa thư mục).
                f.unlink()
        elif f.is_dir():
            # Dir lạ (không chứa file gốc nào) → xoá cả cây. Dir vẫn chứa file
            # snapshot sẽ được giữ; file lạ bên trong nó được nhánh is_file() ở trên dọn.
            # `any(s == f or f in s.parents for s in snap)` —
            #   s.parents: tuple tất cả thư mục cha của s (ví dụ s = /a/b/c.py → parents = (/a/b, /a, /)).
            #   Nếu không có file snapshot nào nằm trong thư mục f → thư mục f là "lạ".
            if not any(s == f or f in s.parents for s in snap):
                # `shutil.rmtree(f, ignore_errors=True)` — xóa THƯ MỤC f và toàn bộ nội dung bên trong.
                # shutil.rmtree: "rm -rf" của Python — xóa đệ quy không hỏi.
                # ignore_errors=True: nếu có lỗi (file đang mở, quyền truy cập...) thì bỏ qua, không crash.
                shutil.rmtree(f, ignore_errors=True)


def restore_files(task_dir: Path, snap: dict[Path, str]) -> None:
    """Khôi phục fixtures về trạng thái gốc + xoá MỌI path lạ agent tạo ra (ĐỆ QUY).

    Ghi lại nội dung gốc cho từng file trong snap (parent có thể đã bị xoá → tạo lại),
    rồi xoá mọi file/dir dưới task_dir không thuộc snapshot. Đệ quy (rglob) để dọn
    cả subdir rò rỉ như venv/ hay tests/ — bản cũ chỉ xử lý top-level nên các thư mục
    này còn sót, làm bẩn lần chạy sau. Đây là lưới an toàn cuối trong `finally`.
    """
    # `.items()` — phương thức của dict, trả về danh sách các cặp (key, value).
    # `for f, content in snap.items():` — mỗi vòng lặp nhận 1 cặp (Path, str).
    for f, content in snap.items():
        # `f.parent` — thư mục chứa file f.
        # `.mkdir(parents=True, exist_ok=True)` — tạo thư mục (và mọi thư mục cha nếu chưa có).
        #   parents=True: tạo cả chuỗi thư mục cha (như mkdir -p).
        #   exist_ok=True: không báo lỗi nếu thư mục đã tồn tại.
        f.parent.mkdir(parents=True, exist_ok=True)
        # `f.write_text(content, encoding="utf-8")` — ghi nội dung gốc lại vào file.
        # Ghi đè toàn bộ nội dung hiện tại (nếu agent đã sửa file này).
        f.write_text(content, encoding="utf-8")
    # Xóa mọi file/thư mục lạ mà agent đã tạo (không nằm trong snapshot).
    remove_extras(task_dir, snap)


def run_pytest(task_dir: Path) -> tuple[bool, str]:
    """Return (passed, output). passed True iff exit code == 0.

    `sys.executable -m pytest` để chắc chắn dùng pytest của venv đang chạy
    (không phụ thuộc PATH). cwd=task_dir → pytest auto-collect test_*.py và
    import source bằng tên trần.
    """
    # `try: ... except subprocess.TimeoutExpired:` — khối xử lý ngoại lệ.
    # try: thử chạy code bên trong.
    # except subprocess.TimeoutExpired: nếu xảy ra lỗi TimeoutExpired (timeout) → bắt và xử lý.
    try:
        # `subprocess.run(...)` — Gọi một chương trình ngoài (external process) từ Python.
        # Subprocess = "tiến trình con" — một chương trình riêng biệt chạy trong hệ điều hành.
        # Khác với gọi hàm Python thông thường, subprocess THỰC SỰ khởi động một chương trình
        # mới (pytest) với tiến trình riêng, không gian bộ nhớ riêng.
        #
        # Tham số đầu tiên — danh sách lệnh và tham số:
        #   sys.executable: đường dẫn Python đang chạy, ví dụ /home/tle/.venv/bin/python.
        #   "-m": chạy module như script (python -m pytest).
        #   "pytest": module cần chạy.
        #   "--tb=short": chỉ in traceback ngắn khi test fail (tiết kiệm output).
        #   "-p", "no:cacheprovider": tắt plugin cache của pytest (không tạo .pytest_cache/).
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--tb=short", "-p", "no:cacheprovider"],
            # `cwd=task_dir` — "current working directory": chạy pytest với thư mục làm việc
            # là task_dir. Quan trọng: pytest sẽ tìm file test_*.py trong thư mục này,
            # và Python sẽ có thể import module trong task_dir bằng tên trực tiếp.
            cwd=task_dir,
            # `capture_output=True` — THU THẬP output của subprocess vào bộ nhớ thay vì
            # in thẳng ra màn hình. Sau khi chạy xong, output nằm trong result.stdout và
            # result.stderr (dạng string nếu text=True, dạng bytes nếu không).
            capture_output=True,
            # `text=True` — đọc stdout/stderr dưới dạng chuỗi (str) thay vì bytes.
            # Nếu không có text=True, result.stdout sẽ là b"..." (bytes).
            text=True,
            # `timeout=60` — nếu subprocess chạy QUÁ 60 giây → ném ngoại lệ
            # subprocess.TimeoutExpired (bắt ở except bên dưới).
            timeout=60,
            # PYTHONDONTWRITEBYTECODE: KHÔNG ghi .pyc. Khi validate ta ghi đè cùng 1
            # file (stub→reference) rồi chạy lại; nếu .pyc cũ còn đó và mtime trùng
            # giây, Python có thể nạp BYTECODE CŨ → kết quả sai (vd stub "pass" nhầm
            # vì chạy lại bytecode của reference). Tắt .pyc → mỗi import compile lại
            # từ source, luôn đúng. `-p no:cacheprovider`: khỏi rải .pytest_cache.
            # `{**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}` —
            #   os.environ: dict chứa tất cả biến môi trường hiện tại (PATH, HOME...).
            #   **os.environ: "giải nén" dict ra thành các cặp key=value riêng lẻ (spread operator).
            #   Kết hợp với "PYTHONDONTWRITEBYTECODE": "1" → tạo dict mới = biến môi trường
            #   cũ + thêm/ghi đè PYTHONDONTWRITEBYTECODE. Subprocess thừa hưởng môi trường này.
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
    except subprocess.TimeoutExpired:
        # Đánh dấu TIMEOUT rõ ràng trong output → validate_tasks phân biệt được "chạy lâu"
        # với "logic sai" (không quarantine nhầm task chỉ vì máy bận).
        return False, "ERROR: pytest TIMEOUT after 60s"

    out = result.stdout + result.stderr
    # Exit code 0 CHƯA đủ để tính PASS: pytest trả 0 cả khi 0 test được collect hoặc TẤT CẢ
    # bị skip (vd file test biến mất, hoặc toàn @skip) → sẽ là PASS GIẢ, làm điểm phồng và
    # che lỗi hide-tests. Yêu cầu CÓ ÍT NHẤT 1 test thực sự passed VÀ không có failed/error.
    passed_ct = sum(int(n) for n in re.findall(r"(\d+) passed", out))
    # Chỉ coi là FAIL khi có SỐ DƯƠNG failed/error (tránh "0 failed"/"0 errors" trong text
    # warning/plugin gây false-fail — Codex review #5). [1-9]\d* = số ≥ 1.
    has_fail = bool(re.search(r"[1-9]\d* (?:failed|error)", out))
    passed = (result.returncode == 0) and passed_ct >= 1 and not has_fail
    return passed, out


# ---------------------------------------------------------------------------
# 1 ĐƠN VỊ CÔNG VIỆC — chạy trong worker process (phải ở module level để pickle)
# ---------------------------------------------------------------------------

# LÝ DO HÀM NÀY PHẢI Ở MODULE LEVEL (không được lồng trong hàm khác):
# ProcessPoolExecutor gửi hàm sang worker process bằng cơ chế "pickle" —
# serialize hàm thành bytes, gửi qua IPC (inter-process communication), worker
# deserialize và chạy. Python chỉ pickle được hàm ở MODULE LEVEL (có tên đầy đủ
# như "eval.run.evaluate_task"), không pickle được hàm lồng (nested/lambda).
def evaluate_task(payload: tuple) -> dict:
    """Chạy agent trên 1 task rồi chấm điểm. Trả về result dict.

    Các bước (mọi thứ bọc trong finally để fixtures luôn được khôi phục):
      1. snapshot fixtures.
      2. GIẤU file test (xoá khỏi workspace) → agent không thể đọc test để gian lận.
      3. chạy agent (stdout/stderr redirect ra log riêng cho gọn terminal).
      4. trả file test lại → chấm bằng pytest độc lập.
      5. restore fixtures.
    """
    # "Giải nén" (unpack) tuple payload thành 6 biến riêng lẻ.
    # Thứ tự phải khớp với thứ tự khi tạo tuple trong hàm main().
    task_path, max_iters, time_budget, repeat_idx, log_dir, temperature, skill_path = payload

    # Chuyển chuỗi đường dẫn thành Path object để dùng các method của Path.
    # (Worker process nhận payload qua pickle — Path object có thể không serialize được
    # nên gửi str rồi chuyển lại ở đây.)
    task_dir = Path(task_path)
    # Lấy ID ổn định của task (ví dụ "bench/he_000").
    tid = rel_id(task_dir)
    # Đọc metadata: thể loại và độ khó.
    category, difficulty = read_meta(task_dir)
    # Đọc mô tả nhiệm vụ cho agent.
    goal = read_goal(task_dir)

    # Tắt log INFO (HTTP request spam của openai/httpx) trong worker → terminal sạch.
    # logging.getLogger() — lấy logger gốc (root logger).
    # .setLevel(logging.WARNING) — chỉ hiển thị WARNING, ERROR, CRITICAL; im lặng INFO/DEBUG.
    logging.getLogger().setLevel(logging.WARNING)

    # Bước 1: chụp ảnh toàn bộ file trong task_dir vào RAM.
    snap = snapshot_files(task_dir)

    # ĐÂY LÀ CƠ CHẾ QUAN TRỌNG NHẤT CỦA EVAL: GIẤU TEST.
    #
    # Vấn đề: Agent có thể "gian lận" bằng cách đọc nội dung file test_*.py,
    # biết trước output mong đợi, rồi viết code hard-code đáp án thay vì thực sự
    # giải quyết bài toán. Điểm số sẽ cao nhưng không phản ánh khả năng thực.
    #
    # Giải pháp: GIẤU file test trước khi agent chạy, chỉ trả lại sau khi agent
    # đã nộp bài. Cách làm:
    #   1. Đọc nội dung test vào RAM (đã có trong snap).
    #   2. Xóa file test khỏi thư mục làm việc.
    #   3. Agent chạy — chỉ thấy code stub và spec trong task.md, KHÔNG thấy test.
    #   4. Sau khi agent xong → ghi lại file test.
    #   5. Chạy pytest → điểm số THỰC SỰ.
    #
    # `hide = read_hide_tests(task_dir)` — đọc cờ từ task.md: có cần giấu không?
    hide = read_hide_tests(task_dir)

    # Dict comprehension: tạo dict theo cú pháp {key: value for item in iterable if condition}.
    # {f: c for f, c in snap.items() if f.name.startswith("test_") and f.suffix == ".py"}
    #   f.name: tên file (không có đường dẫn), ví dụ "test_solution.py".
    #   f.name.startswith("test_"): True nếu tên bắt đầu bằng "test_".
    #   f.suffix: phần mở rộng, ví dụ ".py".
    #   Kết quả: dict chứa chỉ các file test Python.
    # Nếu hide = False → hidden_tests = {} (dict rỗng, không giấu gì).
    hidden_tests = ({f: c for f, c in snap.items()
                     if f.name.startswith("test_") and f.suffix == ".py"}
                    if hide else {})

    # Khởi tạo các biến kết quả với giá trị mặc định (trường hợp xấu nhất).
    finish_reason = "agent_crash"  # lý do agent dừng
    iters_used = 0                  # số vòng lặp đã dùng
    passed = False                  # có pass không
    output = ""                     # output của pytest

    # Tạo đường dẫn file log cho task này.
    # `tid.replace('/', '__')` — thay dấu / bằng __ để dùng làm tên file an toàn.
    # `.r{repeat_idx}.log` — thêm chỉ số lần chạy (nếu chạy nhiều lần).
    log_path = Path(log_dir) / f"{tid.replace('/', '__')}.r{repeat_idx}.log"

    # `time.monotonic()` — ghi lại thời điểm bắt đầu (số giây từ mốc cố định).
    t0 = time.monotonic()

    # `try: ... finally:` — đảm bảo khối `finally` LUÔN CHẠY dù có lỗi hay không.
    # Dùng để đảm bảo restore_files() luôn được gọi, tránh để task_dir ở trạng thái bẩn.
    try:
        # `with open(log_path, "w", encoding="utf-8") as lf` — mở file log để ghi.
        # `"w"` = write mode: tạo mới hoặc ghi đè file cũ.
        # `as lf` — tên biến đại diện cho file đang mở (file object).
        # `redirect_stdout(lf)` — chuyển hướng print() vào file lf.
        # `redirect_stderr(lf)` — chuyển hướng stderr vào file lf.
        # Dùng `with` để đảm bảo file được đóng khi ra khỏi khối, kể cả khi có lỗi.
        with open(log_path, "w", encoding="utf-8") as lf, redirect_stdout(lf), redirect_stderr(lf):
            # Xóa file test khỏi thư mục làm việc (giấu khỏi agent).
            # `for f in hidden_tests:` — lặp qua các KEY của dict (các Path object).
            for f in hidden_tests:
                # GIẤU test = XOÁ khỏi disk. test_*.py biến mất HẲN trong lúc agent chạy nên
                # agent KHÔNG đọc được — kể cả qua run_bash/run_python (vốn không bị _safe_path
                # chặn). [Codex review bắt: phương án "move ra backup" để lại file trên disk ở
                # đường dẫn đoán được = LEAK mới — đã bỏ.] Nội dung gốc vẫn nằm trong snap (RAM)
                # để trả lại bên dưới; nếu hard-kill bỏ qua finally → heal_corrupted_tasks() (git)
                # khôi phục ở đầu run kế (phục cả test LẪN file agent đã sửa).
                if f.exists():
                    f.unlink()

            try:
                # Chạy agent với task hiện tại.
                # run_agent() là hàm chính của coding agent — nó gọi LLM, thực thi tool calls,
                # sửa code, lặp cho đến khi xong hoặc hết turn.
                # workspace=task_dir: agent sẽ làm việc trong thư mục task_dir.
                res = run_agent(goal, workspace=task_dir, max_iters=max_iters,
                                time_budget_s=time_budget, temperature=temperature,
                                skill_path=skill_path)
                # `.get("finish_reason", "unknown")` — đọc key "finish_reason" từ dict res.
                # Nếu key không tồn tại → trả về "unknown" (tham số thứ 2 của .get()).
                finish_reason = res.get("finish_reason", "unknown")
                # `int(...)` — chuyển về kiểu số nguyên (phòng trường hợp trả về float/str).
                iters_used = int(res.get("iters_used", 0))
            except Exception as e:  # noqa: BLE001  (1 task lỗi không được giết cả run)
                # Bắt MỌI loại exception (Exception là lớp cha của hầu hết lỗi Python).
                # Gán `as e` để có thể dùng biến e tham chiếu đến exception đó.
                # QUAN TRỌNG: không để exception từ 1 task crash toàn bộ eval run.
                finish_reason = "agent_crash"
                # `{e!r}` trong f-string: !r gọi repr() trên e, in dạng debugging đầy đủ.
                print(f"AGENT CRASHED: {e!r}")

            # Trả lại file test sau khi agent đã xong — ghi nội dung GỐC từ snap (RAM) để chấm.
            for f, content in hidden_tests.items():  # trả test lại để chấm
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(content, encoding="utf-8")

        # Trước khi chấm: dọn mọi path lạ (file/dir agent tạo, vd lời giải phụ hay
        # venv/ rò rỉ) → pytest chỉ collect đúng test gốc + edit của agent lên file gốc.
        # Test ẩn vừa được trả lại ở trên đã nằm trong snap nên remove_extras GIỮ chúng.
        remove_extras(task_dir, snap)

        # Chấm điểm bằng pytest.
        passed, output = run_pytest(task_dir)

    finally:
        # `finally` — khối này LUÔN CHẠY dù try thành công hay thất bại.
        # Khôi phục task_dir về trạng thái ban đầu để không ảnh hưởng lần chạy sau.
        restore_files(task_dir, snap)

    # Trả về dict chứa đầy đủ thông tin về kết quả chạy task này.
    # Dict literal: {key: value, key: value, ...}.
    return {
        "task": tid,                          # ID task
        "category": category,                  # thể loại
        "difficulty": difficulty,              # độ khó
        "passed": bool(passed),                # có pass không (ép kiểu bool cho chắc)
        "iters_used": iters_used,              # số turn đã dùng
        "finish_reason": finish_reason,        # lý do kết thúc
        # `time.monotonic() - t0` — thời gian chạy (giây).
        # `round(..., 1)` — làm tròn 1 chữ số thập phân.
        "duration_s": round(time.monotonic() - t0, 1),
        # `output[-1000:]` — lấy 1000 ký tự CUỐI của output pytest.
        # Slice âm: Python đếm từ cuối chuỗi. Output có thể rất dài, chỉ giữ phần đuôi quan trọng.
        "pytest_tail": output[-1000:],
        "repeat_idx": repeat_idx,             # chỉ số lần lặp
        "skill_path": skill_path,             # skill đã chèn (None nếu không) — phục vụ so A/B
    }


# ---------------------------------------------------------------------------
# LỌC TASK + RESUME
# ---------------------------------------------------------------------------

def select_tasks(all_tasks: list[Path], filters: list[str]) -> list[Path]:
    """Lọc theo --filter. Mỗi filter là 'key=value' (so metadata: category/
    difficulty/task) hoặc glob/substring trên task id. Chọn task nếu khớp TẤT CẢ.
    """
    # Nếu không có filter nào → trả về tất cả task.
    if not filters:
        return all_tasks

    # `selected = []` — danh sách kết quả rỗng.
    selected = []

    # Duyệt qua từng task.
    for t in all_tasks:
        tid = rel_id(t)               # ID task như "bench/he_000"
        cat, dif = read_meta(t)       # đọc metadata
        # Tạo dict mapping tên thuộc tính → giá trị để tra cứu.
        meta = {"category": cat, "difficulty": dif, "task": tid}
        # `ok = True` — giả định task này khớp, sẽ đặt False nếu có filter nào không khớp.
        ok = True

        for flt in filters:
            # Filter dạng "key=value" — so sánh metadata.
            if "=" in flt:
                # `flt.split("=", 1)` — tách chuỗi tại dấu = đầu tiên (tối đa 1 lần tách).
                # Ví dụ: "difficulty=hard" → ["difficulty", "hard"].
                k, v = flt.split("=", 1)
                # `meta.get(k.strip().lower(), "")` — tra cứu key trong dict meta.
                # .get(key, default): trả về default nếu key không tồn tại.
                if meta.get(k.strip().lower(), "") != v.strip().lower():
                    ok = False
                    break  # filter này không khớp → bỏ qua task, không cần kiểm tra tiếp

            # Filter dạng glob: chứa ký tự * ? [
            # `any(c in flt for c in "*?[]")` — True nếu flt chứa ít nhất 1 ký tự glob.
            elif any(c in flt for c in "*?[]"):
                # `fnmatch(tid, flt)` — kiểm tra tid có khớp glob pattern flt không.
                if not fnmatch(tid, flt):
                    ok = False
                    break

            # Filter dạng substring: kiểm tra chuỗi flt có nằm trong tid không.
            # `flt not in tid` — True nếu flt KHÔNG phải substring của tid.
            elif flt not in tid:
                ok = False
                break

        # Nếu task khớp tất cả filter → thêm vào danh sách kết quả.
        if ok:
            selected.append(t)
    return selected


def load_done(out_path: Path) -> tuple[set, list]:
    """Đọc JSONL đã có → (set (task,repeat) đã chạy, list result cũ) cho --resume.

    Định dạng JSONL (JSON Lines): mỗi dòng là một JSON object hoàn chỉnh, độc lập.
    Khác JSON thông thường (1 object lớn): JSONL cho phép ghi TĂNG DẦN — sau mỗi task
    xong ta append 1 dòng, không cần đọc lại toàn bộ file. Nếu chương trình crash
    giữa chừng, các dòng đã ghi vẫn hợp lệ (không bị corrupt như JSON 1 object).
    """
    # `done: set = set()` — set (tập hợp) rỗng.
    # Set khác list: không có thứ tự, không có phần tử trùng, kiểm tra "in" rất nhanh O(1).
    # Dùng để kiểm tra nhanh task đã chạy chưa.
    done: set = set()

    # `prior: list = []` — danh sách kết quả cũ.
    prior: list = []

    # `out_path.exists()` — kiểm tra file kết quả có tồn tại không.
    if out_path.exists():
        # Đọc toàn bộ file → tách thành dòng → xử lý từng dòng.
        for line in out_path.read_text(encoding="utf-8").splitlines():
            # `.strip()` — xóa khoảng trắng/xuống dòng thừa.
            line = line.strip()
            # Bỏ qua dòng rỗng.
            if not line:
                continue

            # `try: ... except json.JSONDecodeError:` — thử parse JSON, bỏ qua dòng lỗi.
            # json.JSONDecodeError được ném khi chuỗi không phải JSON hợp lệ.
            try:
                # `json.loads(line)` — parse chuỗi JSON thành dict Python.
                # json.loads = "load string": đầu vào là chuỗi (khác json.load đọc từ file).
                r = json.loads(line)
            except json.JSONDecodeError:
                # Dòng không parse được (file bị corrupt?) → bỏ qua, tiếp tục.
                continue

            # Thêm cặp (task_id, repeat_idx) vào set done.
            # `r.get("repeat_idx", 0)` — lấy repeat_idx, mặc định 0 nếu không có.
            done.add((r["task"], r.get("repeat_idx", 0)))
            prior.append(r)

    # Trả về tuple (set, list).
    return done, prior


# ---------------------------------------------------------------------------
# TỔNG HỢP KẾT QUẢ
# ---------------------------------------------------------------------------

def _group_rate(results: list, key: str) -> dict:
    # `defaultdict(lambda: [0, 0])` — defaultdict với factory function là lambda (hàm ẩn danh).
    # `lambda: [0, 0]` — hàm không tham số, trả về danh sách [0, 0] mỗi khi gọi.
    # Mỗi key lần đầu xuất hiện → tự động tạo [0, 0] (index 0 = số pass, index 1 = tổng).
    # Nếu dùng dict thường: phải viết if key not in agg: agg[key] = [0, 0] trước mỗi lần dùng.
    agg: dict = defaultdict(lambda: [0, 0])  # key -> [passed, total]
    for r in results:
        # `r.get(key, "?")` — lấy giá trị của key (category hoặc difficulty) từ result dict.
        # Nếu không có → dùng "?" làm nhóm.
        g = agg[r.get(key, "?")]
        # `g[1] += 1` — tăng tổng (total) lên 1.
        g[1] += 1
        # `if r["passed"]:` — nếu task pass → tăng số pass.
        if r["passed"]:
            g[0] += 1
    return agg


def write_summary(results: list, md_path: Path, ts: str) -> str:
    """Sinh báo cáo markdown: tổng quan + pass@1/pass@any + theo category/difficulty."""
    # `len(results)` — số phần tử trong danh sách results.
    total = len(results)
    # Generator expression: `sum(1 for r in results if r["passed"])`.
    # Duyệt qua results, đếm số result có passed = True.
    # sum() cộng các số 1 lại → tổng số task pass.
    passed = sum(1 for r in results if r["passed"])

    # `L = [...]` — danh sách dòng markdown, sẽ nối thành chuỗi cuối cùng.
    L = [f"# Eval results — {ts}", ""]
    # `L.append(...)` — thêm phần tử vào cuối danh sách.
    # `max(total, 1)` — tránh chia cho 0 khi total = 0.
    # `:.1f` trong f-string: định dạng float với 1 chữ số thập phân.
    L.append(f"**Overall:** {passed}/{total} runs passed "
             f"({100 * passed / max(total, 1):.1f}%).")
    L.append("")

    # Gộp các lần repeat của cùng 1 task: pass@1 (lần đầu) vs pass@any (bất kỳ lần nào).
    # defaultdict(list) — tạo dict với giá trị mặc định là list rỗng [].
    by_task: dict = defaultdict(list)
    for r in results:
        # Nhóm result theo task id.
        by_task[r["task"]].append(r)

    # Số lượng task duy nhất.
    n = len(by_task)

    # pass@1: trong mỗi task, lần đầu chạy (repeat_idx == 0) có pass không?
    # `by_task.values()` — danh sách tất cả value trong dict (mỗi value là list result).
    # `any(x["passed"] for x in rs if x["repeat_idx"] == 0)` —
    #   Lọc chỉ lấy lần chạy đầu tiên, kiểm tra có pass nào không.
    pass1 = sum(1 for rs in by_task.values()
                if any(x["passed"] for x in rs if x["repeat_idx"] == 0))

    # pass@any: trong mỗi task, CÓ BẤT KỲ lần chạy nào pass không?
    passk = sum(1 for rs in by_task.values() if any(x["passed"] for x in rs))
    L.append(f"**Tasks:** {n}  |  pass@1: {pass1}/{n} ({100 * pass1 / max(n, 1):.1f}%)"
             f"  |  pass@any: {passk}/{n} ({100 * passk / max(n, 1):.1f}%)")
    L.append("")

    # Sinh bảng markdown cho category và difficulty.
    # `for key, title in [("category", "By category"), ...]` — lặp qua list of tuples.
    for key, title in [("category", "By category"), ("difficulty", "By difficulty")]:
        # `+=` với list: nối danh sách (L += [...] tương đương L.extend([...])).
        L += [f"## {title}", "", f"| {key} | pass | total | rate |", "|---|---|---|---|"]
        agg = _group_rate(results, key)
        # `sorted(agg)` — sắp xếp các key của dict theo thứ tự bảng chữ cái.
        for g in sorted(agg):
            p, t = agg[g]
            L.append(f"| {g} | {p} | {t} | {100 * p / max(t, 1):.1f}% |")
        L.append("")

    # Thống kê theo finish_reason.
    fr: dict = defaultdict(int)  # defaultdict(int): giá trị mặc định là int() = 0
    for r in results:
        fr[r.get("finish_reason", "?")] += 1
    L += ["## Finish reasons", ""]
    # List comprehension: tạo danh sách từ iterable.
    # `[f"- {k}: {fr[k]}" for k in sorted(fr)]` — tạo dòng markdown cho mỗi finish reason.
    L += [f"- {k}: {fr[k]}" for k in sorted(fr)]
    L.append("")

    # `"\n".join(L)` — nối tất cả dòng bằng ký tự xuống dòng.
    md = "\n".join(L)
    # Ghi báo cáo markdown ra file.
    md_path.write_text(md, encoding="utf-8")
    return md


def pass_rate(results: list) -> float:
    # Tính tỷ lệ pass. Nếu results rỗng → trả về 0.0 (tránh ZeroDivisionError).
    # Biểu thức điều kiện 1 dòng: `giá_trị_nếu_đúng if điều_kiện else giá_trị_nếu_sai`.
    return sum(1 for r in results if r["passed"]) / len(results) if results else 0.0


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> int:
    # `argparse.ArgumentParser(description=...)` — tạo parser đọc tham số dòng lệnh.
    # description: mô tả hiện ra khi người dùng chạy `python run.py --help`.
    ap = argparse.ArgumentParser(description="Run the coding agent over eval tasks.")

    # `ap.add_argument(...)` — định nghĩa từng tham số dòng lệnh.
    # "filter_pos" — tên tham số vị trí (positional argument): không cần gõ --filter_pos.
    # nargs="?" — tùy chọn (0 hoặc 1 lần): có thể có hoặc không.
    # help="..." — mô tả hiện trong --help.
    ap.add_argument("filter_pos", nargs="?", help="(compat) tên 1 task, vd 01_strings")

    # "--jobs", "-j" — tham số có tên (named argument): gõ --jobs 8 hoặc -j 8.
    # type=int — chuyển string "8" thành số nguyên 8 tự động.
    # default=1 — nếu không chỉ định → mặc định là 1.
    ap.add_argument("--jobs", "-j", type=int, default=1, help="số agent chạy song song")
    ap.add_argument("--max-iters", type=int, default=20, help="trần số turn mỗi agent")

    # action="append" — mỗi lần dùng --filter thêm 1 giá trị vào list.
    # Ví dụ: --filter difficulty=hard --filter category=bench → args.filter = ["difficulty=hard", "category=bench"]
    ap.add_argument("--filter", action="append", default=[],
                    help="key=value (category/difficulty/task) hoặc glob/substring; lặp được")
    ap.add_argument("--repeats", type=int, default=1, help="chạy mỗi task K lần (pass@k)")

    # action="store_true" — nếu flag xuất hiện → giá trị True, nếu không có → False.
    # Ví dụ: --resume → args.resume = True; không có --resume → args.resume = False.
    ap.add_argument("--resume", action="store_true",
                    help="bỏ qua (task,repeat) đã có trong --out")
    ap.add_argument("--agent-timeout", type=float, default=None,
                    help="trần wall-clock mỗi task, giây (None = không giới hạn)")
    ap.add_argument("--temperature", type=float, default=None,
                    help="sampling temperature (0 = greedy/deterministic — khuyến nghị cho eval: "
                         "tool-call ổn định + kết quả tái lập)")

    # type=Path — chuyển chuỗi đường dẫn thành Path object tự động.
    ap.add_argument("--out", type=Path, default=None, help="file JSONL kết quả")
    ap.add_argument("--min-pass-rate", type=float, default=None,
                    help="nếu đặt: exit !=0 khi pass-rate dưới ngưỡng (CI gate)")
    # SkillOpt substrate: chèn skill học được vào system prompt cho MỌI rollout của lần chạy này.
    ap.add_argument("--skill-path", type=Path, default=None,
                    help="file skill (.md) chèn sau SYSTEM_PROMPT; bỏ trống = không skill (hành vi gốc)")
    # Chọn task theo danh sách tường minh (mỗi dòng 1 task-id) — OR-semantics, dùng cho
    # split train/val/test của SkillOpt. Khác --filter (vốn AND nhiều điều kiện).
    ap.add_argument("--tasks-file", type=Path, default=None,
                    help="file liệt kê task-id (mỗi dòng 1 id, vd 'bench/he_010') để chọn đúng các task đó")

    # `ap.parse_args()` — đọc sys.argv (tham số dòng lệnh thực tế) và trả về Namespace object.
    # args.jobs, args.filter, args.resume, v.v. — truy cập từng giá trị qua dấu chấm.
    args = ap.parse_args()
    # Fail-fast: --skill-path không tồn tại → exit ngay, đừng để worker chạy mới phát hiện.
    if args.skill_path is not None and not args.skill_path.exists():
        print(f"--skill-path not found: {args.skill_path}")
        return 2
    # Fail-fast: --repeats>1 + --jobs>1 = nhiều worker chấm CÙNG 1 task_dir song song. Hide/
    # snapshot/restore thao tác TẠI CHỖ trên task_dir → các repeat đua nhau xoá/khôi phục
    # test ⇒ điểm sai. Cô lập per-task chưa làm; tạm CHẶN tổ hợp này (audit HIGH).
    if args.repeats > 1 and args.jobs > 1:
        print("ERROR: --repeats>1 cùng --jobs>1 sẽ đua trên cùng task_dir (hide/restore tại chỗ). "
              "Dùng --jobs 1 cho repeats, hoặc chạy mỗi repeat ra --out riêng.")
        return 2

    # LOCK 1-eval-1-lúc: hide/snapshot/restore thao tác TẠI CHỖ trên eval/tasks dùng chung →
    # hai lần `python eval/run.py` chạy song song sẽ giẫm trạng thái giấu test của nhau (Codex
    # review #4). Lấy lock độc quyền; nếu một eval khác đang giữ (pid còn sống) → từ chối.
    if not _acquire_eval_lock():
        return 2

    # Chữa lành fixtures TRƯỚC khi chấm (sau khi có lock nên không giẫm eval khác): nếu một run
    # trước bị HARD-KILL để lại test bị xoá / code bị agent sửa, `git checkout -- eval/tasks`
    # trả về HEAD. Bỏ qua bước này thì --resume chấm trên cây bẩn → điểm sai lan ra (audit/Codex).
    _healed = heal_corrupted_tasks()
    if _healed:
        print(f"⚠ healed {_healed} corrupted fixture path(s) from a prior interrupted run (git checkout)")

    # Kiểm tra thư mục tasks tồn tại.
    if not TASKS_DIR.exists():
        print(f"No tasks dir at {TASKS_DIR}")
        # Trả về 2 = mã lỗi "usage error" (quy ước Unix).
        return 2

    # `list(args.filter)` — tạo bản sao của list filters (tránh sửa list gốc của argparse).
    filters = list(args.filter)
    # Nếu có positional argument → thêm vào danh sách filters.
    if args.filter_pos:
        filters.append(args.filter_pos)

    # Tìm tất cả task, rồi lọc theo filters.
    all_tasks = discover_tasks(TASKS_DIR)
    tasks = select_tasks(all_tasks, filters)
    # --tasks-file: nếu có, chọn ĐÚNG các task có id nằm trong file (OR-semantics),
    # ghi đè --filter. Mỗi dòng 1 task-id; dòng trống / bắt đầu '#' bị bỏ qua.
    if args.tasks_file:
        wanted = {ln.strip() for ln in args.tasks_file.read_text(encoding="utf-8").splitlines()
                  if ln.strip() and not ln.strip().startswith("#")}
        tasks = [t for t in all_tasks if rel_id(t) in wanted]
        missing = wanted - {rel_id(t) for t in all_tasks}
        if missing:
            print(f"WARNING: {len(missing)} task-id trong --tasks-file không khớp task nào: "
                  f"{sorted(missing)[:5]}{'...' if len(missing) > 5 else ''}")
    if not tasks:
        print(f"No tasks matched (discovered {len(all_tasks)} total, filters={filters})")
        return 2

    # `RESULTS_DIR.mkdir(parents=True, exist_ok=True)` — tạo thư mục kết quả nếu chưa có.
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Tạo timestamp để đặt tên file kết quả.
    # datetime.now() — thời điểm hiện tại.
    # .strftime("%Y%m%d-%H%M%S") — định dạng: năm4chữ tháng2chữ ngày2chữ - giờ phút giây.
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")

    # `args.out or (RESULTS_DIR / f"run-{ts}.jsonl")` — dùng out_path do user chỉ định,
    # hoặc tạo tên file mặc định theo timestamp nếu không có.
    # `or` trong Python: trả về vế trái nếu truthy, ngược lại trả về vế phải.
    # None or "abc" → "abc"; Path("/foo") or "abc" → Path("/foo").
    out_path = args.out or (RESULTS_DIR / f"run-{ts}.jsonl")

    # AUDITABILITY: ghi sidecar <out>.config.json → mỗi file kết quả TỰ MÔ TẢ (model, sampling,
    # giới hạn, git SHA, argv). Không có nó thì mọi so sánh A/B trong report chỉ là 2 file JSONL
    # không rõ sinh ra từ cấu hình nào (audit HIGH). Bọc try để sidecar không bao giờ làm hỏng eval.
    try:
        from src.agent import get_model
        _sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True).stdout.strip() or "unknown"
        _cfg = {"timestamp": ts, "model": get_model(), "temperature": args.temperature,
                "max_iters": args.max_iters, "agent_timeout": args.agent_timeout,
                "jobs": args.jobs, "repeats": args.repeats,
                "skill_path": str(args.skill_path) if args.skill_path else None,
                "tasks_file": str(args.tasks_file) if args.tasks_file else None,
                "git_sha": _sha, "argv": sys.argv[1:]}
        out_path.parent.mkdir(parents=True, exist_ok=True)
        _cfg_path = out_path.parent / (out_path.name + ".config.json")
        # --resume CHỈ key theo (task, repeat_idx) nên có thể trộn 2 lần chạy khác CẤU HÌNH
        # vào CÙNG 1 out file (chimera 2 model/skill). Trước khi ghi đè sidecar, nếu đang resume
        # vào file đã có và config "đồng nhất" KHÁC lần trước → cảnh báo to (audit HIGH).
        if args.resume and out_path.exists() and _cfg_path.exists():
            try:
                old = json.loads(_cfg_path.read_text(encoding="utf-8"))
                keys = ("model", "temperature", "max_iters", "agent_timeout", "skill_path")
                diff = {k: (old.get(k), _cfg.get(k)) for k in keys if old.get(k) != _cfg.get(k)}
                if diff:
                    print(f"⚠ RESUME CONFIG MISMATCH vào {out_path.name}: {diff}\n"
                          "   → out-file sẽ TRỘN kết quả của 2 cấu hình khác nhau (không đồng nhất). "
                          "Dùng --out riêng cho mỗi cấu hình để so sánh A/B chuẩn.")
            except Exception:
                pass
        _cfg_path.write_text(json.dumps(_cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

    # Thư mục chứa log từng task.
    log_dir = RESULTS_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Khởi tạo tập hợp task đã chạy và danh sách kết quả.
    done: set = set()
    results: list = []

    # --resume: đọc kết quả cũ từ file JSONL.
    if args.resume:
        done, results = load_done(out_path)
        print(f"Resume: {len(done)} (task,repeat) already done — skipping those.")

    # Xây dựng danh sách công việc cần làm: (task, repeat_idx) chưa có trong done.
    work = []
    for t in tasks:
        tid = rel_id(t)
        # `range(args.repeats)` — tạo dãy số từ 0 đến repeats-1.
        # range(3) → 0, 1, 2 (không bao gồm 3).
        for r in range(args.repeats):
            # `(tid, r) not in done` — kiểm tra cặp này chưa có trong set done.
            if (tid, r) not in done:
                # Tạo tuple payload để gửi cho worker.
                # Dùng str(t) vì Path không pickle tốt qua process boundary.
                work.append((str(t), args.max_iters, args.agent_timeout, r, str(log_dir),
                             args.temperature,
                             str(args.skill_path) if args.skill_path else None))

    total = len(work)
    print(f"Discovered {len(all_tasks)} tasks; selected {len(tasks)}; "
          f"{total} runs to do (repeats={args.repeats}, jobs={args.jobs}).")
    print(f"Results → {out_path}   (per-task logs → {log_dir})\n")

    if total:
        # `get_context("spawn")` — tạo context với start method "spawn".
        # spawn: mỗi worker process khởi động Python HOÀN TOÀN từ đầu (không copy bộ nhớ cha).
        # An toàn hơn "fork" cho code có kết nối mạng (OpenAI client, socket) vì tránh
        # chia sẻ file descriptor và kết nối đang mở giữa các process.
        ctx = get_context("spawn")  # mỗi worker re-import → OpenAI client riêng (an toàn fork).
        n_done = 0

        # Kết quả ghi NGAY khi mỗi task xong → crash giữa chừng vẫn còn file hợp lệ,
        # --resume đọc lại được. Chế độ "a" khi --resume (nối tiếp file cũ đã load ở
        # load_done); ngược lại "w" để GHI ĐÈ — tránh âm thầm nối kết quả run trước
        # vào file mặc định cùng tên (làm summary đếm trùng).
        # mode "a" = append (nối vào cuối file), "w" = write (ghi mới/ghi đè).
        mode = "a" if args.resume else "w"

        # `with open(...) as out_f, ProcessPoolExecutor(...) as ex:` — 2 context manager cùng lúc.
        # ProcessPoolExecutor(max_workers=args.jobs, mp_context=ctx):
        #   max_workers=N — tạo pool N worker process.
        #   mp_context=ctx — dùng spawn context đã tạo ở trên.
        # Khi ra khỏi `with` → tất cả worker được dọn dẹp, file được đóng.
        with open(out_path, mode, encoding="utf-8") as out_f, \
                ProcessPoolExecutor(max_workers=args.jobs, mp_context=ctx) as ex:

            # Gửi TẤT CẢ công việc vào pool ngay lập tức.
            # `ex.submit(evaluate_task, w)` — gửi 1 công việc: gọi evaluate_task(w) trong worker.
            # Trả về Future object — đại diện cho kết quả sẽ có trong tương lai.
            # Dict comprehension: {future: payload} để sau khi future hoàn thành còn lấy lại payload.
            futs = {ex.submit(evaluate_task, w): w for w in work}

            # `as_completed(futs)` — iterator trả về Future theo thứ tự HOÀN THÀNH (không phải submit).
            # Cơ chế: as_completed() dùng internal queue. Khi worker báo xong → future vào queue.
            # Vòng lặp `for fut in as_completed(futs):` sẽ BLOCK (chờ) cho đến khi có future mới xong.
            # Lợi thế: xử lý ngay kết quả mới nhất thay vì chờ tuần tự theo thứ tự submit.
            for fut in as_completed(futs):
                try:
                    # `fut.result()` — lấy giá trị trả về của evaluate_task().
                    # Nếu worker ném exception → fut.result() RE-RAISE exception đó ở đây.
                    # BLOCK cho đến khi future hoàn thành (nhưng as_completed đã đảm bảo xong rồi).
                    r = fut.result()
                except Exception as e:  # noqa: BLE001
                    # Worker process crash hoặc ném exception không bắt được → tạo result lỗi.
                    w = futs[fut]  # lấy payload tương ứng từ dict futs
                    r = {"task": rel_id(Path(w[0])), "category": "?", "difficulty": "?",
                         "passed": False, "iters_used": 0, "finish_reason": "worker_error",
                         "duration_s": 0.0, "pytest_tail": repr(e), "repeat_idx": w[3],
                         "skill_path": w[6] if len(w) > 6 else None}

                results.append(r)

                # Ghi kết quả vào file JSONL NGAY LẬP TỨC (không đợi hết run).
                # `json.dumps(r)` — chuyển dict r thành chuỗi JSON 1 dòng.
                # json.dumps = "dump string": đầu ra là chuỗi (khác json.dump ghi vào file).
                # `+ "\n"` — thêm ký tự xuống dòng để mỗi JSON object nằm trên 1 dòng riêng.
                # Đây chính là định dạng JSONL (JSON Lines).
                out_f.write(json.dumps(r) + "\n")

                # `out_f.flush()` — ĐẨY dữ liệu từ buffer trong RAM xuống đĩa NGAY.
                # Python mặc định ghi vào buffer (RAM) rồi mới flush khi buffer đầy hoặc file đóng.
                # flush() đảm bảo nếu crash ngay sau dòng này, dòng JSON vừa ghi đã an toàn trên đĩa.
                out_f.flush()

                n_done += 1
                # `"PASS" if r["passed"] else "FAIL"` — ternary expression.
                mark = "PASS" if r["passed"] else "FAIL"
                print(f"[{mark}] {r['task']} r{r['repeat_idx']} "
                      f"({r['finish_reason']}, {r['iters_used']}it, {r['duration_s']}s) "
                      f"[{n_done}/{total}]")
    else:
        print("Nothing to run (all selected runs already in --out).")

    # Sinh báo cáo tổng kết.
    # `.with_suffix(".md")` — thay đổi phần mở rộng file: run-xxx.jsonl → run-xxx.md.
    summary = write_summary(results, out_path.with_suffix(".md"), ts)
    print("\n" + summary)
    print(f"Full results: {out_path}")
    print("Reminder: stop the vLLM tmux pane when done "
          "(Ctrl-C in `tmux attach -t vllm`) — it's a shared GPU.")

    # CI gate: nếu chỉ định --min-pass-rate thì kiểm tra và trả exit code phù hợp.
    if args.min_pass_rate is not None:
        # `pass_rate(results) >= args.min_pass_rate` — so sánh float.
        # True → trả 0 (thành công); False → trả 1 (thất bại, CI sẽ mark pipeline red).
        return 0 if pass_rate(results) >= args.min_pass_rate else 1
    return 0  # hoàn thành = thành công; pass-rate là tín hiệu chất lượng, không phải exit code


# `if __name__ == "__main__":` — khối code này CHỈ CHẠY khi file được gọi trực tiếp
# (python eval/run.py), KHÔNG CHẠY khi file được import bởi module khác.
# __name__ là biến đặc biệt Python tự đặt:
#   - Khi chạy trực tiếp: __name__ = "__main__"
#   - Khi import bởi module khác: __name__ = "eval.run"
# Đây là pattern chuẩn để file vừa dùng được như script, vừa import được như module.
if __name__ == "__main__":
    # `sys.exit(main())` — chạy hàm main() và dùng giá trị trả về làm exit code.
    # sys.exit(0) = thoát thành công; sys.exit(1) = thoát có lỗi.
    # Các công cụ bên ngoài (CI, shell scripts) đọc exit code để biết thành công hay thất bại.
    sys.exit(main())
