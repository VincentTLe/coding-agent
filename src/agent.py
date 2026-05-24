"""
agent.py — ReAct-style coding agent that uses tools to complete a task.

WHAT THIS FILE DOES
  Takes a natural-language goal (e.g. "Fix the failing tests in demo_repo/"),
  calls an LLM that may invoke any of the 10 tools defined in src/tools.py
  (read_file, write_file, apply_patch, multi_edit, grep_files, glob_files,
  list_dir, run_bash, run_python, spawn_subagent), keeps looping until the
  model is satisfied (returns content with no more tool_calls), or we hit
  `max_iters` and give up.

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
  (Or use examples/05_agent_loop.py for the prettier demo CLI.)
"""

from __future__ import annotations

# `logging` thay cho `print()` — sau này có thể redirect log vào file để
# thu thập trace cho fine-tuning ở Phase 3. Đây là Rule C trong AGENTS.md.
import logging
import os
from pathlib import Path

# Đọc biến môi trường từ .env (BASE_URL, MODEL_NAME, API_KEY) — y hệt 01_chat.py.
from dotenv import load_dotenv

# OpenAI SDK — bao bọc HTTP/JSON, cho phép swap backend bằng cách đổi base_url.
# `OpenAIError` là base class của MỌI lỗi SDK (timeout, 5xx, kết nối rớt, 400 do
# context tràn). Bắt nó ở vòng lặp để 1 lỗi transient không kill cả run_agent —
# xem BƯỚC 1 bên dưới để hiểu vì sao việc này quan trọng cho tính đúng đắn.
from openai import OpenAI, OpenAIError

# TypedDict cho 1 message — chỉ dùng type hint giúp Pylance không kêu
# "list[dict] không phải Iterable[ChatCompletionMessageParam]" khi truyền vào create().
from openai.types.chat import ChatCompletionMessageParam

# Lấy 3 thứ từ tools.py:
#   - TOOL_SCHEMAS: danh sách JSON schema mô tả tools (model nhìn vào để biết gọi sao)
#   - execute_tool: dispatcher chạy tool theo name + args
#   - set_workspace: chốt thư mục agent được phép đọc/ghi (sandbox)
from src.tools import TOOL_SCHEMAS, execute_tool, set_workspace

# System prompt — tách ra file riêng để sau này dễ versioning cho training data.
from src.prompts import SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# ANSI color codes — tô màu output để prof nhìn dễ phân biệt từng phần.
# Không cần thư viện ngoài, chỉ là escape codes terminal hiểu sẵn.
# ---------------------------------------------------------------------------

# Mỗi mã ANSI là chuỗi đặc biệt báo terminal "đổi màu chữ kể từ đây".
# `\033[XXm` = bắt đầu màu. `\033[0m` = reset về mặc định.
class Color:
    HEADER = "\033[1;34m"   # bold blue — cho dòng "=== Turn N ==="
    TOOL = "\033[1;32m"     # bold green — cho dòng "[tool] tool_name(...)"
    RESULT = "\033[33m"     # yellow — cho dòng "[tool result]"
    ASSISTANT = "\033[1;35m"  # bold magenta — cho "[assistant] ..."
    FINISH = "\033[1;36m"   # bold cyan — cho "Agent finished."
    WARN = "\033[1;31m"     # bold red — cho cảnh báo
    RESET = "\033[0m"       # tắt mọi màu


def cprint(color: str, text: str) -> None:
    """In ra text có màu. Dùng `log.info` thay vì `print` để consistent.

    Tại sao tách hàm này? — Tránh lặp `{Color.X}...{Color.RESET}` ở 5 chỗ.
    """
    log.info(f"{color}{text}{Color.RESET}")


# ---------------------------------------------------------------------------
# Setup (same shape as 01_chat.py — đọc .env, tạo client, set logging)
# ---------------------------------------------------------------------------

# Đọc file .env vào os.environ. Có file ./.env thì auto detect.
load_dotenv()

# Đọc 3 biến cấu hình. Nếu thiếu BASE_URL hay MODEL → crash ngay (fail fast).
# API_KEY có default vì vLLM không enforce auth.
BASE_URL = os.environ["VLLM_BASE_URL"]
MODEL = os.environ["VLLM_MODEL_NAME"]
API_KEY = os.environ.get("VLLM_API_KEY", "not-needed")

# Tạo OpenAI client trỏ vào vLLM. Đây chính là pattern "portability" — chỉ cần
# đổi base_url trong .env là chạy được với GPT-4 cloud, Ollama, Claude proxy, ...
client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

# Cấu hình logging. `format="%(message)s"` = chỉ in nội dung message, không in
# timestamp/level — gọn cho demo. Level INFO = thấy mọi log.info().
logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("agent")


# ---------------------------------------------------------------------------
# THE AGENT LOOP — trái tim của hệ thống
# ---------------------------------------------------------------------------

def run_agent(goal: str, max_iters: int = 15) -> None:
    """Run the ReAct loop until the model stops calling tools, or max_iters.

    ReAct = Reasoning + Acting interleaved. Each iteration:
      - reason:  model thinks, may produce visible content.
      - act:     model emits tool_calls (or nothing -> we're done).
      - observe: we execute each tool and append result as role=tool.
    Termination: model returns NO tool_calls (it has decided it's done).
    """
    # Khởi tạo "cuốn sổ ký ức" (messages list) — y hệt 01_chat.py, nhưng nay
    # chứa cả system prompt VÀ goal của user (2 message ban đầu).
    # Dùng OpenAI TypedDict để Pylance pass-through; dict literal vẫn assign được
    # vì TypedDict là structural typing (chỉ check keys + value types).
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": goal},
    ]

    # Vòng lặp giới hạn `max_iters` turn — safety net để agent không loop vô tận.
    # Mỗi turn = 1 round-trip với model + thực thi tool nếu có.
    for i in range(1, max_iters + 1):
        # Header phân tách từng turn — dễ nhìn khi demo.
        cprint(Color.HEADER, f"\n=== Turn {i} (history: {len(messages)} messages) ===")

        # -----------------------------------------------------------------------
        # BƯỚC 1: GỌI API (REASON)
        # Khác 01_chat.py ở 2 tham số mới:
        #   - tools=TOOL_SCHEMAS: gửi danh sách tool cho model biết
        #   - tool_choice="auto": cho model TỰ QUYẾT có gọi tool không
        # ("required" sẽ ép gọi tool mỗi turn — không phù hợp vì cần model có
        # khả năng "kết thúc" bằng cách trả về content trần)
        # -----------------------------------------------------------------------
        # type:ignore: TOOL_SCHEMAS là list[dict] (xem tools.py), không exact
        # match OpenAI TypedDict ChatCompletionToolUnionParam. Runtime hợp lệ vì
        # dict shape khớp schema OpenAI mong đợi.
        #
        # Bọc try/except quanh CHỈ lời gọi API: nếu vLLM rớt mạng, trả 5xx, hay
        # context vượt quá window (400), exception sẽ bubble ra ngoài và giết
        # cả run_agent — eval/run.py sẽ tính nguyên task là crash. Bắt ở đây để
        # log lỗi (Rule C: verbose) rồi return GỌN GÀNG.
        # An toàn về tính đúng đắn: tại điểm này messages list đang Ở TRẠNG THÁI
        # HỢP LỆ (mọi assistant-tool_calls trước đó đã có đủ tool message ghép
        # cặp). Vì ta return TRƯỚC khi append assistant message mới, list không
        # bao giờ bị bỏ lại với 1 assistant.tool_calls "mồ côi" không có kết quả.
        try:
            resp = client.chat.completions.create(  # type: ignore[arg-type]
                model=MODEL,
                messages=messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
                max_tokens=2048,
            )
        except OpenAIError as e:
            cprint(Color.WARN, f"\nAPI error on turn {i}: {e}. Stopping.")
            return

        # -----------------------------------------------------------------------
        # BƯỚC 2: BÓC LẤY MESSAGE (giống 01_chat.py)
        # resp.choices là list — nếu n=1 (default), index 0 là câu trả lời duy nhất.
        # msg là Pydantic object có .content, .role, .tool_calls, .reasoning, ...
        # -----------------------------------------------------------------------
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
        # model_dump trả về dict[str, Any], không exact-match TypedDict
        # ChatCompletionMessageParam → type:ignore. Runtime hoàn toàn ổn vì
        # dict shape khớp schema OpenAI; chỉ type checker khó tính.
        messages.append(msg.model_dump(exclude_none=True))  # type: ignore[arg-type]

        # -----------------------------------------------------------------------
        # BƯỚC 4: NẾU MODEL CÓ CONTENT (= nói chuyện), IN RA
        # Content có thể None khi model chỉ gọi tool không nói gì.
        # Khi có content, đây là lúc model "narrate" (giải thích nó đang làm gì).
        # -----------------------------------------------------------------------
        if msg.content:
            cprint(Color.ASSISTANT, f"[assistant] {msg.content}")

        # -----------------------------------------------------------------------
        # BƯỚC 5: NẾU KHÔNG CÓ TOOL_CALLS, AGENT KẾT THÚC
        # Quy ước ReAct: model dừng gọi tool = model nghĩ task xong → mình tin nó.
        # `not msg.tool_calls` true khi tool_calls là None HOẶC list rỗng.
        # -----------------------------------------------------------------------
        if not msg.tool_calls:
            cprint(Color.FINISH, "\nAgent finished.")
            return

        # -----------------------------------------------------------------------
        # BƯỚC 5.5: NẾU ĐÂY LÀ TURN CUỐI (i == max_iters) MÀ MODEL VẪN GỌI TOOL,
        # KHÔNG chạy tool nữa. Lý do: kết quả tool ở turn cuối sẽ KHÔNG bao giờ
        # được gửi lại cho model (vòng lặp kết thúc ngay sau), nên chạy chúng chỉ
        # phí công — tệ hơn, có thể là write_file/apply_patch làm thay đổi đĩa mà
        # model không kịp verify. Dừng tại đây và rơi xuống cảnh báo max_iters.
        # -----------------------------------------------------------------------
        if i == max_iters:
            break

        # -----------------------------------------------------------------------
        # BƯỚC 6: NẾU CÓ TOOL_CALLS, CHẠY TỪNG CÁI VÀ TRẢ KẾT QUẢ VỀ
        # Có thể có >1 tool_call trong 1 turn (model parallel calls).
        # -----------------------------------------------------------------------
        for tc in msg.tool_calls:
            # type:ignore: msg.tool_calls có thể chứa ChatCompletionMessageCustomToolCall
            # (không có .function). Hiện model chỉ emit function calls (Hermes parser)
            # nên runtime ổn — Pylance khó tính.
            # Log tên tool + arguments TRƯỚC khi chạy → debug được tool nào hang.
            cprint(Color.TOOL, f"[tool] {tc.function.name}({tc.function.arguments})")  # type: ignore[union-attr]

            # execute_tool tự parse JSON args + dispatch theo name. Nó luôn trả
            # về string (kể cả khi có lỗi — string bắt đầu bằng "ERROR:").
            result = execute_tool(tc.function.name, tc.function.arguments)  # type: ignore[union-attr]

            # Cắt bớt khi log để khỏi spam terminal. Model vẫn nhận FULL kết quả
            # qua append messages bên dưới.
            preview = result if len(result) < 500 else result[:500] + "...[truncated]"
            cprint(Color.RESULT, f"[tool result]\n{preview}")

            # Append tool result theo format chuẩn OpenAI:
            #   role: "tool"
            #   tool_call_id: phải khớp với tc.id để API biết kết quả này thuộc call nào
            #   content: chuỗi kết quả (model đọc chuỗi này ở turn sau)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })
        # Hết for — loop sang turn tiếp theo, model sẽ "thấy" tool results vừa append.

    # Rơi xuống đây = đã dùng hết max_iters turn mà model vẫn còn muốn gọi tool
    # (chưa chịu trả content trần để báo "xong"). Đây là safety net chống loop
    # vô tận — không hẳn là bug, nhưng dấu hiệu task quá khó hoặc model bị kẹt.
    cprint(Color.WARN, f"\nAgent hit max_iters={max_iters} without finishing.")


# ---------------------------------------------------------------------------
# ENTRY POINT — `python -m src.agent "goal"`
# (Để gọn, examples/05_agent_loop.py là CLI wrapper "đẹp hơn" cho demo)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.agent 'task description'")
        print("Example: python -m src.agent 'Fix the failing tests in demo_repo/'")
        sys.exit(1)

    # Chốt sandbox file ops vào demo_repo/ — agent không thể "đi lạc" sang sửa
    # src/agent.py của chính mình. Nếu sửa được, ta đã có "self-modification"
    # nhưng đó là Phase 4 — chưa phải bây giờ.
    set_workspace(Path(__file__).parent.parent / "demo_repo")

    # sys.argv[0] là tên script. sys.argv[1:] là các từ user gõ → join lại
    # thành 1 câu hoàn chỉnh cho agent.
    task = " ".join(sys.argv[1:])
    cprint(Color.HEADER, f"GOAL: {task}\n")
    run_agent(task)
