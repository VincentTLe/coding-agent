"""
cli/solve.py — one-shot CLI wrapper around the ReAct agent in src/agent.py.

WHAT THIS FILE DOES
  Thin entry point for the demo: parses args, resolves the workspace
  directory, and calls `run_agent(task, workspace=..., max_iters=...)`. All
  real agent logic lives in `src/agent.py` — this file is just plumbing.

WHY SPLIT IT FROM src/agent.py
  Putting the CLI here lets `src/agent.py` be importable from elsewhere
  (e.g. `tests/test_agent.py` mocking the LLM) without invoking
  argparse / sys.exit. Same separation-of-concerns as Click apps that
  put their CLI in __main__ and the logic in a library module.

DEMO COMMAND (the exact line to run during the prof checkpoint)
  cd ~/code/coding-agent && source .venv/bin/activate
  python cli/solve.py "Fix the failing test in demo_repo/"

OPTIONAL FLAGS
  --max-iters N      cap on agent turns (default 15)
  --workspace PATH   directory the tools may read/write (default demo_repo)
"""

# `from __future__ import annotations` — bật lazy type hints (`list[dict]` chỉ
# là chuỗi, không bị tính ngay). Xem giải thích chi tiết trong eval/run.py.
from __future__ import annotations

# ---------------------------------------------------------------------------
# CÁC IMPORT CẦN THIẾT
# ---------------------------------------------------------------------------
# `import tên_module` — nhập toàn bộ module vào không gian tên hiện tại.
# Sau đó dùng bằng `tên_module.hàm_hoặc_biến`.

# `argparse` — thư viện chuẩn (stdlib) của Python để PHÂN TÍCH THAM SỐ DÒNG LỆNH.
# "Tham số dòng lệnh" (command-line arguments) là những gì bạn gõ sau tên chương trình.
# Ví dụ: `python solve.py "Fix the bug" --max-iters 20 --workspace /tmp/sandbox`
#   - "Fix the bug"     → positional argument (tham số vị trí, không có --)
#   - --max-iters 20    → optional argument (tham số tùy chọn, có --)
#   - --workspace /tmp  → optional argument khác
# argparse:
#   1. Định nghĩa các argument nào được chấp nhận.
#   2. Đọc sys.argv (list chuỗi gõ vào terminal).
#   3. Phân tích và trả về object Namespace với các thuộc tính.
#   4. Tự động tạo thông báo --help.
#   5. Báo lỗi nếu argument sai kiểu hoặc thiếu argument bắt buộc.
import argparse

# `sys` — thư viện chuẩn tương tác với Python runtime.
# Các dùng thường gặp:
#   `sys.path`   → list thư mục Python tìm module khi import.
#   `sys.argv`   → list argument dòng lệnh (sys.argv[0] = tên file).
#   `sys.exit(n)` → thoát chương trình với exit code n.
#   `sys.stdin`  → luồng input chuẩn (keyboard).
#   `sys.stdout` → luồng output chuẩn (màn hình).
import sys

# `Path` từ thư viện `pathlib` — đối tượng đại diện cho đường dẫn file/thư mục.
# Ưu điểm so với chuỗi thuần:
#   - Portable: tự xử lý `/` (Unix) vs `\` (Windows).
#   - Có nhiều phương thức tiện lợi: .exists(), .parent, .resolve(), .stem...
#   - Toán tử `/` nối path: Path("/home") / "user" / "file.txt" → Path("/home/user/file.txt")
from pathlib import Path

# Thêm project root vào sys.path TRƯỚC khi import src/ — khi chạy
# `python cli/solve.py`, Python chỉ thấy thư mục cli/, không thấy src/.
# Xem giải thích chi tiết từng bước trong eval/run.py.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Tái dùng toàn bộ hạ tầng của src/agent.py — không duplicate API/env setup:
#   - run_agent           : hàm chính chạy vòng lặp ReAct agent.
#   - load_model_config() : ModelConfig active (models.json, fallback .env) —
#     banner in model/endpoint từ ĐÚNG nguồn mà get_client() sẽ dùng, thay vì
#     đọc lại VLLM_* env vars có thể lệch với models.json (misreport khi demo).
#     Hàm này tự gọi load_dotenv() nên ở đây không cần import dotenv nữa.
from src.agent import load_model_config, run_agent


# ---------------------------------------------------------------------------
# HÀM main — ĐIỂM VÀO CHƯƠNG TRÌNH
# ---------------------------------------------------------------------------
# `def main() -> int:` — định nghĩa hàm tên `main`, trả về kiểu `int`.
# `def` là từ khóa Python để ĐỊNH NGHĨA hàm.
# `->` là ký hiệu type hint cho kiểu trả về.
# `int` = số nguyên. Hàm trả về exit code: 0 = thành công, khác 0 = lỗi.
def main() -> int:
    # Không gọi load_dotenv() ở đây nữa — load_model_config() (gọi bên dưới)
    # và get_client() (bên trong run_agent) đều tự load .env khi cần.

    # ---------------------------------------------------------------------------
    # ARGPARSE — PHÂN TÍCH THAM SỐ DÒNG LỆNH
    # ---------------------------------------------------------------------------
    # `argparse.ArgumentParser(description=...)` — tạo object "bộ phân tích".
    # `description` = đoạn mô tả hiện khi user gõ `python solve.py --help`.
    parser = argparse.ArgumentParser(
        description="Run the from-scratch coding agent on a single task.",
    )

    # `parser.add_argument("task", ...)` — định nghĩa POSITIONAL argument.
    # POSITIONAL argument: không có dấu `--` trước, vị trí trong dòng lệnh xác định ý nghĩa.
    # Ví dụ: `python solve.py "Fix the bug"` → "Fix the bug" là positional argument "task".
    #
    # `nargs="+"` — số lượng giá trị:
    #   nargs="+"  → 1 hoặc nhiều giá trị (list).
    #   nargs="?"  → 0 hoặc 1 giá trị.
    #   nargs="*"  → 0 hoặc nhiều giá trị (list).
    #   nargs=N    → đúng N giá trị.
    # Dùng nargs="+" để user có thể gõ task KHÔNG CẦN dấu ngoặc kép:
    #   `python solve.py Fix the failing test`
    #   → args.task = ["Fix", "the", "failing", "test"]
    #   Sau đó " ".join(args.task) → "Fix the failing test"
    # Nếu nargs=None (mặc định), chỉ nhận 1 từ — phải thêm dấu ngoặc kép.
    parser.add_argument(
        "task",
        nargs="+",
        help="Goal for the agent, e.g. 'Fix the failing test in demo_repo/'.",
    )

    # `--max-iters` — optional argument (có --).
    # `type=int` — argparse tự chuyển chuỗi "15" thành số nguyên 15.
    #   Nếu không có `type=int`, args.max_iters sẽ là chuỗi "15", không phải số 15.
    # `default=15` — nếu user không truyền --max-iters, mặc định là 15.
    parser.add_argument(
        "--max-iters", type=int, default=15,
        help="Maximum agent turns before giving up (default: 15).",
    )

    # `--workspace` — optional argument chỉ thư mục làm việc.
    # `default=str(Path(...) / "demo_repo")`:
    #   Path(__file__).resolve().parent.parent → project root (đã giải thích trên)
    #   / "demo_repo" → toán tử `/` trên Path nối thêm "demo_repo" vào cuối path.
    #   Đây KHÔNG phải chia số — đây là toán tử nối path của thư viện pathlib.
    #   Ví dụ: Path("/home/tle/project") / "demo_repo" = Path("/home/tle/project/demo_repo")
    #   str(...) → chuyển thành chuỗi cho argparse lưu (argparse lưu chuỗi, không phải Path).
    parser.add_argument(
        "--workspace",
        default=str(Path(__file__).resolve().parent.parent / "demo_repo"),
        help="Directory the tools (read/write/bash) are confined to.",
    )

    # `args = parser.parse_args()` — thực sự phân tích dòng lệnh.
    # Đọc `sys.argv` (list tất cả token gõ vào terminal).
    # Trả về object `Namespace` với thuộc tính tương ứng tên argument:
    #   args.task          → list chuỗi (do nargs="+")
    #   args.max_iters     → int (do type=int, lưu ý: "--max-iters" → args.max_iters)
    #   args.workspace     → chuỗi
    # Nếu argument bắt buộc thiếu hoặc sai kiểu: argparse tự in lỗi và exit(2).
    args = parser.parse_args()

    # ---------------------------------------------------------------------------
    # VALIDATE VÀ CHUẨN BỊ THAM SỐ
    # ---------------------------------------------------------------------------
    # Validate input TRƯỚC khi giải quyết workspace — không chạy cho 1 lần
    # gọi sai (vd task rỗng). parser.error() in usage rồi exit(2).
    #
    # `" ".join(args.task)` — nối list chuỗi thành 1 chuỗi, ngăn cách bằng dấu cách.
    # Ví dụ: ["Fix", "the", "bug"] → "Fix the bug"
    # `.join(iterable)` là phương thức của chuỗi:
    #   - Gọi trên chuỗi ngăn cách: " ".join(...) → dùng dấu cách.
    #   - Tham số: bất kỳ iterable chứa chuỗi.
    # `.strip()` — xóa khoảng trắng đầu/cuối (phòng trường hợp user gõ nhầm).
    task_text = " ".join(args.task).strip()

    # `if not task_text:` — nếu task_text là chuỗi rỗng "" sau strip().
    # Chuỗi rỗng là falsy trong Python, `not ""` = True.
    if not task_text:
        # `parser.error(msg)` — in thông báo lỗi chuẩn argparse và thoát với exit code 2.
        # Tại sao không dùng print() + sys.exit()?
        # parser.error() tự động thêm tên chương trình và format đúng chuẩn argparse.
        parser.error("task must not be empty")

    # Chốt sandbox (file ops + bash CWD) vào workspace rồi truyền thẳng vào
    # run_agent. .resolve() ở đây → mọi tool đọc/ghi đều bị _safe_path() kẹp
    # trong thư mục này, agent không thể leo ra sửa src/ hay /etc. Đây là
    # ranh giới an toàn DUY NHẤT — workspace giờ là param tường minh, không
    # còn global set_workspace() nữa.
    #
    # `Path(args.workspace)` — bọc chuỗi workspace thành Path object.
    # `.resolve()` — chuyển thành absolute path (tuyệt đối).
    #   Ví dụ: "demo_repo" (tương đối) → "/home/tle/code/coding-agent/demo_repo" (tuyệt đối).
    #   Tại sao cần tuyệt đối? Vì khi agent chạy bash, working directory có thể thay đổi.
    #   Absolute path luôn trỏ đúng nơi bất kể cwd hiện tại là gì.
    workspace = Path(args.workspace).resolve()

    # ---------------------------------------------------------------------------
    # BANNER TRƯỚC KHI CHẠY
    # ---------------------------------------------------------------------------
    # Dùng print() chứ KHÔNG dùng log.info(): logging chỉ được cấu hình BÊN
    # TRONG run_agent (_setup_logging) — tại điểm này chưa có handler nào,
    # log.info() bị nuốt im lặng nên banner cũ chưa bao giờ in ra.
    #
    # model/endpoint đọc từ load_model_config() — cùng nguồn (models.json,
    # fallback .env) mà get_client() dùng để gửi request thật. Bản cũ đọc
    # VLLM_* env vars trực tiếp, có thể lệch với models.json → banner báo
    # sai model đang chạy ngay giữa demo.
    cfg = load_model_config()
    print("=" * 60)
    print(f"  model    : {cfg.model}")
    print(f"  endpoint : {cfg.base_url}")
    print(f"  workspace: {args.workspace}")
    print(f"  max_iters: {args.max_iters}")
    print(f"  goal     : {task_text}")
    print("=" * 60)

    # ---------------------------------------------------------------------------
    # CHẠY AGENT
    # ---------------------------------------------------------------------------
    # `try: ... except ...: ...` — xử lý ngoại lệ (exception handling).
    # Chạy `run_agent(...)` trong try để bắt lỗi "user ngắt" (Ctrl+C, Ctrl+D).
    try:
        # `run_agent(task_text, workspace=workspace, max_iters=args.max_iters)`
        # Gọi hàm run_agent từ src/agent.py.
        # `workspace=workspace` — KEYWORD ARGUMENT: truyền bằng tên tham số.
        #   Khác positional argument (truyền theo vị trí):
        #   run_agent(task_text, workspace, 15) — positional
        #   run_agent(task_text, workspace=workspace, max_iters=15) — keyword
        #   Keyword argument: thứ tự không quan trọng, rõ ràng hơn.
        run_agent(task_text, workspace=workspace, max_iters=args.max_iters)
    except (KeyboardInterrupt, EOFError):
        # `KeyboardInterrupt` — user bấm Ctrl+C. Python ném exception này.
        # `EOFError` — stdin đóng (ví dụ: piped input hết dữ liệu, Ctrl+D).
        # Bắt cả hai vì cả hai đều nghĩa là "user muốn dừng".
        # `(Err1, Err2)` — bắt nhiều loại exception trong 1 except block.
        # print() thay vì log.info() — nhất quán với banner, và vẫn hiện
        # được cả khi Ctrl+C đến trước lúc run_agent kịp cấu hình logging.
        print("\nInterrupted.")
        # `return 130` — trả về exit code 130.
        # Quy ước Unix: exit code 128+N = bị tín hiệu N. Ctrl+C gửi SIGINT (signal 2).
        # 128 + 2 = 130 → báo shell biết "chương trình bị interrupt".
        return 130
    # `return 0` — trả về 0 = thành công (không có lỗi).
    return 0


# `if __name__ == "__main__":` — chỉ chạy main() khi file được gọi trực tiếp
# (`python cli/solve.py "task"`), không chạy khi bị import. Xem giải thích
# chi tiết về pattern này trong eval/run.py.
# Exit code từ main() (0 = OK, 130 = Ctrl+C) được truyền cho shell qua sys.exit.
if __name__ == "__main__":
    sys.exit(main())
