"""
cli/solve.py — one-shot CLI wrapper around the ReAct agent in src/agent.py.

WHAT THIS FILE DOES
  Thin entry point for the demo: parses args, resolves the workspace
  directory, and calls `run_agent(task, workspace=..., max_iters=...)`. All
  real agent logic lives in `src/agent.py` — this file is just plumbing.

WHY SPLIT IT FROM src/agent.py
  Putting the CLI here lets `src/agent.py` be importable from elsewhere
  (e.g. `tests/test_agent_loop.py` mocking the LLM) without invoking
  argparse / sys.exit. Same separation-of-concerns as Click apps that
  put their CLI in __main__ and the logic in a library module.

DEMO COMMAND (the exact line to run during the prof checkpoint)
  cd ~/code/coding-agent && source .venv/bin/activate
  python cli/solve.py "Fix the failing test in demo_repo/"

OPTIONAL FLAGS
  --max-iters N      cap on agent turns (default 15)
  --workspace PATH   directory the tools may read/write (default demo_repo)
"""

# ---------------------------------------------------------------------------
# `from __future__ import annotations`
# ---------------------------------------------------------------------------
# `from __future__ import annotations` là câu lệnh ĐẶC BIỆT của Python.
# Từ khóa `from` nghĩa là "lấy từ module nào đó".
# `__future__` (đọc: "dunder future") là module đặc biệt chứa các tính năng
# Python MỚI HƠN mà bạn muốn bật ngay trong phiên bản Python hiện tại.
# `import annotations` bật lazy evaluation cho type hints:
#   - Bình thường: `list[dict]` được Python tính toán ngay → lỗi trên Python 3.8.
#   - Sau dòng này: `list[dict]` chỉ là chuỗi ký tự, không tính ngay → tương thích 3.8+.
# QUY TẮC BẮT BUỘC: dòng này phải là dòng code ĐẦU TIÊN trong file,
# trước mọi import khác (chỉ sau docstring và comments).
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

# `logging` — thư viện chuẩn để ghi nhật ký (log).
# Logging quan trọng hơn print() vì:
#   - Có CẤP ĐỘ: DEBUG < INFO < WARNING < ERROR < CRITICAL.
#   - Có thể BẬT/TẮT theo cấp độ mà không cần xóa code.
#   - Tự động thêm timestamp, tên module, cấp độ vào mỗi dòng log.
# Cách dùng: `log = logging.getLogger("tên_module")`, sau đó `log.info("...")`.
import logging

# `os` — thư viện chuẩn tương tác với hệ điều hành (Operating System).
# Ở đây dùng `os.environ` để đọc biến môi trường (environment variables).
# Biến môi trường là cặp KEY=VALUE mà shell/OS cung cấp cho chương trình.
# Ví dụ: trong terminal bạn chạy `export VLLM_MODEL_NAME=Qwen3-14B`,
# sau đó `os.environ.get("VLLM_MODEL_NAME")` trả về "Qwen3-14B".
import os

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

# ---------------------------------------------------------------------------
# SỬA sys.path ĐỂ IMPORT ĐƯỢC src/
# ---------------------------------------------------------------------------
# VẤNỀ: Khi bạn gõ `python cli/solve.py`, Python khởi động với sys.path chứa:
#   1. Thư mục chứa file đang chạy: `/home/tle/code/coding-agent/cli`
#   2. Các thư mục cài đặt Python (site-packages, stdlib...)
#
# Python TÌM KIẾM module theo thứ tự trong sys.path. Vì vậy nếu bạn viết
# `from src.agent import run_agent`, Python tìm:
#   - `/home/tle/code/coding-agent/cli/src/agent.py` → KHÔNG CÓ (sai!)
#   - Các thư mục site-packages → KHÔNG CÓ
#   → ImportError: No module named 'src'
#
# GIẢI PHÁP: Thêm PROJECT ROOT vào đầu sys.path TRƯỚC khi import src/.
#
# GIẢI THÍCH TỪNG BƯỚC của `Path(__file__).resolve().parent.parent`:
# ┌────────────────────────────────────────────────────────────────────┐
# │ BƯỚC 1: __file__                                                   │
# │   `__file__` là biến đặc biệt Python tự đặt khi load file.        │
# │   "dunder file" (đọc: double-underscore file).                     │
# │   Giá trị: đường dẫn đến file đang chạy.                          │
# │   Ví dụ: "/home/tle/code/coding-agent/cli/solve.py"               │
# │   Có thể là đường dẫn tương đối nếu gọi bằng relative path.       │
# │                                                                    │
# │ BƯỚC 2: Path(__file__)                                             │
# │   Bọc chuỗi __file__ thành Path object để có thể dùng .resolve(). │
# │   Path("/home/tle/code/coding-agent/cli/solve.py")                 │
# │                                                                    │
# │ BƯỚC 3: .resolve()                                                 │
# │   Chuyển đường dẫn tương đối → tuyệt đối.                         │
# │   Giải quyết symlinks (symbolic links = shortcut).                 │
# │   Kết quả: đường dẫn đầy đủ, canonical.                           │
# │   Path("/home/tle/code/coding-agent/cli/solve.py") (already abs)   │
# │                                                                    │
# │ BƯỚC 4: .parent (lần 1)                                            │
# │   Thuộc tính `.parent` trả về thư mục chứa file/thư mục này.      │
# │   Path("/home/tle/code/coding-agent/cli/solve.py").parent          │
# │      → Path("/home/tle/code/coding-agent/cli")                     │
# │   (Thư mục cli/ chứa file solve.py)                                │
# │                                                                    │
# │ BƯỚC 5: .parent (lần 2)                                            │
# │   Một lần nữa lấy thư mục cha.                                     │
# │   Path("/home/tle/code/coding-agent/cli").parent                   │
# │      → Path("/home/tle/code/coding-agent")   ← PROJECT ROOT!      │
# │   (Thư mục coding-agent/ chứa cli/)                                │
# └────────────────────────────────────────────────────────────────────┘
#
# SAU KHI có project root:
# `str(...)` — chuyển Path object thành chuỗi vì sys.path là list[str].
# `sys.path.insert(0, chuỗi)` — CHÈN vào VỊ TRÍ 0 (đầu tiên) của sys.path.
#
# TẠI SAO INSERT Ở ĐẦU chứ không APPEND ở cuối?
#   Python tìm module theo thứ tự TỪ ĐẦU ĐẾN CUỐI sys.path.
#   Nếu append → project root ở cuối → Python tìm qua tất cả site-packages
#   trước, rủi ro gặp package cùng tên (ví dụ: nếu có pip install src).
#   Insert ở đầu → project root được ưu tiên tìm TRƯỚC → an toàn và nhanh.
#
# KẾT QUẢ: Sau dòng này, `from src.agent import run_agent` sẽ tìm thấy
# `/home/tle/code/coding-agent/src/agent.py` → import thành công.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# `from dotenv import load_dotenv` — import hàm từ thư viện bên thứ ba (third-party).
# `dotenv` (tên đầy đủ: python-dotenv) đọc file `.env` trong thư mục hiện tại.
# File `.env` chứa các cặp KEY=VALUE, ví dụ:
#   VLLM_BASE_URL=http://localhost:8000/v1
#   VLLM_MODEL_NAME=Qwen3-14B-Instruct
# `load_dotenv()` nạp các cặp này vào `os.environ` để code đọc được.
# Giúp không phải hardcode URL/key trong code hoặc export thủ công mỗi lần.
from dotenv import load_dotenv

# Import the agent module. We re-use ITS client, logger, run_agent — no
# duplication of API/env setup here.
# `from src.agent import run_agent` — import CHỈ hàm run_agent từ module src.agent.
# `src.agent` = file `src/agent.py` tương đối với project root.
# `run_agent` = hàm chính chạy toàn bộ vòng lặp ReAct agent.
# Nhờ sys.path.insert ở trên, Python tìm thấy src/agent.py.
from src.agent import run_agent


# ---------------------------------------------------------------------------
# HÀM main — ĐIỂM VÀO CHƯƠNG TRÌNH
# ---------------------------------------------------------------------------
# `def main() -> int:` — định nghĩa hàm tên `main`, trả về kiểu `int`.
# `def` là từ khóa Python để ĐỊNH NGHĨA hàm.
# `->` là ký hiệu type hint cho kiểu trả về.
# `int` = số nguyên. Hàm trả về exit code: 0 = thành công, khác 0 = lỗi.
def main() -> int:
    # `load_dotenv()` — đọc file .env và nạp vào os.environ.
    # Gọi ở đây (không phải top-level) để test dễ mock hơn.
    load_dotenv()

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
    # LOG THÔNG TIN TRƯỚC KHI CHẠY
    # ---------------------------------------------------------------------------
    # `logging.getLogger("agent")` — lấy logger tên "agent".
    # Logging có hierarchy: "agent.tools", "agent.stream" đều là con của "agent".
    # Dùng logger thay vì print() để có thể bật/tắt theo level.
    log = logging.getLogger("agent")
    log.info("=" * 60)
    # `os.environ.get("KEY", "?")` — lấy biến môi trường, mặc định "?" nếu chưa set.
    # An toàn hơn os.environ["KEY"] vì không crash khi key không tồn tại.
    log.info(f"  model    : {os.environ.get('VLLM_MODEL_NAME', '?')}")
    log.info(f"  endpoint : {os.environ.get('VLLM_BASE_URL', '?')}")
    log.info(f"  workspace: {args.workspace}")
    log.info(f"  max_iters: {args.max_iters}")
    log.info(f"  goal     : {task_text}")
    log.info("=" * 60)

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
        log.info("\nInterrupted.")
        # `return 130` — trả về exit code 130.
        # Quy ước Unix: exit code 128+N = bị tín hiệu N. Ctrl+C gửi SIGINT (signal 2).
        # 128 + 2 = 130 → báo shell biết "chương trình bị interrupt".
        return 130
    # `return 0` — trả về 0 = thành công (không có lỗi).
    return 0


# ---------------------------------------------------------------------------
# ENTRY POINT — ĐIỂM KHỞI CHẠY
# ---------------------------------------------------------------------------
# `if __name__ == "__main__":` — PATTERN CHUẨN Python, cực kỳ quan trọng.
#
# `__name__` (đọc: "dunder name") là biến Python tự đặt:
# ┌──────────────────────────────────────────────────────────────────┐
# │ TRƯỜNG HỢP 1: CHẠY TRỰC TIẾP                                    │
# │   Lệnh: `python cli/solve.py "Fix bug"`                          │
# │   Python đặt: __name__ = "__main__"                              │
# │   Điều kiện: "__main__" == "__main__" → True                     │
# │   Kết quả: sys.exit(main()) ĐƯỢC CHẠY                            │
# │                                                                  │
# │ TRƯỜNG HỢP 2: ĐƯỢC IMPORT TỪ FILE KHÁC                          │
# │   Lệnh: `import solve` (trong file khác, ví dụ test_solve.py)   │
# │   Python đặt: __name__ = "solve" (tên module)                   │
# │   Điều kiện: "solve" == "__main__" → False                       │
# │   Kết quả: sys.exit(main()) KHÔNG CHẠY                           │
# │   → Chỉ import hàm main, không chạy ngay                         │
# └──────────────────────────────────────────────────────────────────┘
#
# TẠI SAO CẦN PATTERN NÀY?
#   Nếu không có block này, `sys.exit(main())` chạy ở TOP LEVEL — nghĩa là
#   chạy MỖI KHI file được load, kể cả khi pytest import để test.
#   Block này ngăn side effects khi import, cho phép test riêng từng hàm.
#
# `sys.exit(main())`:
#   1. Gọi main() trước, nhận exit code (int).
#   2. Truyền vào sys.exit(): thoát chương trình với exit code đó.
#   3. Shell nhận exit code: 0 = OK, 1+ = lỗi, 130 = interrupted.
#   Ví dụ: `python solve.py "task" && echo "success"` → chỉ in "success" nếu exit 0.
if __name__ == "__main__":
    sys.exit(main())
