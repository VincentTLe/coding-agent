"""
agent.py — ReAct-style coding agent that uses tools to complete a task.

WHAT THIS FILE DOES
  Takes a natural-language goal (e.g. "Fix the failing tests in demo_repo/"),
  calls an LLM that may invoke any of the 11 tools defined in src/tools.py
  (read_file, write_file, apply_patch, multi_edit, grep_files, glob_files,
  list_dir, run_bash, run_python, spawn_subagent, finish), and keeps looping.
  Termination: model gọi finish(), hoặc trả lời không tool_calls SAU KHI đã
  hành động; trả lời chay TRƯỚC KHI hành động bị nudge tối đa 2 lần rồi tính
  là no_action; hết `max_iters` hoặc time budget thì dừng với lý do tương ứng.

KEY DIFFERENCE FROM 01_chat.py
  01_chat.py only had `messages` + `content`. Here we ALSO have:
    - `tools=TOOL_SCHEMAS` in the API call (tell model what it can call)
    - `msg.tool_calls` to read (what the model wants to call)
    - role="tool" messages we append back (results of calls)

THE REACT LOOP (the heart of every modern coding agent — Claude/Codex use this)
   1. Send messages + tool schemas to the LLM.
   2. LLM responds either with plain content (it's done) OR with one or
      more tool_calls (it wants to do something).
   3. If content-only -> return. If tool_calls -> execute each, append the
      tool result to messages, loop.
   4. Stop if we exceed max_iters as a safety net.

WHEN DONE
  cd ~/code/coding-agent && source .venv/bin/activate
  python -m src.agent "Fix the failing tests in demo_repo/"
  (Or use cli/solve.py — the human-facing one-shot CLI; cli/chat.py is the REPL.)
"""

# `from __future__ import annotations` là dòng đặc biệt giúp Python 3.9 hiểu
# kiểu dữ liệu mới hơn viết trong type hints (ví dụ: float | None thay vì
# Union[float, None]). Nó KHÔNG thay đổi logic chương trình, chỉ ảnh hưởng
# đến cách Python đọc các chú thích kiểu dữ liệu (type hints).
# Phải đặt ở dòng đầu tiên của file (sau docstring).
from __future__ import annotations

# `import logging` — nhập (import) module logging sẵn có trong Python.
# "Module" là một file Python chứa các hàm và lớp ta có thể dùng lại.
# `import` = "hãy tải module này vào, tôi muốn dùng nó".
# `logging` thay cho `print()` — sau này có thể redirect log vào file để
# thu thập trace cho fine-tuning ở Phase 3. Đây là Rule C trong AGENTS.md.
import logging

# `import os` — nhập module os (operating system).
# Module này cho phép tương tác với hệ điều hành: đọc biến môi trường,
# kiểm tra file tồn tại không, v.v.
import os

# `import sys` — dùng sys.stderr cho handler logging "động" (xem _DynamicStderrHandler):
# eval redirect_stderr cho từng task nên log phải bám sys.stderr TẠI LÚC ghi, không bind cứng.
import sys

# `import time` — nhập module time.
# Dùng để đo thời gian (time.monotonic() trả về số giây kể từ một điểm
# tham chiếu cố định — dùng để tính xem đã chạy bao nhiêu giây).
import time

# `from pathlib import Path` — từ module pathlib, chỉ lấy lớp Path.
# Cú pháp `from X import Y` = "từ module X, chỉ nhập phần Y".
# Path là cách Python hiện đại xử lý đường dẫn file/thư mục —
# thay vì viết chuỗi như "/home/user/demo_repo", ta dùng Path("/home/user/demo_repo")
# và có các phương thức tiện lợi như .resolve(), .exists(), .name, v.v.
from pathlib import Path
import json
from dataclasses import dataclass
from functools import lru_cache

# `from dotenv import load_dotenv` — nhập hàm load_dotenv từ thư viện python-dotenv.
# Hàm này đọc file .env (chứa cấu hình bí mật như API key, URL) và nạp
# các cặp KEY=VALUE vào os.environ (từ điển biến môi trường của tiến trình).
# Đọc biến môi trường từ .env (BASE_URL, MODEL_NAME, API_KEY) — y hệt 01_chat.py.
from dotenv import load_dotenv

# `from openai import OpenAI, OpenAIError` — từ thư viện openai, nhập 2 thứ:
#   - OpenAI: lớp (class) để tạo client kết nối với API. Ta sẽ gọi
#     OpenAI(base_url=..., api_key=...) để tạo đối tượng client.
#   - OpenAIError: lớp cơ sở (base class) của MỌI lỗi SDK — khi kết nối
#     thất bại, server trả 5xx, hay context quá dài (400), Python sẽ
#     "throw" (ném ra) một OpenAIError. Ta "bắt" nó bằng try/except.
# OpenAI SDK — bao bọc HTTP/JSON, cho phép swap backend bằng cách đổi base_url.
# `OpenAIError` là base class của MỌI lỗi SDK (timeout, 5xx, kết nối rớt, 400 do
# context tràn). Bắt nó ở vòng lặp để 1 lỗi transient không kill cả run_agent —
# xem BƯỚC 1 bên dưới để hiểu vì sao việc này quan trọng cho tính đúng đắn.
from openai import OpenAI, OpenAIError

# TypedDict cho 1 message — chỉ dùng type hint giúp Pylance không kêu
# "list[dict] không phải Iterable[ChatCompletionMessageParam]" khi truyền vào create().
# ChatCompletionMessageParam là kiểu dữ liệu đặc biệt mô tả hình dạng của 1 message:
# phải có 'role' và 'content'. Dùng để IDE kiểm tra ta không gõ sai key.
from openai.types.chat import ChatCompletionMessageParam

# Lấy 2 thứ từ tools.py:
#   - TOOL_SCHEMAS: danh sách JSON schema mô tả tools (model nhìn vào để biết gọi sao)
#   - execute_tool: dispatcher chạy tool theo name + args + workspace (sandbox dir)
# Lưu ý: KHÔNG còn `set_workspace` — workspace nay là tham số tường minh truyền
# thẳng vào execute_tool() ở mỗi lời gọi (xem run_agent), không phải global.
from src.tools import TOOL_SCHEMAS, execute_tool

# `from src.prompts import SYSTEM_PROMPT` — nhập biến SYSTEM_PROMPT từ file
# src/prompts.py. Đây là chuỗi dài mô tả cách agent phải hoạt động.
# System prompt — tách ra file riêng để sau này dễ versioning cho training data.
# build_system_prompt: ghép skill học được (SkillOpt) vào sau SYSTEM_PROMPT.
from src.prompts import SYSTEM_PROMPT, build_system_prompt


# ---------------------------------------------------------------------------
# ANSI color codes — tô màu output để prof nhìn dễ phân biệt từng phần.
# Không cần thư viện ngoài, chỉ là escape codes terminal hiểu sẵn.
# ---------------------------------------------------------------------------

# Mỗi mã ANSI là chuỗi đặc biệt báo terminal "đổi màu chữ kể từ đây".
# `\033[XXm` = bắt đầu màu. `\033[0m` = reset về mặc định.
#
# `class Color:` — định nghĩa một LỚP (class) tên Color.
# Class là "khuôn mẫu" gom nhóm dữ liệu liên quan lại với nhau.
# Ở đây ta không dùng class để tạo đối tượng phức tạp — chỉ dùng như
# "namespace" (không gian tên) để gom các hằng số màu vào 1 chỗ.
# Thay vì viết COLOR_HEADER = "..." rải rác, ta gom vào Color.HEADER,
# Color.TOOL, v.v. — rõ ràng và dễ tìm hơn.
class Color:
    # Các dòng bên trong class đều được thụt vào 4 dấu cách — Python dùng
    # thụt đầu dòng (indentation) để xác định phạm vi (scope).
    # Mỗi biến bên trong class (không có def) gọi là "class attribute"
    # (thuộc tính lớp) — dùng bằng cách viết Color.HEADER, Color.TOOL, v.v.

    HEADER = "\033[1;34m"   # bold blue — cho dòng "=== Turn N ==="
    THINKING = "\033[97m"   # bright white — thinking stream của model (cli/chat.py dùng)
    TOOL = "\033[1;32m"     # bold green — cho dòng "[tool] tool_name(...)"
    RESULT = "\033[33m"     # yellow — cho dòng "[tool result]"
    ASSISTANT = "\033[1;35m"  # bold magenta — cho "[assistant] ..."
    FINISH = "\033[1;36m"   # bold cyan — cho "Agent finished."
    WARN = "\033[1;31m"     # bold red — cho cảnh báo
    RESET = "\033[0m"       # tắt mọi màu — phải có sau mỗi đoạn màu


# `def cprint(color: str, text: str) -> None:` — định nghĩa HÀM tên cprint.
# `def` là từ khóa Python dùng để khai báo hàm. Cú pháp:
#   def <tên_hàm>(<tham_số_1>: <kiểu_1>, <tham_số_2>: <kiểu_2>) -> <kiểu_trả_về>:
# Hàm là đoạn code được đặt tên, có thể gọi đi gọi lại.
# `color: str` = tham số color phải là chuỗi ký tự (str = string).
# `text: str` = tham số text cũng là chuỗi.
# `-> None` = hàm này KHÔNG trả về giá trị gì (None = "không có gì").
def cprint(color: str, text: str) -> None:
    """In ra text có màu. Dùng `log.info` thay vì `print` để consistent.

    Tại sao tách hàm này? — Tránh lặp `{Color.X}...{Color.RESET}` ở 5 chỗ.
    """
    # `log.info(...)` — gọi phương thức info trên đối tượng log.
    # Phương thức (method) là hàm "gắn liền" với một đối tượng, gọi bằng dấu chấm.
    # log.info() in ra một dòng log với mức độ INFO.
    #
    # `f"{color}{text}{Color.RESET}"` — đây là f-string (formatted string).
    # f-string = chuỗi bắt đầu bằng chữ f trước dấu nháy.
    # Bên trong f-string, mọi thứ nằm trong {} sẽ được tính toán và chèn vào chuỗi.
    # Ví dụ: f"Xin chào {name}" với name="An" → "Xin chào An"
    # Ở đây: {color} chèn mã màu ANSI, {text} chèn nội dung, {Color.RESET} tắt màu.
    log.info(f"{color}{text}{Color.RESET}")


# ---------------------------------------------------------------------------
# Setup (LAZY — KHÔNG side-effect ở import)
#
# Trước đây file này đọc .env, dựng OpenAI client và gọi logging.basicConfig
# NGAY ở top level → chỉ cần `import src.agent` là đã require .env + cấu hình
# logging toàn cục cho cả tiến trình. Điều đó làm import có tác dụng phụ: eval
# harness / examples / test import module này sẽ crash nếu thiếu .env, và việc
# basicConfig chạy lúc import giẫm lên cấu hình logging của caller.
#
# Cách sửa: ĐẨY mọi thứ vào hàm lazy, chỉ chạy khi run_agent thực sự cần:
#   - get_client(): singleton — lần đầu mới load_dotenv + đọc env + dựng client.
#   - logging: cấu hình 1 lần bên trong run_agent qua _setup_logging() (có guard).
# => `import src.agent` giờ KHÔNG dựng client, KHÔNG cần env, KHÔNG đụng logging.
# ---------------------------------------------------------------------------

# `log = logging.getLogger("agent")` — lấy (hoặc tạo) một logger có tên "agent".
# Logger là đối tượng dùng để ghi log. Nếu gọi getLogger("agent") 2 lần,
# Python trả về cùng 1 đối tượng — getLogger không tạo mới, chỉ tra cứu.
# `log` chỉ là một logger object — lấy logger KHÔNG có side-effect (không cấu
# hình gì), nên để ở module level vẫn an toàn. Việc CẤU HÌNH (basicConfig) mới
# là thứ phải hoãn lại tới run_agent.
log = logging.getLogger("agent")

# `_client: OpenAI | None = None`
# Khai báo biến _client với kiểu dữ liệu là "OpenAI HOẶC None".
# `OpenAI | None` = union type — biến này có thể chứa một OpenAI object,
# hoặc có thể là None (không có gì). Ban đầu gán = None vì client chưa được tạo.
# Dấu gạch dưới đầu (_client) là quy ước Python nghĩa là "biến nội bộ,
# không dùng từ bên ngoài module này".
# Singleton client — None cho tới lần get_client() đầu tiên. `global` cho phép
# gán lại biến module-level từ trong hàm.
_client: OpenAI | None = None

# `_logging_ready = False`
# Biến boolean (đúng/sai) — False = chưa cấu hình logging.
# Sau khi _setup_logging() chạy lần đầu, nó sẽ đặt biến này = True
# để không bao giờ gọi basicConfig() thêm lần nào nữa.
# Đã cấu hình logging chưa — guard để _setup_logging() chỉ basicConfig 1 lần,
# tránh giẫm lên cấu hình của caller ở những lần run_agent sau.
_logging_ready = False


# ---------------------------------------------------------------------------
# MODEL CONFIG — Pi-style models.json (swap model = edit a data file, not code)
# ---------------------------------------------------------------------------
# Borrowed from Pi's models.json: model/provider knobs live in a data file
# (models.json at the repo root), read by id, so swapping Qwen3-14B for another
# model is a config edit — not a code change. Secrets stay in .env (referenced
# via api_key_env). If models.json is absent we fall back to the legacy VLLM_*
# env vars, so nothing breaks for anyone without the file.
@dataclass(frozen=True)
class ModelConfig:
    base_url: str
    model: str
    api_key: str = "not-needed"
    max_tokens: int = 2048
    temperature: float = 0.0
    context_window: int = 32768


@lru_cache(maxsize=1)
def load_model_config() -> ModelConfig:
    """Active model config from models.json (by id), falling back to .env.

    models.json: {"default": "<id>", "models": {"<id>": {base_url, model,
    api_key_env?, max_tokens?, temperature?, context_window?}}}. Active id =
    $AGENT_MODEL or the file's "default". The API key is read from the env var
    named by api_key_env (default VLLM_API_KEY) so no secret lives in the JSON.
    """
    load_dotenv()
    cfg_path = Path(__file__).resolve().parent.parent / "models.json"
    if cfg_path.exists():
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
        model_id = os.environ.get("AGENT_MODEL") or data["default"]
        entry = data["models"][model_id]
        api_key = os.environ.get(entry.get("api_key_env", "VLLM_API_KEY"), "not-needed")
        return ModelConfig(
            base_url=entry["base_url"],
            model=entry["model"],
            api_key=api_key,
            max_tokens=entry.get("max_tokens", 2048),
            temperature=entry.get("temperature", 0.0),
            context_window=entry.get("context_window", 32768),
        )
    # Fallback: legacy .env behaviour (identical to before models.json existed).
    return ModelConfig(
        base_url=os.environ["VLLM_BASE_URL"],
        model=os.environ["VLLM_MODEL_NAME"],
        api_key=os.environ.get("VLLM_API_KEY", "not-needed"),
    )


# `def get_client() -> OpenAI:` — hàm trả về một OpenAI object (không None).
# Đây là ví dụ điển hình của pattern "LAZY SINGLETON":
#   - SINGLETON = chỉ có DUY NHẤT MỘT instance của client trong toàn chương trình.
#     Lần đầu gọi get_client() → tạo mới. Mọi lần sau → trả về cái cũ.
#     Tại sao? Vì tạo HTTP connection tốn thời gian; không cần tạo đi tạo lại.
#   - LAZY = "lười biếng" — KHÔNG tạo client khi file được import.
#     Chỉ tạo khi thực sự cần (lần đầu gọi get_client()).
#     Tại sao? Vì `import src.agent` có thể xảy ra trong test/eval mà không
#     cần .env — nếu tạo client ngay lúc import sẽ crash vì thiếu API key.
def get_client() -> OpenAI:
    """Trả về OpenAI client (singleton), dựng lười ở lần gọi đầu tiên.

    Tại sao lười? — Để `import src.agent` không có tác dụng phụ: không đọc .env,
    không cần biến môi trường, không tạo kết nối. Chỉ khi run_agent (hoặc caller)
    THỰC SỰ cần gọi model thì mới load_dotenv + đọc env + dựng client.

    Đọc 3 biến cấu hình ở đây (không phải lúc import). Thiếu BASE_URL hay MODEL
    → crash ngay (fail fast). API_KEY có default vì vLLM không enforce auth.
    """
    # `global _client` — từ khóa global cho phép hàm này GÁN LẠI biến _client
    # được khai báo ở cấp module (bên ngoài mọi hàm).
    # Trong Python, hàm có thể ĐỌC biến module-level mà không cần khai báo gì.
    # Nhưng nếu muốn GÁN LẠI (_client = ...) biến đó, PHẢI khai báo `global _client`
    # trước — không thì Python sẽ tạo một biến LOCAL (nội bộ hàm) mới tên _client,
    # không liên quan đến biến module-level. Đây là quirk nổi tiếng của Python.
    global _client

    # `if _client is None:` — kiểm tra xem _client có đang là None không.
    # `if` là câu lệnh điều kiện: nếu điều kiện đúng, chạy khối thụt vào bên dưới.
    # `is None` = so sánh "có phải None không?" (dùng `is` chứ không phải `==`
    # vì None là singleton — chỉ có đúng 1 đối tượng None trong Python).
    if _client is None:
        # Khối này chỉ chạy khi _client chưa được tạo (lần đầu gọi get_client).

        # Đọc cấu hình model (models.json, fallback .env). load_model_config()
        # tự gọi load_dotenv nên `import src.agent` vẫn không có side-effect.
        # base_url + api_key lấy từ config → đổi model/endpoint = sửa models.json,
        # không phải sửa code. Đây chính là pattern "portability" kiểu Pi.
        cfg = load_model_config()
        # timeout + max_retries TƯỜNG MINH: mặc định SDK (~600s/request, retry nhiều lần)
        # khiến 1 call vLLM kẹt treo cả turn ~10-30 phút — time_budget_s chỉ check GIỮA các
        # turn nên không cắt được call đang treo, và harness await fut.result() không timeout.
        # Đặt trần mỗi request (120s) + 1 retry → call hỏng bị cắt nhanh, không nuốt cả budget
        # của run dài không người trông (audit HIGH). Có thể đưa vào models.json sau.
        _client = OpenAI(base_url=cfg.base_url, api_key=cfg.api_key,
                         timeout=120.0, max_retries=1)

    # `return _client` — trả về giá trị cho bên gọi hàm.
    # `return` là từ khóa kết thúc hàm và trả về giá trị.
    # Dù đây là lần đầu hay lần thứ 100 gọi get_client(), đều trả về cùng
    # một _client (singleton).
    return _client


# `def get_model() -> str:` — hàm trả về tên model dưới dạng chuỗi.
# Đọc MODEL lười từ env (gọi sau khi get_client đã load_dotenv, hoặc tự đọc).
# Tách riêng khỏi get_client để chỗ gọi API đọc tên model rõ ràng. load_dotenv
# là idempotent nên gọi ở đây cũng an toàn nếu vì lý do gì client chưa dựng.
def get_model() -> str:
    """Đọc MODEL lười từ env (gọi sau khi get_client đã load_dotenv, hoặc tự đọc).

    Tách riêng khỏi get_client để chỗ gọi API đọc tên model rõ ràng. load_dotenv
    là idempotent nên gọi ở đây cũng an toàn nếu vì lý do gì client chưa dựng.
    """
    # Tên model lấy từ cùng nguồn cấu hình (models.json theo id, fallback .env).
    # load_model_config() được cache (lru_cache) nên gọi lại rẻ và nhất quán với
    # base_url/api_key mà get_client đã dùng.
    return load_model_config().model


# `def _setup_logging() -> None:` — hàm cấu hình hệ thống logging.
# Dấu gạch dưới đầu (_setup_logging) báo hiệu đây là hàm "private" —
# chỉ dùng trong file này, không dùng từ bên ngoài.
class _DynamicStderrHandler(logging.Handler):
    """Ghi log ra sys.stderr ĐỌC ĐỘNG tại lúc emit (KHÔNG bind cứng một stream).

    Vì sao cần: eval gọi run_agent BÊN TRONG `redirect_stderr(file_log_của_task)` cho
    TỪNG task. `logging.basicConfig` (cách cũ) bind handler vào sys.stderr DUY NHẤT 1 lần
    mỗi process; ở ProcessPool 'spawn' worker bị tái dùng qua nhiều task, task đầu bind vào
    file-log#1, các task sau redirect sang file mới nhưng guard bỏ qua basicConfig → handler
    vẫn trỏ stream cũ (đã đóng) → 590/627 log per-task = 0 byte (mất trace để audit).
    Handler này đọc `sys.stderr` ngay lúc emit nên luôn ghi vào file-log của task hiện tại.
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            sys.stderr.write(self.format(record) + "\n")
            sys.stderr.flush()      # flush ngay (như StreamHandler) → hard-kill không mất trace
        except Exception:           # logging KHÔNG được phép giết caller
            self.handleError(record)


def _setup_logging() -> None:
    """Gắn 1 lần (có guard) handler ghi log "agent" ra sys.stderr ĐỘNG tại lúc emit.

    `format="%(message)s"` = chỉ in nội dung message (gọn cho demo). `propagate=False` để
    log không lọt lên root (tránh nhân đôi + tránh dính handler cũ của caller). Dùng
    _DynamicStderrHandler thay vì basicConfig để log bám đúng redirect_stderr mỗi task của
    eval (xem docstring handler) — sửa bug log 0 byte ở pool worker tái dùng.
    """
    # `global _logging_ready` — cần gán lại biến module-level này.
    global _logging_ready

    # `if not _logging_ready:` — chỉ gắn handler 1 lần mỗi process (handler đã "động" nên
    # gắn 1 lần là đủ để theo mọi redirect về sau).
    if not _logging_ready:
        log.setLevel(logging.INFO)
        log.propagate = False
        handler = _DynamicStderrHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        log.addHandler(handler)
        _logging_ready = True


# ---------------------------------------------------------------------------
# THE AGENT LOOP — trái tim của hệ thống
# ---------------------------------------------------------------------------
# execute_turn — cơ chế "chạy trọn một lượt tool_calls" DÙNG CHUNG
# ---------------------------------------------------------------------------

def execute_turn(tool_calls: list[dict], messages: list, workspace: Path,
                 *, on_call=None, on_result=None) -> bool:
    """Chạy trọn một lượt tool_calls, giữ bất biến ghép cặp — dùng CHUNG bởi
    run_agent (eval/solve) và cli/chat.py (REPL).

    Trước đây REPL tự cài lại khối này và 2 bản đã drift theo 3 hướng: REPL có
    JSON-repair mà eval không (args hỏng nằm lại history → vLLM 400 turn sau,
    chết cả run eval); eval biết finish mà REPL lờ đi; chỉ REPL chống Ctrl+C
    làm đứt cặp. "Một lượt agent diễn ra thế nào" giờ có ĐÚNG MỘT câu trả lời.

    tool_calls: list dict ĐÃ CHUẨN HÓA {"id", "name", "arguments"} — caller tự
    chuyển từ SDK object (run_agent) / streaming fragments (chat.py) về dạng này.
    PRE: messages[-1] là assistant message mang đúng các tool_calls này.

    Hành vi:
      1. Validate JSON arguments TRƯỚC khi chạy. Args hỏng (model emit Python
         triple-quote trong JSON...) → KHÔNG chạy tool; sửa bản copy trong
         messages[-1] thành "{}" (history hợp lệ — turn sau không 400) + trả
         error message hướng dẫn retry. Error giữ ENGLISH-ONLY: Qwen3 instruct
         tuned trên English, trộn Vietnamese giảm tỉ lệ retry thành công.
      2. Chạy từng tool qua execute_tool, append ĐÚNG 1 role:"tool" mỗi call
         với tool_call_id khớp (bất biến ghép cặp của API).
      3. Ctrl+C giữa một tool dài: điền placeholder cho call đó VÀ mọi call
         còn lại (pairing vẫn đủ) rồi mới re-raise — caller quyết số phận
         (REPL: break turn, sống tiếp; eval: thoát nhưng history hợp lệ).

    on_call(name, args) / on_result(result): hook in ra màn hình — mặc định
    là style của run_agent ([tool]/[tool result]); REPL truyền style riêng (▶/↳).
    Returns: True nếu lượt này có gọi tool finish.
    """
    if on_call is None:
        def on_call(name, args):
            cprint(Color.TOOL, f"[tool] {name}({args})")
    if on_result is None:
        def on_result(result):
            # Cắt preview 500 chars khi in — model vẫn nhận FULL qua messages.
            preview = result if len(result) < 500 else result[:500] + "...[truncated]"
            cprint(Color.RESULT, f"[tool result]\n{preview}")

    finish_called = any(tc["name"] == "finish" for tc in tool_calls)
    interrupted: KeyboardInterrupt | None = None

    for tc in tool_calls:
        on_call(tc["name"], tc["arguments"])

        # Validate JSON trước — execute_tool cũng tự bắt JSON hỏng, nhưng chỉ
        # validate ở đây mới SỬA ĐƯỢC bản args nằm trong history (điểm sống còn).
        bad_json: str | None = None
        if tc["arguments"]:
            try:
                json.loads(tc["arguments"])
            except json.JSONDecodeError as e:
                bad_json = str(e)

        if interrupted is not None:
            # Đã bị Ctrl+C ở tool trước — không chạy nữa, chỉ điền placeholder
            # để tool_call này không thành mồ côi.
            result = "[skipped: user interrupted tool execution]"
        elif bad_json is not None:
            # Sửa args trong assistant message vừa append: "{}" parse được →
            # history không làm vLLM 400 ở turn sau. Tool result vẫn nói rõ lỗi.
            for entry in messages[-1].get("tool_calls", []):
                if entry.get("id") == tc["id"]:
                    entry["function"]["arguments"] = "{}"
            result = (
                f"ERROR: invalid JSON in arguments: {bad_json}\n"
                "Retry with valid JSON. Escape newlines as \\n and double-quotes as \\\". "
                "Do NOT use Python triple-quote (\"\"\") inside JSON strings."
            )
        else:
            try:
                result = execute_tool(tc["name"], tc["arguments"], workspace)
            except KeyboardInterrupt as e:
                interrupted = e
                result = "[interrupted: user cancelled tool execution]"

        on_result(result)
        messages.append({
            "role": "tool",
            "tool_call_id": tc["id"],
            "content": result,
        })

    if interrupted is not None:
        # Re-raise SAU khi mọi tool_call đã có result — pairing nguyên vẹn.
        raise interrupted
    return finish_called


# ---------------------------------------------------------------------------

# `def run_agent(goal: str, workspace: Path, max_iters: int = 15,`
# `              time_budget_s: float | None = None,`
# `              temperature: float | None = None) -> dict:`
#
# Khai báo hàm run_agent với 5 tham số:
#   - goal: str          — nhiệm vụ dạng text ("Fix the failing tests...")
#   - workspace: Path    — thư mục sandbox agent được phép đọc/ghi
#   - max_iters: int = 15 — số vòng lặp tối đa; "= 15" = có giá trị mặc định
#                           nếu không truyền vào thì mặc định là 15
#   - time_budget_s: float | None = None — ngân sách thời gian (giây), None = không giới hạn
#   - temperature: float | None = None — độ "sáng tạo" của model; None = dùng mặc định
#   - client: OpenAI | None = None — SEAM cho test: truyền client giả (scripted
#     responses) để test mọi bất biến của loop offline. None = get_client() thật.
# `-> dict` = hàm trả về một dictionary (từ điển key→value).
def run_agent(goal: str, workspace: Path, max_iters: int = 15,
              time_budget_s: float | None = None,
              temperature: float | None = None,
              skill_path: Path | str | None = None,
              client: OpenAI | None = None) -> dict:
    """Run the ReAct loop until the model stops calling tools, or max_iters.

    ReAct = Reasoning + Acting interleaved. Each iteration:
      - reason:  model thinks, may produce visible content.
      - act:     model emits tool_calls (or nothing -> we're done).
      - observe: we execute each tool and append result as role=tool.
    Termination: model returns NO tool_calls (it has decided it's done).

    workspace: thư mục sandbox agent được phép đọc/ghi — nay là THAM SỐ tường
    minh (positional thứ 2, BẮT BUỘC), không còn là global trong tools.py. Mỗi
    lời gọi execute_tool() bên dưới truyền thẳng workspace này xuống tool.

    Returns {"finish_reason": str, "iters_used": int} so the eval harness can
    record the outcome. finish_reason ∈ {finished, max_iters, api_error, timeout, no_action}.
    `iters_used` = số turn ĐÃ thực hiện (1-based `i` tại điểm thoát) — nhất quán ở
    MỌI nhánh return (finished / max_iters / api_error / timeout / no_action).
    Callers that ignore the return value (the REPL, the CLI) are unaffected.

    time_budget_s: optional wall-clock cap, checked BETWEEN turns (None = no cap).

    === 5 GIÁ TRỊ finish_reason VÀ NHÁNH NÀO RETURN CHÚNG ===
      "finished"   — model tự nguyện dừng gọi tool SAU KHI đã gọi ít nhất 1 tool.
                     Đây là kết thúc "hạnh phúc" — agent hoàn thành nhiệm vụ.
      "no_action"  — model trả lời text mà KHÔNG gọi tool nào cả (nói mà không làm),
                     kể cả sau khi nhắc (nudge). Agent thất bại kiểu "báo cáo miệng".
      "max_iters"  — đã dùng hết max_iters turn mà model vẫn còn muốn gọi tool thêm.
                     Safety net chống loop vô tận.
      "api_error"  — lỗi kết nối/HTTP khi gọi API (timeout, 5xx, context quá dài).
      "timeout"    — đã vượt quá time_budget_s giây (ngân sách thời gian).
    """
    # `_setup_logging()` — gọi hàm _setup_logging đã định nghĩa ở trên.
    # Gọi hàm trong Python: viết tên hàm theo sau là dấu () (có thể truyền tham số
    # vào trong ngoặc). Ở đây không có tham số.
    # Cấu hình logging 1 lần (lười — không chạy lúc import). Phải gọi TRƯỚC mọi
    # cprint/log.info bên dưới để output hiện ra.
    _setup_logging()

    # Client: dùng cái caller truyền vào (test bơm FakeClient ở đây), không có
    # thì dựng client thật — lười, không có gì xảy ra lúc import module.
    # Đây là seam DUY NHẤT cần cho việc test loop: mọi thứ khác giữ nguyên.
    if client is None:
        client = get_client()

    # `model = get_model()` — đọc tên model từ biến môi trường.
    # Ví dụ: model = "Qwen/Qwen2.5-Coder-7B-Instruct"
    model = get_model()

    # `messages: list[ChatCompletionMessageParam] = [...]`
    # Khai báo biến messages là một LIST (danh sách) chứa các message.
    # LIST trong Python:
    #   - Được tạo bằng cặp ngoặc vuông: [item1, item2, ...]
    #   - Có thứ tự (phần tử 0, 1, 2, ...)
    #   - Có thể thêm phần tử vào cuối bằng .append()
    #   - Có thể chứa nhiều kiểu dữ liệu khác nhau
    # `list[ChatCompletionMessageParam]` = type hint: list này chứa các message objects.
    #
    # Ban đầu có 2 message:
    #   1. {"role": "system", "content": SYSTEM_PROMPT} — lệnh nền cho model
    #   2. {"role": "user", "content": goal}            — nhiệm vụ của người dùng
    # role = "system" | "user" | "assistant" | "tool" — quy ước của OpenAI API.
    #
    # Khởi tạo "cuốn sổ ký ức" (messages list) — y hệt 01_chat.py, nhưng nay
    # chứa cả system prompt VÀ goal của user (2 message ban đầu).
    # Dùng OpenAI TypedDict để Pylance pass-through; dict literal vẫn assign được
    # vì TypedDict là structural typing (chỉ check keys + value types).
    # Skill injection (SkillOpt substrate): nếu caller truyền skill_path, đọc nội
    # dung skill và ghép vào sau SYSTEM_PROMPT qua build_system_prompt. KHÔNG truyền
    # skill_path (mặc định None) → build_system_prompt(None) trả về SYSTEM_PROMPT
    # nguyên văn → hành vi byte-identical với trước (REPL, eval mặc định không đổi).
    skill_text = Path(skill_path).read_text(encoding="utf-8") if skill_path else None
    system_content = build_system_prompt(skill_text)

    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": goal},
    ]

    # `start = time.monotonic()` — ghi lại thời điểm bắt đầu (tính bằng giây).
    # time.monotonic() trả về một số thực (float) = số giây kể từ một điểm
    # tham chiếu cố định. Dùng để tính "đã chạy bao lâu?" bằng cách trừ:
    #   elapsed = time.monotonic() - start
    # "monotonic" = đồng hồ chỉ đi tới, không nhảy ngược (khác system clock
    # có thể bị điều chỉnh bởi NTP).
    start = time.monotonic()

    # Guardrail "nói mà không làm": ~30% lần model trả prose (mô tả/viết code dạng
    # text) ngay turn đầu mà KHÔNG gọi tool nào → loop tưởng "xong" → task fail oan.
    #   made_tool_call: đã gọi tool lần nào chưa (chốt phân biệt "xong thật" vs "bail").
    #   nudges_used:    đã nhắc bao nhiêu lần; chặn ở MAX_NUDGES để không loop vô tận.

    # `made_tool_call = False` — cờ boolean, ban đầu False (chưa gọi tool lần nào).
    made_tool_call = False

    # `nudges_used = 0` — đếm số lần đã nhắc model "hãy gọi tool đi".
    nudges_used = 0

    # `MAX_NUDGES = 2` — tối đa nhắc 2 lần, sau đó từ bỏ.
    # Tên viết HOA = hằng số (không thay đổi trong suốt hàm).
    MAX_NUDGES = 2

    # NUDGE là chuỗi nhắc nhở gửi cho model khi nó trả lời text mà không gọi tool.
    # `(` mở ngoặc để nối nhiều chuỗi liên tiếp trên nhiều dòng (Python tự ghép).
    NUDGE = ("You replied with text but called no tool, so nothing has actually changed "
             "on disk and the task is NOT done. If the task needs a file created or edited, "
             "call write_file / apply_patch / multi_edit now — do not just describe the code. "
             "Only stop without a tool call once the work is truly complete.")

    # `for i in range(1, max_iters + 1):` — vòng lặp FOR.
    # `for` là từ khóa bắt đầu vòng lặp. Cú pháp: for <biến> in <dãy giá trị>:
    # `range(1, max_iters + 1)` — tạo dãy số nguyên từ 1 đến max_iters (bao gồm).
    #   range(start, stop) tạo dãy: start, start+1, ..., stop-1  (KHÔNG bao gồm stop)
    #   Ví dụ: range(1, 4) = [1, 2, 3]
    #   range(1, max_iters + 1) với max_iters=15 → range(1, 16) = [1, 2, ..., 15]
    # Biến `i` lần lượt nhận giá trị 1, 2, 3, ..., max_iters (số turn hiện tại).
    # Vòng lặp giới hạn `max_iters` turn — safety net để agent không loop vô tận.
    # Mỗi turn = 1 round-trip với model + thực thi tool nếu có.
    # create_kwargs LOOP-INVARIANT: model/tools/tool_choice/max_tokens/temperature
    # không đổi giữa các turn — dựng MỘT lần ở đây thay vì mỗi turn. `messages`
    # nằm trong dict theo THAM CHIẾU (reference): mọi messages.append() bên trong
    # vòng lặp tự động được API call tiếp theo nhìn thấy, không cần dựng lại dict.
    # type:ignore: TOOL_SCHEMAS là list[dict] (xem tools.py), không exact match
    # OpenAI TypedDict — runtime hợp lệ vì dict shape khớp schema API mong đợi.
    create_kwargs = dict(
        model=model,
        messages=messages,
        tools=TOOL_SCHEMAS,
        tool_choice="auto",
        max_tokens=load_model_config().max_tokens,
    )
    # Chỉ thêm key "temperature" khi caller truyền giá trị cụ thể — API không
    # nhận temperature=None (muốn default thì PHẢI vắng key).
    # temperature=None → dùng default của model (REPL). Eval truyền 0.0 để decode
    # tham lam (greedy): tool-call ổn định + kết quả TÁI LẬP được (pass@1 chuẩn).
    # Ở temp mặc định (~0.6), thỉnh thoảng turn-1 model trả prose thay vì gọi
    # write_file → task fail oan; greedy gần như loại bỏ hành vi đó.
    if temperature is not None:
        create_kwargs["temperature"] = temperature

    for i in range(1, max_iters + 1):
        # Hết ngân sách thời gian (nếu eval truyền vào) → dừng gọn. Chỉ check GIỮA
        # các turn: không ngắt được 1 tool đang chạy dở, nhưng mỗi tool đã có timeout
        # riêng (run_bash 600s, run_python/pytest 60s) nên thời gian bị chặn trên.

        # `if time_budget_s is not None and time.monotonic() - start > time_budget_s:`
        # Điều kiện phức hợp với `and`:
        #   - `time_budget_s is not None`: kiểm tra có giới hạn thời gian không.
        #     `is not None` = "không phải None" = "có giá trị cụ thể".
        #     Nếu không có giới hạn thời gian (None) → SKIP kiểm tra này (tiết kiệm
        #     tính toán — đây là "short-circuit evaluation": nếu vế trái `and` là
        #     False, Python KHÔNG tính vế phải nữa vì cả AND đã chắc là False).
        #   - `time.monotonic() - start > time_budget_s`: tính thời gian đã trôi qua
        #     (giây hiện tại trừ giây bắt đầu), so sánh với ngân sách.
        #     `>` = "lớn hơn". Nếu đúng = đã hết thời gian.
        # `and` = toán tử AND: cả hai vế phải đúng thì điều kiện mới đúng.
        #   SHORT-CIRCUIT: nếu vế trái đã sai → Python bỏ qua vế phải NGAY LẬP TỨC.
        #   Ví dụ: False and <bất kỳ> → kết quả luôn là False, không cần tính <bất kỳ>.
        if time_budget_s is not None and time.monotonic() - start > time_budget_s:
            cprint(Color.WARN, f"\nAgent hit time budget {time_budget_s:.0f}s on turn {i}.")
            # `return {"finish_reason": "timeout", "iters_used": i}` — kết thúc hàm
            # và trả về dictionary.
            # `return` kết thúc hàm ngay lập tức — bất kể còn bao nhiêu code phía sau.
            # `{"finish_reason": "timeout", "iters_used": i}` = dict với 2 cặp key:value.
            # `iters_used: i` (KHÔNG phải i-1) cho NHẤT QUÁN với mọi nhánh return
            # khác — tất cả đều báo `i` (1-based số turn đã bước vào). Bug cũ trả
            # i-1 khiến eval đếm lệch 1 ở case timeout.
            return {"finish_reason": "timeout", "iters_used": i}

        # Header phân tách từng turn — dễ nhìn khi demo.
        # `len(messages)` = độ dài (số phần tử) của list messages.
        # `len()` là hàm built-in của Python, trả về số nguyên.
        cprint(Color.HEADER, f"\n=== Turn {i} (history: {len(messages)} messages) ===")

        # -----------------------------------------------------------------------
        # BƯỚC 1: GỌI API (REASON)
        # Khác 01_chat.py ở 2 tham số mới:
        #   - tools=TOOL_SCHEMAS: gửi danh sách tool cho model biết
        #   - tool_choice="auto": cho model TỰ QUYẾT có gọi tool không
        # ("required" sẽ ép gọi tool mỗi turn — không phù hợp vì cần model có
        # khả năng "kết thúc" bằng cách trả về content trần)
        # -----------------------------------------------------------------------

        # Bọc try/except quanh CHỈ lời gọi API: nếu vLLM rớt mạng, trả 5xx, hay
        # context vượt quá window (400), exception sẽ bubble ra ngoài và giết
        # cả run_agent — eval/run.py sẽ tính nguyên task là crash. Bắt ở đây để
        # log lỗi (Rule C: verbose) rồi return GỌN GÀNG.
        # An toàn về tính đúng đắn: tại điểm này messages list đang Ở TRẠNG THÁI
        # HỢP LỆ (mọi assistant-tool_calls trước đó đã có đủ tool message ghép
        # cặp). Vì ta return TRƯỚC khi append assistant message mới, list không
        # bao giờ bị bỏ lại với 1 assistant.tool_calls "mồ côi" không có kết quả.

        # `try:` ... `except OpenAIError as e:` — cấu trúc xử lý lỗi (exception handling).
        # `try:` = "thử chạy đoạn code này".
        # `except OpenAIError as e:` = "nếu xảy ra lỗi loại OpenAIError, bắt nó vào
        #   biến e và chạy đoạn code bên dưới".
        # Nếu không có lỗi → khối except bị bỏ qua.
        # Nếu có lỗi không phải OpenAIError → lỗi tiếp tục "bọc lên" (bubble up)
        #   tới caller mà không bị bắt ở đây.
        try:
            # `client.chat.completions.create(**create_kwargs)` — gọi API OpenAI.
            # `client.chat.completions.create(...)` = gọi phương thức create()
            # thông qua chuỗi thuộc tính: client → chat → completions → create().
            # Đây là cách OpenAI SDK tổ chức API — mỗi cấp là một namespace.
            #
            # `**create_kwargs` — toán tử "double star" (unpacking).
            # `**dict` = "mở gói" dictionary thành các keyword arguments.
            # Ví dụ: create(**{"model": "abc", "max_tokens": 100})
            #   = create(model="abc", max_tokens=100)
            # Dùng khi muốn build dict tham số rồi truyền vào — linh hoạt hơn
            # viết thẳng vào lời gọi hàm.
            #
            # Lời gọi này BLOCK (chặn) chương trình cho đến khi nhận được phản hồi
            # từ model — có thể mất vài giây đến vài chục giây.
            resp = client.chat.completions.create(**create_kwargs)  # type: ignore[arg-type]
            # Một số endpoint trả 200 nhưng choices RỖNG (lỗi phía server / context tràn).
            # Không guard thì resp.choices[0] bên dưới ném IndexError → crash worker. Coi
            # như api_error để harness ghi nhận đúng thay vì "agent_crash".
            if not resp.choices:
                cprint(Color.WARN, f"\nAPI returned empty choices on turn {i}. Stopping.")
                return {"finish_reason": "api_error", "iters_used": i}
        except OpenAIError as e:
            # `e` là biến chứa thông tin lỗi — có thể in ra để debug.
            # `f"\nAPI error on turn {i}: {e}. Stopping."` = f-string chèn i và e vào.
            cprint(Color.WARN, f"\nAPI error on turn {i}: {e}. Stopping.")
            # Trả về ngay với finish_reason="api_error" — không thử lại.
            return {"finish_reason": "api_error", "iters_used": i}

        # -----------------------------------------------------------------------
        # BƯỚC 2: BÓC LẤY MESSAGE (giống 01_chat.py)
        # resp.choices là list — nếu n=1 (default), index 0 là câu trả lời duy nhất.
        # msg là Pydantic object có .content, .role, .tool_calls, .reasoning, ...
        # -----------------------------------------------------------------------

        # `resp.choices[0].message` — truy cập phần tử đầu tiên (index 0) của
        # list choices, rồi lấy thuộc tính message.
        # `[0]` = lấy phần tử đầu tiên của list (Python đếm từ 0: [0], [1], [2], ...).
        # `.message` = thuộc tính chứa nội dung phản hồi của model.
        msg = resp.choices[0].message

        # -----------------------------------------------------------------------
        # BƯỚC 3: APPEND ASSISTANT MESSAGE VÀO SỔ KÝ ỨC
        # KHÁC 01_chat.py: ở đây mình KHÔNG append `{"role":"assistant","content":...}`,
        # vì làm vậy sẽ MẤT field `tool_calls`. Đây là BẤT BIẾN sống còn của
        # ReAct loop: mỗi assistant message có tool_calls PHẢI được theo sau bởi
        # đúng 1 tool message cho MỖI tool_call_id. Nếu append thủ công chỉ
        # content, các tool-result message ở BƯỚC 6 sẽ tham chiếu tool_call_id
        # không tồn tại trong assistant trước → API trả 400 và cả run hỏng.
        # `model_dump(exclude_none=True)` = convert Pydantic object → dict, bỏ field
        # null (vd: `content: None` khi model chỉ gọi tool, `audio: None`). Đã
        # verify: exclude_none GIỮ NGUYÊN mảng tool_calls + id + function, nên
        # bất biến ghép cặp vẫn toàn vẹn — chỉ rụng các field thừa làm API khó chịu.
        # -----------------------------------------------------------------------

        # `msg.model_dump(exclude_none=True)`
        # msg là Pydantic object (đối tượng từ thư viện Pydantic — dùng để validate
        # và parse dữ liệu có cấu trúc). Pydantic objects có phương thức model_dump():
        #   - .model_dump() → chuyển đổi object thành dict Python thông thường.
        #     Ví dụ: msg.model_dump() có thể trả về:
        #       {"role": "assistant", "content": None, "tool_calls": [...], "audio": None}
        #   - exclude_none=True → loại bỏ các key có giá trị None.
        #     Sau khi exclude_none: {"role": "assistant", "tool_calls": [...]}
        # TẠI SAO QUAN TRỌNG?
        #   OpenAI API rất nhạy cảm: nếu gửi `{"content": None}` thay vì bỏ key content
        #   hoàn toàn, một số version API sẽ từ chối với lỗi 400 (bad request).
        #   exclude_none=True đảm bảo chỉ gửi các field có giá trị thực sự.
        # TẠI SAO KHÔNG APPEND THỦ CÔNG {"role": "assistant", "content": msg.content}?
        #   Vì làm vậy sẽ MẤT field tool_calls! Khi model gọi tool, msg.content = None
        #   nhưng msg.tool_calls = [{"id": "call_abc", "function": {...}}]. Nếu không
        #   giữ tool_calls trong message history, lần sau gửi lên API, nó sẽ thấy
        #   tool result message (role="tool") mà không có assistant message kèm
        #   tool_calls → lỗi 400 "tool call id not found".

        # `messages.append(...)` — thêm phần tử vào CUỐI list messages.
        # .append() là phương thức của list: list.append(phần_tử_mới).
        # Sau mỗi turn, messages ngày càng dài ra:
        #   [system, user, assistant1, tool1, assistant2, tool2, ...]
        # Đây chính là "bộ nhớ" của agent — toàn bộ lịch sử được gửi lên API
        # mỗi turn để model "nhớ" đã làm gì.
        messages.append(msg.model_dump(exclude_none=True))  # type: ignore[arg-type]

        # -----------------------------------------------------------------------
        # BƯỚC 4: NẾU MODEL CÓ CONTENT (= nói chuyện), IN RA
        # Content có thể None khi model chỉ gọi tool không nói gì.
        # Khi có content, đây là lúc model "narrate" (giải thích nó đang làm gì).
        # -----------------------------------------------------------------------

        # `if msg.content:` — kiểm tra "nếu content có giá trị".
        # Trong Python, `if x:` là True khi x:
        #   - Không phải None
        #   - Không phải chuỗi rỗng ""
        #   - Không phải 0, False, [], {}, ...
        # Vậy `if msg.content:` = "nếu model có trả lời text (không phải None/rỗng)".
        if msg.content:
            cprint(Color.ASSISTANT, f"[assistant] {msg.content}")

        # -----------------------------------------------------------------------
        # BƯỚC 5: NẾU KHÔNG CÓ TOOL_CALLS, AGENT KẾT THÚC
        # Quy ước ReAct: model dừng gọi tool = model nghĩ task xong → mình tin nó.
        # `not msg.tool_calls` true khi tool_calls là None HOẶC list rỗng.
        # -----------------------------------------------------------------------

        # `if not msg.tool_calls:` — kiểm tra "nếu KHÔNG có tool calls".
        # `not` đảo ngược giá trị boolean:
        #   - `not None`  = True  (None là falsy trong Python)
        #   - `not []`    = True  (list rỗng là falsy)
        #   - `not [...]` = False (list có phần tử là truthy)
        # Vậy `if not msg.tool_calls:` đúng khi:
        #   - msg.tool_calls là None (model không có tool calls field), HOẶC
        #   - msg.tool_calls là [] (list rỗng — model không muốn gọi tool nào)
        # Cả hai trường hợp đều có nghĩa: model không muốn thực hiện hành động nào.
        if not msg.tool_calls:
            # Đã hành động ít nhất 1 lần → tin agent đã xong thật (giữ nguyên hành vi
            # ReAct cũ, bảo toàn quyền kết thúc hợp lệ của agent đã làm việc xong).

            # `if made_tool_call:` — nếu đã gọi tool ít nhất 1 lần trước đó.
            # made_tool_call là biến boolean đặt = True ở BƯỚC 6 khi chạy tool.
            # Logic: nếu model ĐÃ gọi tool + bây giờ không gọi nữa = thực sự xong.
            if made_tool_call:
                cprint(Color.FINISH, "\nAgent finished.")
                # Trả về "finished" — kết thúc thành công.
                return {"finish_reason": "finished", "iters_used": i}

            # Chưa đụng tool lần nào mà đã "xong" → gần như chắc là trả prose suông.
            # Còn quota nhắc VÀ còn turn để model phản hồi nudge thì nhắc rồi loop lại.
            # An toàn pairing: assistant vừa append KHÔNG có tool_calls nên messages
            # đang hợp lệ; thêm 1 user nudge sau nó OK.
            #
            # `nudges_used < MAX_NUDGES and i < max_iters`
            # Điều kiện kép với `and`:
            #   - `nudges_used < MAX_NUDGES`: còn quota nhắc (<= 2 lần).
            #     `<` = "nhỏ hơn". nudges_used=0, MAX_NUDGES=2 → 0 < 2 = True.
            #   - `i < max_iters`: còn ít nhất 1 turn nữa sau turn hiện tại.
            #     Nếu i == max_iters (đây là turn cuối), nhắc rồi cũng vô nghĩa
            #     vì vòng lặp sẽ kết thúc ngay — model không kịp đọc nudge.
            # `and` = short-circuit: nếu vế trái sai, vế phải KHÔNG được tính.
            if nudges_used < MAX_NUDGES and i < max_iters:
                # `nudges_used += 1` — tăng biến nudges_used lên 1.
                # `+=` là cú pháp rút gọn: `x += 1` = `x = x + 1`.
                nudges_used += 1
                cprint(Color.WARN,
                       f"\nModel answered without calling a tool; nudging ({nudges_used}/{MAX_NUDGES}).")
                # Thêm message nhắc nhở vào lịch sử — model sẽ đọc ở turn sau.
                messages.append({"role": "user", "content": NUDGE})
                # `continue` — bỏ qua phần còn lại của vòng lặp, nhảy ngay sang
                # lần lặp tiếp theo (tăng i lên 1 và kiểm tra lại điều kiện for).
                # Không có continue thì code sẽ tiếp tục chạy các bước bên dưới.
                continue

            # Hết quota (hoặc đây là turn cuối) mà vẫn không act → dừng, đánh dấu
            # no_action để harness phân biệt với "finished" thật (fail kiểu "nói mà
            # không làm"). Return TẠI ĐÂY (iters_used=i) thay vì để rơi xuống nhánh
            # max_iters ở cuối hàm — phân loại finish_reason chính xác hơn.
            cprint(Color.WARN, "\nAgent stopped without ever calling a tool (no_action).")
            return {"finish_reason": "no_action", "iters_used": i}

        # -----------------------------------------------------------------------
        # BƯỚC 5.5: PHÁT HIỆN finish MỘT LẦN DUY NHẤT cho cả turn.
        # Cờ này dùng cho CẢ quyết định turn-cuối bên dưới LẪN lối ra "finished"
        # sau khi chạy tool. (Trước đây check finish viết ở 2 nơi với 2 idiom
        # khác nhau — drift chỉ chờ xảy ra; 1 nguồn sự thật an toàn hơn.)
        # -----------------------------------------------------------------------
        finish_called = any(
            getattr(tc, "function", None) and tc.function.name == "finish"
            for tc in msg.tool_calls
        )

        # Turn cuối (i == max_iters) mà model vẫn gọi tool THƯỜNG (không finish):
        # KHÔNG chạy tool nữa — kết quả sẽ không bao giờ được gửi lại cho model,
        # và write_file/apply_patch có thể đổi đĩa mà model không kịp verify.
        # `messages.pop()` gỡ assistant message vừa append ở trên (tool_calls
        # của nó chưa hề được chạy) — giữ BẤT BIẾN ghép cặp tool_calls ↔
        # role:"tool" đúng ở MỌI điểm thoát, không chỉ tại mỗi API call (trace
        # dùng làm training data Phase-3 không được chứa orphan tool_calls).
        # Quan trọng cho SkillOpt: finish trên turn cuối vẫn phân loại "finished"
        # (model ĐÃ tuyên bố xong, không phải bị cụt vì hết turn) — nó RƠI XUỐNG
        # đường thực thi bình thường vì finish là pure-function: chạy, append
        # role:"tool", return "finished" ở dưới. Một đường thoát duy nhất.
        if i == max_iters and not finish_called:
            messages.pop()
            break

        # -----------------------------------------------------------------------
        # BƯỚC 6: NẾU CÓ TOOL_CALLS, CHẠY TỪNG CÁI VÀ TRẢ KẾT QUẢ VỀ
        # Có thể có >1 tool_call trong 1 turn (model parallel calls).
        # -----------------------------------------------------------------------

        # Tới đây chắc chắn sẽ chạy tool (đã qua BƯỚC 5.5 break) → đánh dấu agent
        # đã THỰC SỰ hành động (tắt guardrail "nói mà không làm" cho các turn sau).
        # `= True` gán giá trị True cho biến made_tool_call.
        made_tool_call = True

        # (finish_called đã được tính MỘT lần ở BƯỚC 5.5 phía trên — nếu cờ bật,
        # ta vẫn chạy đủ mọi tool_call của turn rồi mới return "finished" bên dưới.)

        # Chuẩn hóa SDK objects → dict {"id","name","arguments"} rồi giao TRỌN
        # lượt cho execute_turn (định nghĩa phía trên) — cùng MỘT khối cơ chế
        # với REPL cli/chat.py: validate/repair JSON args → chạy execute_tool →
        # append đúng 1 role:"tool" mỗi call (bất biến ghép cặp). Lợi ích mới
        # cho eval: args JSON hỏng được thay "{}" trong history nên turn sau
        # không 400, model nhận error hướng dẫn retry thay vì chết cả run.
        # type:ignore: msg.tool_calls có thể chứa CustomToolCall không có
        # .function — model hiện chỉ emit function calls (Hermes parser).
        calls = [{"id": tc.id,
                  "name": tc.function.name,        # type: ignore[union-attr]
                  "arguments": tc.function.arguments}  # type: ignore[union-attr]
                 for tc in msg.tool_calls]
        execute_turn(calls, messages, workspace)
        # Hết lượt tool — loop sang turn tiếp, model sẽ "thấy" results vừa append.

        # Model đã gọi finish() → kết thúc sạch. Đã append đủ tool result ở trên nên
        # messages hợp lệ. Phân loại "finished" (KHÔNG phải no_action — model ĐÃ hành
        # động bằng cách gọi finish). Đây là mấu chốt của finish: cho model một hành
        # động kết thúc hợp lệ thay vì trả prose suông (vốn bị tính là no_action).
        if finish_called:
            cprint(Color.FINISH, "\nAgent called finish() — task complete.")
            return {"finish_reason": "finished", "iters_used": i}

    # Rơi xuống đây = đã dùng hết max_iters turn mà model vẫn còn muốn gọi tool
    # (chưa chịu trả content trần để báo "xong"). Đây là safety net chống loop
    # vô tận — không hẳn là bug, nhưng dấu hiệu task quá khó hoặc model bị kẹt.
    #
    # Tại sao rơi xuống đây thay vì return bên trong vòng lặp?
    #   Vì ở BƯỚC 5.5, khi i == max_iters và model vẫn gọi tool thường (không
    #   finish), ta pop assistant message mồ côi rồi `break` thoát vòng for.
    #   Code tiếp tục chạy các dòng SAU vòng lặp — dòng cprint và return này.
    cprint(Color.WARN, f"\nAgent hit max_iters={max_iters} without finishing.")
    # Trả về "max_iters" — đã hết số lượt cho phép.
    return {"finish_reason": "max_iters", "iters_used": max_iters}


# ---------------------------------------------------------------------------
# ENTRY POINT — `python -m src.agent "goal"`
# Đây là entry NỘI BỘ, load-bearing: spawn_subagent (tools.py) gọi đúng lệnh
# `python -m src.agent` để chạy child agent. CLI cho người dùng là cli/solve.py
# (one-shot) và cli/chat.py (REPL) — đừng thêm tính năng "đẹp" vào đây.
# ---------------------------------------------------------------------------

# `if __name__ == "__main__":` — điều kiện đặc biệt trong Python.
# Khi chạy file TRỰC TIẾP (python src/agent.py), Python đặt biến đặc biệt
# __name__ = "__main__". Khi file được IMPORT từ file khác, __name__ = "src.agent".
# Vậy: code bên trong `if __name__ == "__main__":` CHỈ chạy khi file được
# chạy trực tiếp, KHÔNG chạy khi bị import. Đây là pattern chuẩn Python để
# viết code "chỉ chạy khi là file chính".
if __name__ == "__main__":
    # `import argparse` — nhập module argparse để xử lý tham số dòng lệnh.
    # Đặt import ở đây (thay vì đầu file) vì argparse chỉ cần khi chạy trực tiếp,
    # không cần khi import module này từ file khác.
    import argparse

    # argparse thay cho việc bóc sys.argv thủ công — cho phép --workspace (chốt
    # sandbox file ops) + --max-iters tùy chọn, và tự sinh usage/-h.

    # `argparse.ArgumentParser(description=...)` — tạo parser xử lý tham số dòng lệnh.
    # `description=` = mô tả hiển thị khi dùng --help.
    parser = argparse.ArgumentParser(
        description="ReAct coding agent. Example: "
                    "python -m src.agent 'Fix the failing tests in demo_repo/'")

    # `parser.add_argument("goal", nargs="+", help=...)` — thêm tham số bắt buộc.
    # "goal" = tên tham số (positional — không cần dấu --).
    # `nargs="+"` = nhận 1 hoặc nhiều từ (+ = "một hoặc nhiều").
    #   Ví dụ: python -m src.agent Fix the failing tests
    #   → args.goal = ["Fix", "the", "failing", "tests"]
    # positional `goal` với nargs="+" → gom MỌI từ user gõ thành 1 list, rồi
    # join lại thành câu hoàn chỉnh (giữ hành vi cũ: gõ không cần đóng ngoặc kép).
    parser.add_argument("goal", nargs="+", help="natural-language task description")

    # `parser.add_argument("--workspace", default="demo_repo", help=...)` — tham số tùy chọn.
    # "--workspace" bắt đầu bằng -- → tùy chọn (có thể bỏ qua, dùng default).
    # `default="demo_repo"` = nếu không truyền --workspace, mặc định là "demo_repo".
    # --workspace: thư mục các FILE TOOL được phép đọc/ghi (qua _safe_path).
    # Lưu ý trung thực: run_bash/run_python KHÔNG bị chặn bởi workspace — chúng
    # vẫn với tới đường dẫn tuyệt đối. Default demo_repo/ chỉ chống tai nạn
    # đường dẫn, không chống self-modification qua bash. Xem TRUST MODEL ở tools.py.
    parser.add_argument("--workspace", default="demo_repo",
                        help="sandbox directory the agent may read/write (default: demo_repo)")

    # `type=int` = tự động chuyển chuỗi từ command line thành số nguyên.
    # `default=None` = nếu không truyền, giá trị là None (sẽ dùng default của run_agent).
    # --max-iters tùy chọn: bỏ trống thì dùng default của run_agent (15).
    parser.add_argument("--max-iters", type=int, default=None,
                        help="max ReAct turns (default: run_agent's 15)")

    # `args = parser.parse_args()` — đọc và phân tích tham số từ sys.argv.
    # Sau lệnh này, args.goal, args.workspace, args.max_iters có giá trị từ CLI.
    args = parser.parse_args()

    # `" ".join(args.goal)` — nối list thành chuỗi, phân cách bằng dấu cách.
    # `" ".join(["Fix", "the", "tests"])` = "Fix the tests"
    # Join các từ goal thành 1 câu. Path(...).resolve() biến --workspace thành
    # đường dẫn tuyệt đối trước khi đưa vào run_agent (tool ops chốt vào đây).
    task = " ".join(args.goal)

    # `Path(args.workspace).resolve()` — tạo Path object rồi chuyển thành đường
    # dẫn tuyệt đối. resolve() = "tính toán đường dẫn đầy đủ từ thư mục hiện tại".
    # Ví dụ: Path("demo_repo").resolve() → Path("/home/user/code/project/demo_repo")
    workspace = Path(args.workspace).resolve()

    cprint(Color.HEADER, f"GOAL: {task}\n")

    # `if args.max_iters is not None:` — kiểm tra user có truyền --max-iters không.
    # Nếu có → truyền vào run_agent. Nếu không → dùng default của hàm (15).
    # Chỉ truyền max_iters khi user có chỉ định → nếu không, dùng default của hàm.
    if args.max_iters is not None:
        # `run_agent(task, workspace=workspace, max_iters=args.max_iters)` — gọi hàm
        # run_agent với 3 tham số.
        # `workspace=workspace` là keyword argument — tên tham số = giá trị.
        run_agent(task, workspace=workspace, max_iters=args.max_iters)
    else:
        # Không truyền max_iters → run_agent dùng default = 15.
        run_agent(task, workspace=workspace)
