"""
cli/chat.py — Interactive REPL chat với coding agent (giống Claude Code / Codex).

KHÁC `cli/solve.py` Ở ĐÂU
  solve.py là ONE-SHOT: gõ task qua argv → chạy đến hết → thoát.
  chat.py là REPL nhiều turn: bạn gõ → agent stream từng token + thinking + tool calls
  → kết thúc 1 lượt → bạn gõ tiếp → ...
  History tích lũy trong cùng 1 session (giống chat với Claude Code).

3 TÍNH NĂNG MỚI SO VỚI solve.py
  1. STREAMING: `stream=True` → nhận từng delta thay vì chờ cả response.
  2. THINKING HIỆN REAL-TIME: vLLM khởi động với `--reasoning-parser qwen3`
     nên Qwen3-14B emit `<think>...</think>` được tách thành field `reasoning_content`
     riêng. Mình in màu trắng sáng (Color.THINKING) ngay khi nó chảy về.
  3. TOOL CALL STEP-BY-STEP: hiện ngay tool name + args (green) và result (yellow)
     trước khi model viết câu trả lời tiếp.

LỆNH SLASH (nguồn duy nhất: tuple COMMANDS bên dưới — /help và banner render từ đó)
  /exit, /quit, /q     thoát
  /clear, /reset       xoá history (giữ system prompt)
  /think, /deep        bật chế độ deep thinking (model thinks before each turn)
  /nothink, /fast      tắt thinking (fast mode — mặc định)
  /mode                xem mode hiện tại
  /tokens, /tok        ước lượng tokens của history so với context window
  /compact             summarize history ngay (không chờ auto-trigger)
  /help, /?            hiện danh sách lệnh

CÁCH CHẠY
  cd ~/code/coding-agent && source .venv/bin/activate
  python cli/chat.py                              # workspace = demo_repo
  python cli/chat.py --workspace /tmp/playground  # workspace khác
"""

# `from __future__ import annotations` — bật lazy type hints (`list[dict]` chỉ
# là chuỗi, không bị tính ngay). Xem giải thích chi tiết trong eval/run.py.
from __future__ import annotations

# ---------------------------------------------------------------------------
# IMPORT SECTION
# ---------------------------------------------------------------------------
# `import` là từ khóa Python để "nhập" code từ nơi khác vào file này.
# Giống như trong Excel bạn copy công thức từ sheet khác — import cho phép
# dùng hàm/class đã có sẵn mà không cần tự viết lại.

# `argparse` — thư viện chuẩn của Python để xử lý tham số dòng lệnh.
# Ví dụ: khi bạn gõ `python chat.py --workspace /tmp`, argparse đọc
# `--workspace /tmp` và biến nó thành `args.workspace = "/tmp"`.
import argparse

# `logging` — thư viện chuẩn để in thông báo debug/info/warning ra console
# hoặc file. Khác print() ở chỗ: có level (DEBUG/INFO/WARNING/ERROR) và
# có thể bật/tắt theo level.
import logging

# `sys` — thư viện chuẩn để tương tác với Python runtime.
# sys.path → danh sách thư mục Python tìm kiếm khi import.
# sys.exit(0) → thoát chương trình với mã 0 (0 = thành công).
# sys.stdin → luồng đầu vào chuẩn (keyboard).
import sys

# `Path` từ thư viện `pathlib` — class đại diện cho đường dẫn file/thư mục.
# Dùng Path thay vì chuỗi thuần giúp code portable (Windows dùng \, Linux/Mac
# dùng /) và có nhiều phương thức tiện lợi như .parent, .resolve(), .exists().
from pathlib import Path

# Thêm project root vào sys.path TRƯỚC khi import src/ — khi chạy
# `python cli/chat.py`, Python chỉ thấy thư mục cli/, không thấy src/.
# Xem giải thích chi tiết từng bước trong eval/run.py.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# `from openai import OpenAI` — chỉ dùng làm TYPE HINT (client: OpenAI) ở các
# hàm dưới. Client THẬT được dựng bởi get_client() trong src/agent.py — một
# nguồn cấu hình duy nhất (models.json), không tự dựng client ở đây nữa.
from openai import OpenAI

# Tái dùng tools + prompt y nguyên — không duplicate.
# `TOOL_SCHEMAS` là list mô tả các tool (hàm) mà model có thể gọi.
# (execute_tool không import trực tiếp nữa — việc THỰC THI tool của REPL đi
# qua src.agent.execute_turn, cùng cơ chế với run_agent.)
from src.tools import TOOL_SCHEMAS

# `SYSTEM_PROMPT` là chuỗi văn bản định nghĩa "nhân cách" và quy tắc của agent.
# Luôn được đặt là message đầu tiên với role="system".
from src.prompts import SYSTEM_PROMPT

# Dùng chung hạ tầng với src/agent.py thay vì tự chế bản sao ở đây:
#   - Color           : bảng màu ANSI duy nhất của cả project (palette 1 chỗ).
#   - get_client()    : OpenAI client singleton, đã hardened (timeout=120s,
#                       max_retries=1) — trước đây chat.py tự dựng OpenAI(...)
#                       từ VLLM_* env vars, KHÔNG timeout và bỏ qua models.json.
#   - get_model()     : tên model từ cùng nguồn cấu hình.
#   - load_model_config(): ModelConfig (context_window, max_tokens...) từ
#                       models.json, fallback .env — load_dotenv gọi bên trong.
from src.agent import Color, execute_turn, get_client, get_model, load_model_config
# Compaction: CƠ CHẾ sống ở src/compaction.py (module sâu, có unit test);
# file này chỉ giữ CHÍNH SÁCH (ngưỡng auto-trigger tính từ models.json).
from src.compaction import KEEP_RECENT_MESSAGES, compact_messages, estimate_tokens


# ---------------------------------------------------------------------------
# Auto-compaction — giữ conversation history dưới context limit
# ---------------------------------------------------------------------------
# PROBLEM: context window có hạn (Qwen3-14B: 32K, đọc từ models.json). Qua
# 20-30 turn, history vượt limit → vLLM 400 "context length exceeded".
# Giải pháp kiểu Claude Code: summarize các turn cũ, giữ recent verbatim.
# CƠ CHẾ (estimate_tokens + compact_messages + bất biến split-tại-user) nằm
# ở src/compaction.py — đọc docstring bên đó. Ở đây chỉ còn NGƯỠNG trigger.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# HẰNG SỐ (CONSTANTS)
# ---------------------------------------------------------------------------
# Hằng số là biến mà giá trị KHÔNG thay đổi trong suốt chương trình.
# Quy ước Python: viết HOA toàn bộ tên (ví dụ COMPACT_THRESHOLD_TOKENS).
# Đây chỉ là quy ước — Python không ngăn bạn thay đổi, nhưng viết hoa
# báo hiệu "đừng sửa cái này trong lúc chạy".

# Cấu hình model active (models.json, fallback .env) — NGUỒN DUY NHẤT cho
# context_window / max_tokens / base_url. Trước đây file này tự hardcode
# MAX_MODEL_LEN=32768 và max_tokens=2048, có thể lệch với models.json.
# lru_cache trong load_model_config → cùng object với cái get_client() dùng.
cfg = load_model_config()

# Trigger point: khi estimated tokens vượt threshold, auto-compact TRƯỚC
# stream call tiếp theo. 75% context window (32K → 24576) — đủ headroom cho
# next response (cfg.max_tokens) + tool results. KHÔNG hardcode 24000 nữa:
# đổi model trong models.json là threshold tự scale theo.
# `int(...)` vì context_window * 0.75 trả float — token count phải là int.
COMPACT_THRESHOLD_TOKENS = int(cfg.context_window * 0.75)

# ---------------------------------------------------------------------------
# SLASH COMMANDS — NGUỒN DUY NHẤT
# ---------------------------------------------------------------------------
# Một tuple (tên_lệnh, mô_tả) duy nhất; cả /help LẪN banner render từ đây.
# Trước đây danh sách lệnh bị chép tay 3 chỗ (docstring, /help, banner) và
# đã lệch nhau (thiếu /compact, /tokens) — giờ thêm lệnh mới chỉ sửa 1 chỗ.
# Tuple lồng tuple (immutable) thay vì list: báo hiệu "data tĩnh, đừng mutate".
COMMANDS: tuple[tuple[str, str], ...] = (
    ("/exit /quit /q", "thoát REPL"),
    ("/clear /reset", "xoá history (giữ system prompt)"),
    ("/think /deep", "bật deep thinking (model nghĩ trước mỗi turn)"),
    ("/nothink /fast", "tắt thinking (fast mode — mặc định)"),
    ("/mode", "xem thinking mode hiện tại"),
    ("/tokens /tok", "ước lượng tokens của history so với context window"),
    ("/compact", "summarize history ngay (không chờ auto-trigger)"),
    ("/help /?", "hiện danh sách lệnh này"),
)


# ---------------------------------------------------------------------------
# HÀM stream_one_turn
# ---------------------------------------------------------------------------
# Đây là hàm quan trọng nhất — thực hiện 1 vòng giao tiếp với model.
# `client: OpenAI` — API client.
# `model: str` — tên model.
# `messages: list` — lịch sử hội thoại.
# `thinking_enabled: bool = False` — tham số tùy chọn, mặc định False.
# `-> tuple[str, list[dict]]` — trả về (content, danh_sách_tool_calls).
def stream_one_turn(
    client: OpenAI,
    model: str,
    messages: list,
    thinking_enabled: bool = False,
) -> tuple[str, list[dict]]:
    """Stream 1 round-trip với model. Trả về (content_buf, tool_calls).

    In ra thinking (white) + content (magenta) ngay khi delta về.
    Accumulate tool_calls từ các chunk vì OpenAI stream chia tool_calls qua nhiều delta.

    thinking_enabled: bật/tắt block <think>...</think> của Qwen3 qua chat template.
    """
    # ---------------------------------------------------------------------------
    # GỌI API VỚI stream=True
    # ---------------------------------------------------------------------------
    # Bình thường (stream=False), `client.chat.completions.create()` CHỜ cho đến
    # khi model tạo xong toàn bộ response rồi mới trả về. Với văn bản dài (vài
    # nghìn token), bạn có thể chờ 10-30 giây trước khi thấy bất kỳ chữ nào.
    #
    # `stream=True` thay đổi cách hoạt động hoàn toàn: thay vì chờ, server GỬI
    # NGAY từng mảnh nhỏ (chunk) khi vừa tạo ra, theo giao thức SSE
    # (Server-Sent Events). Kết quả là `stream` không phải là response hoàn chỉnh
    # mà là một ITERATOR (đối tượng có thể lặp) — mỗi lần lặp nhận 1 chunk.
    #
    # ITERATOR là gì? Hãy nghĩ đến vòi nước: iterator là vòi nước, mỗi lần bạn
    # "hỏi" (gọi next()), nó nhả ra 1 giọt nước (1 chunk). Khác list/tuple:
    # list là cái xô đã chứa đầy nước — bạn có thể đọc bất kỳ chỗ nào ngay lập tức.
    # Iterator phải đọc TUẦN TỰ và chỉ đọc 1 lần (không rewind).
    #
    # `extra_body.chat_template_kwargs.enable_thinking` — Qwen3 native flag để
    # bật/tắt thinking. vLLM forward thẳng sang chat template.
    # type:ignore: messages là list[dict] và TOOL_SCHEMAS cũng là list[dict].
    # Không ép sang OpenAI TypedDict cho đỡ ràng buộc cứng — runtime hợp lệ
    # vì dict shape khớp schema, Pylance chỉ kêu vì TypedDict strict.
    stream = client.chat.completions.create(  # type: ignore[arg-type,call-overload]
        model=model,
        messages=messages,
        tools=TOOL_SCHEMAS,
        tool_choice="auto",      # "auto" = model tự quyết có dùng tool hay không
        max_tokens=cfg.max_tokens,  # trần độ dài response — từ ModelConfig (models.json)
        stream=True,             # BẬT streaming — đây là từ khóa quan trọng!
        extra_body={"chat_template_kwargs": {"enable_thinking": thinking_enabled}},
    )

    # `content_buf = ""` — buffer tích lũy toàn bộ visible content.
    # Buffer = vùng nhớ tạm. Mỗi chunk chỉ có 1 mảnh nhỏ của text (delta.content),
    # ta cộng dồn vào `content_buf` để cuối cùng có chuỗi đầy đủ.
    content_buf = ""        # tích luỹ visible content qua các delta (cần trả về để lưu history)

    # Thinking KHÔNG cần tích luỹ: ta chỉ in nó ra để user xem, không lưu vào
    # history (reasoning_content không gửi lại model ở turn sau). `in_thinking`
    # đủ để biết đã in header chưa — không cần buffer riêng.

    # TOOL CALLS — CƠ CHẾ GHÉP MẢNH QUAN TRỌNG:
    # Khi model muốn gọi tool, nó không gửi toàn bộ tool call trong 1 chunk.
    # Thay vào đó, thông tin được chia nhỏ và rải qua NHIỀU CHUNK:
    #   Chunk 1: tool_call.id = "call_abc123", tool_call.name = "read_file"
    #   Chunk 2: tool_call.arguments = '{"path": "/hom'
    #   Chunk 3: tool_call.arguments = 'e/user/file.txt"}'
    # Ta phải ghép (accumulate) các mảnh này lại để có tool call hoàn chỉnh.
    #
    # `tool_calls: dict[int, dict] = {}` — dict (dictionary) rỗng.
    # dict là kiểu dữ liệu ánh xạ key → value: {"key1": value1, "key2": value2}.
    # `dict[int, dict]` — type hint: key là int (index), value là dict (tool call data).
    # Model có thể gọi NHIỀU tool song song — mỗi tool có một `index` riêng.
    # `{}` là dict rỗng trong Python (không nhầm với set hay block code).
    tool_calls: dict[int, dict] = {}

    in_thinking = False     # đang trong block thinking? (bool: True/False)
    in_content = False      # đang trong block content?

    # ---------------------------------------------------------------------------
    # VÒNG LẶP FOR TRÊN STREAM — TRÁI TIM CỦA STREAMING
    # ---------------------------------------------------------------------------
    # `for chunk in stream:` — đây là vòng lặp ITERATOR.
    # `stream` là iterator (đối tượng có thể lặp). Mỗi lần lặp:
    #   - Python gọi `next(stream)` ẩn sau hậu trường.
    #   - `next()` gửi HTTP request nhận chunk tiếp theo TỪ SERVER (blocking I/O).
    #   - Chunk được gán vào biến `chunk`.
    #   - Khi server gửi xong (event "data: [DONE]"), vòng lặp tự dừng.
    # Nhờ cơ chế này, ta xử lý từng mảnh ngay khi về, không cần chờ tất cả.
    #
    # So sánh với list thông thường:
    #   for item in [1, 2, 3]: → tất cả đã trong bộ nhớ, lặp qua ngay.
    #   for chunk in stream:   → mỗi chunk đến từ mạng, phải chờ từng cái.
    for chunk in stream:
        # Phòng trường hợp chunk rỗng (vLLM thi thoảng emit chunk không choices).
        # `if not chunk.choices:` — `chunk.choices` là list; `not list` = True khi list rỗng.
        # `continue` — bỏ qua phần còn lại của vòng lặp, chuyển sang chunk tiếp theo.
        if not chunk.choices:
            continue
        # `chunk.choices[0].delta` — truy cập:
        #   .choices    → list các choice (thường chỉ 1 khi stream)
        #   [0]         → choice đầu tiên
        #   .delta      → MẢNH THAY ĐỔI của chunk này (delta = "thay đổi nhỏ").
        #                  Khác .message (response hoàn chỉnh): .delta chỉ chứa
        #                  phần MỚI trong chunk này, không phải toàn bộ.
        delta = chunk.choices[0].delta

        # -----------------------------------------------------------------------
        # PHẦN 1: XỬ LÝ THINKING (suy nghĩ nội bộ của model)
        # -----------------------------------------------------------------------
        # vLLM với `--reasoning-parser qwen3` tách `<think>...</think>` ra field
        # riêng. Field name là `reasoning_content` trong vLLM (một số version là
        # `reasoning` — getattr với fallback để tương thích cả hai).
        #
        # `getattr(obj, name, default)` — hàm built-in lấy thuộc tính của object.
        # Cú pháp: getattr(đối_tượng, "tên_thuộc_tính", giá_trị_mặc_định)
        # Ví dụ: getattr(delta, "reasoning_content", None)
        #   → Nếu delta có thuộc tính reasoning_content, trả về giá trị đó.
        #   → Nếu không có (AttributeError), trả về None (không crash).
        # Tại sao không dùng delta.reasoning_content trực tiếp? Vì nếu thuộc
        # tính không tồn tại, Python ném AttributeError → crash. getattr an toàn hơn.
        #
        # `or getattr(delta, "reasoning", None)` — nếu reasoning_content là None
        # (falsy), thử field "reasoning" (tên trong một số phiên bản vLLM cũ hơn).
        r = getattr(delta, "reasoning_content", None) or getattr(delta, "reasoning", None)
        if r:
            if not in_thinking:
                # Header chỉ in 1 lần khi bắt đầu thinking — không spam.
                # `flush=True` — ép Python ghi buffer ra terminal NGAY.
                # Bình thường Python buffer output để tối ưu I/O; flush=True tắt buffer.
                print(f"\n{Color.FINISH}[thinking]{Color.RESET}", flush=True)
                in_thinking = True
                in_content = False
            # `end=""` — tham số của print(): mặc định print thêm "\n" (xuống dòng)
            # sau mỗi lần gọi. `end=""` thay bằng chuỗi rỗng → không xuống dòng.
            # Nhờ vậy các mảnh thinking nối liền nhau thành 1 đoạn văn liên tục.
            # `flush=True` — ghi ngay, không đợi buffer đầy.
            print(f"{Color.THINKING}{r}{Color.RESET}", end="", flush=True)

        # -----------------------------------------------------------------------
        # PHẦN 2: XỬ LÝ VISIBLE CONTENT (câu trả lời thực sự của model)
        # -----------------------------------------------------------------------
        # `delta.content` là field chứa mảnh văn bản hiển thị cho user.
        # Khác `delta.reasoning_content` (suy nghĩ nội bộ):
        #   - reasoning_content: quá trình suy luận, KHÔNG gửi lại model, chỉ hiển thị
        #   - content: câu trả lời thực, được LƯU VÀO HISTORY và gửi cho model ở turn sau
        if delta.content:
            if not in_content:
                # Nếu vừa thoát thinking → xuống dòng để close block đó.
                # `in_thinking` → vừa đang ở chế độ thinking.
                if in_thinking:
                    print()  # print() không tham số → in dòng trống (chỉ xuống dòng)
                print(f"\n{Color.ASSISTANT}[assistant]{Color.RESET}", flush=True)
                in_content = True
                in_thinking = False
            # `end=""` + `flush=True` → in mảnh ngay, không xuống dòng.
            # `content_buf += delta.content` — cộng dồn mảnh mới vào buffer.
            print(f"{Color.ASSISTANT}{delta.content}{Color.RESET}", end="", flush=True)
            content_buf += delta.content

        # -----------------------------------------------------------------------
        # PHẦN 3: XỬ LÝ TOOL CALLS (yêu cầu gọi công cụ)
        # -----------------------------------------------------------------------
        # Khi model quyết định gọi tool, nó không gửi text trong delta.content
        # mà gửi trong delta.tool_calls — một list các tool_call delta.
        #
        # TẠI SAO TOOL CALLS ĐẾN THEO TỪNG MẢNH?
        # Vì streaming gửi từng token một. JSON arguments có thể dài (ví dụ:
        # nội dung file cần ghi). Nếu chờ cả arguments xong mới gửi, streaming
        # mất ý nghĩa. Nên server gửi từng mảnh JSON khi vừa tạo ra.
        #
        # CẤU TRÚC GHÉP MẢNH:
        # `tool_calls[idx]` là dict lưu trạng thái ghép cho tool có index `idx`.
        # Mỗi chunk tool_call có:
        #   - `.index`           → vị trí trong danh sách (model gọi nhiều tool cùng lúc)
        #   - `.id`              → ID duy nhất (ví dụ "call_abc123"), thường đến ở chunk đầu
        #   - `.function.name`   → tên tool (ví dụ "read_file"), thường đến ở chunk đầu
        #   - `.function.arguments` → chuỗi JSON, ĐẾN THEO NHIỀU CHUNK (mỗi chunk 1 phần)
        if delta.tool_calls:
            # `for tcd in delta.tool_calls:` — lặp qua list tool_call delta trong chunk này.
            # Thường chỉ có 1 tcd/chunk, nhưng protocol cho phép nhiều.
            for tcd in delta.tool_calls:
                # `tcd.index` — chỉ số (index) của tool call này trong danh sách tổng.
                # Dùng làm KEY trong dict `tool_calls` để gom tất cả chunks của cùng 1 tool.
                idx = tcd.index
                # Nếu chưa thấy index này → tạo dict rỗng mới để bắt đầu ghép.
                # `if idx not in tool_calls:` — `not in` kiểm tra key KHÔNG có trong dict.
                if idx not in tool_calls:
                    # `{"id": "", "name": "", "arguments": ""}` — dict với 3 key,
                    # tất cả bắt đầu là chuỗi rỗng để sẵn sàng cộng dồn.
                    tool_calls[idx] = {"id": "", "name": "", "arguments": ""}
                # `if tcd.id:` — nếu chunk này có id (không None, không rỗng)
                if tcd.id:
                    # `+=` cộng dồn chuỗi. ID thường chỉ đến 1 lần nhưng dùng +=
                    # để an toàn (không mất nếu có edge case).
                    tool_calls[idx]["id"] += tcd.id
                # `if tcd.function:` — nếu chunk này có thông tin function
                if tcd.function:
                    if tcd.function.name:
                        # Ghép tên hàm (thường đến 1 lần, ngắn)
                        tool_calls[idx]["name"] += tcd.function.name
                    if tcd.function.arguments:
                        # Ghép arguments — phần này ĐẾN NHIỀU LẦN vì JSON dài.
                        # Ví dụ: `'{"pa'` + `'th": '` + `'"/etc"}' → '{"path": "/etc"}'`
                        tool_calls[idx]["arguments"] += tcd.function.arguments

    # Hết stream — xuống dòng cho đẹp (print() không tham số = in newline).
    print()

    # `return content_buf, [tool_calls[i] for i in sorted(tool_calls)]`
    #
    # RETURN TUPLE: (chuỗi_content, list_tool_calls)
    #
    # `[tool_calls[i] for i in sorted(tool_calls)]` — LIST COMPREHENSION.
    # List comprehension là cú pháp ngắn gọn để tạo list từ iterable:
    #   [biểu_thức for biến in iterable]
    # Ví dụ: [x*2 for x in [1,2,3]] → [2, 4, 6]
    #
    # `sorted(tool_calls)` — hàm built-in `sorted()` trả về list các KEY của
    # dict `tool_calls`, đã được sắp xếp tăng dần. Vì key là int (index 0, 1, 2...),
    # sắp xếp đảm bảo tool calls được trả về đúng thứ tự model yêu cầu.
    # `tool_calls[i]` → lấy dict tool call tương ứng với index i.
    return content_buf, [tool_calls[i] for i in sorted(tool_calls)]


# ---------------------------------------------------------------------------
# HÀM chat — VÒNG LẶP REPL CHÍNH
# ---------------------------------------------------------------------------
# REPL = Read-Eval-Print Loop: đọc input → xử lý → in kết quả → lặp lại.
# Giống terminal Python interactive mode (`python` không có file), nhưng
# ở đây là vòng lặp chat với agent.
#
# `workspace: Path` — thư mục làm việc (Path object).
# `max_tool_turns: int = 15` — giới hạn số vòng tool call/turn. Mặc định 15.
def chat(workspace: Path, max_tool_turns: int = 15) -> None:
    """Vòng lặp REPL chính."""
    # Client + model lấy từ src/agent.py — MỘT nguồn cấu hình (models.json,
    # fallback .env) cho cả solve.py lẫn chat.py. get_client() còn hardened
    # sẵn (timeout=120s/request, max_retries=1) — bản OpenAI(...) tự dựng
    # trước đây đọc VLLM_* env trực tiếp, KHÔNG timeout → 1 call vLLM treo
    # có thể đóng băng REPL ~10 phút (SDK default ~600s).
    client = get_client()
    model = get_model()
    # workspace giờ là param tường minh — không còn global set_workspace().
    # .resolve() đã làm ở main() trước khi truyền vào; ta đẩy thẳng nó vào
    # execute_tool() mỗi lần gọi tool để _safe_path() kẹp file ops trong đây.

    # `messages: list[dict] = [...]` — khởi tạo list chứa 1 dict (system message).
    # Đây là "bộ nhớ" của cuộc trò chuyện — mỗi message là 1 dict với keys:
    #   "role": "system" | "user" | "assistant" | "tool"
    #   "content": chuỗi văn bản
    # List này sẽ được APPEND thêm message sau mỗi lượt user + assistant.
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Thinking mode (sticky). Default OFF — fast cho task đơn giản (greeting,
    # câu hỏi ngắn). User gõ /think để bật trước khi giao task phức tạp.
    # `sticky` nghĩa là cài đặt này GHI NHỚ qua các lượt — không reset sau mỗi câu.
    thinking_enabled = False

    # Banner — giống style Claude Code / Codex.
    # `'═' * 60` — nhân chuỗi: lặp lại ký tự '═' 60 lần → chuỗi 60 ký tự '═══...═══'.
    # Trong Python, `*` trên chuỗi nghĩa là lặp (không phải nhân số).
    print(f"{Color.HEADER}{'═' * 60}{Color.RESET}")
    print(f"{Color.HEADER}  coding-agent (REPL chat){Color.RESET}")
    print(f"  model     : {model}")
    # endpoint lấy từ cùng ModelConfig mà get_client() dùng — banner không
    # thể nói dối về nơi request thật sự được gửi đến.
    print(f"  endpoint  : {cfg.base_url}")
    print(f"  workspace : {workspace}")
    # Render danh sách lệnh từ COMMANDS (chỉ tên ĐẦU TIÊN của mỗi nhóm alias
    # cho gọn 1 dòng — /help mới liệt kê đầy đủ alias + mô tả).
    # `names.split()[0]` — tách "/exit /quit /q" theo khoảng trắng, lấy phần tử đầu.
    print(f"  commands  : {'  '.join(names.split()[0] for names, _ in COMMANDS)}")
    print(f"  mode      : fast (thinking off) — gõ /think để bật deep thinking")
    print(f"  compact   : auto-trigger ở ~{COMPACT_THRESHOLD_TOKENS} tokens (giữ {KEEP_RECENT_MESSAGES} msg gần nhất)")
    print(f"{Color.HEADER}{'═' * 60}{Color.RESET}")

    # ---------------------------------------------------------------------------
    # VÒNG LẶP REPL BÊN NGOÀI (OUTER LOOP)
    # ---------------------------------------------------------------------------
    # `while True:` — vòng lặp vô hạn (infinite loop).
    # `True` luôn là True, nên vòng chạy mãi cho đến khi gặp `break` hoặc
    # `sys.exit()` hoặc exception không được catch.
    while True:
        # --- Lấy input từ user ---
        # `try: ... except ...: ...` — CẤU TRÚC XỬ LÝ NGOẠI LỆ (exception handling).
        # `try` block: chạy code có thể sinh lỗi.
        # `except (ErrorType1, ErrorType2):` — bắt lỗi kiểu ErrorType1 hoặc ErrorType2.
        # Nếu lỗi xảy ra trong `try`, nhảy ngay vào `except`.
        # Nếu không có lỗi, `except` block bị bỏ qua.
        try:
            # `input(prompt)` — hàm built-in, in `prompt` ra rồi CHỜ user gõ Enter.
            # Trả về chuỗi user đã gõ (không gồm ký tự Enter ở cuối).
            # Ví dụ: user gõ "Fix my bug" → input() trả về "Fix my bug".
            # `.strip()` — xóa khoảng trắng đầu/cuối (user vô tình bấm Space trước/sau).
            user_input = input(f"\n{Color.FINISH}you> {Color.RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            # `EOFError` — xảy ra khi stdin đóng (ví dụ: pipe bị đứt, file input kết thúc).
            # `KeyboardInterrupt` — xảy ra khi user bấm Ctrl+C.
            # Cả hai đều là tín hiệu "user muốn thoát" → thoát gracefully (không crash).
            print(f"\n{Color.FINISH}Bye.{Color.RESET}")
            return  # `return` trong hàm không có giá trị trả về → thoát hàm chat().

        # `if not user_input:` — nếu user_input là chuỗi rỗng "" (sau strip()).
        # Xảy ra khi user bấm Enter mà không gõ gì → bỏ qua, lấy input tiếp.
        if not user_input:
            continue  # `continue` — bỏ qua phần còn lại của vòng while, lặp từ đầu.

        # --- SLASH COMMANDS (một dispatcher inline duy nhất) ---
        # Tất cả lệnh xử lý NGAY TẠI ĐÂY thay vì hàm helper riêng: chúng cần
        # state sống trong chat() (messages, client, model, thinking_enabled)
        # — trước đây tách đôi (handle_slash + inline) khiến danh sách lệnh
        # bị chép tay nhiều chỗ và helper gọi sys.exit ngầm. Mọi lệnh khai
        # báo trong tuple COMMANDS (đầu file); /help và banner render từ đó.
        # `low = user_input.lower()` — lowercase để so sánh không phân biệt hoa/thường.
        # Ví dụ: "/THINK" → "/think"
        low = user_input.lower()

        # `/exit` — thoát REPL. `return` thoát hàm chat() → main() trả 0 →
        # sys.exit(0) ở entry point. Sạch hơn sys.exit chôn trong helper:
        # luồng thoát đọc được từ trên xuống.
        if low in ("/exit", "/quit", "/q"):
            print(f"{Color.FINISH}Bye.{Color.RESET}")
            return

        # `/clear` — xoá history nhưng giữ system prompt (conversation nào
        # cũng cần system message đầu tiên để model biết mình là ai).
        # `messages.clear()` xóa TẠI CHỖ (in-place) — khác `messages = []`
        # (tạo list mới, các ref cũ vẫn thấy list cũ).
        if low in ("/clear", "/reset"):
            messages.clear()
            messages.append({"role": "system", "content": SYSTEM_PROMPT})
            print(f"{Color.FINISH}Conversation cleared.{Color.RESET}")
            continue

        # `/help` — render từ COMMANDS nên KHÔNG thể thiếu lệnh nào (trước
        # đây /help hand-list và đã quên /compact, /tokens).
        # `{names:<18}` — format căn trái trong 18 ký tự để cột mô tả thẳng hàng.
        if low in ("/help", "/?"):
            for names, desc in COMMANDS:
                print(f"{Color.FINISH}  {names:<18} {desc}{Color.RESET}")
            continue

        # `/think` — BẬT thinking mode (sticky: giữ nguyên qua các lượt sau).
        # `thinking_enabled = True` — gán True vào biến.
        # `continue` — quay lại đầu vòng while, bỏ qua phần gọi LLM.
        if low in ("/think", "/deep"):
            thinking_enabled = True
            print(f"{Color.FINISH}Thinking mode: ON (deep — model thinks before each turn){Color.RESET}")
            continue

        # `/nothink` — TẮT thinking mode.
        if low in ("/nothink", "/fast"):
            thinking_enabled = False
            print(f"{Color.FINISH}Thinking mode: OFF (fast — model responds directly){Color.RESET}")
            continue

        # `/mode` — xem thinking mode hiện tại.
        if low == "/mode":
            # `m = "ON (deep)" if thinking_enabled else "OFF (fast)"` —
            # CONDITIONAL EXPRESSION (ternary operator) — cú pháp rút gọn của if/else:
            # `giá_trị_nếu_true if điều_kiện else giá_trị_nếu_false`
            # Nếu thinking_enabled là True → m = "ON (deep)"
            # Nếu thinking_enabled là False → m = "OFF (fast)"
            m = "ON (deep)" if thinking_enabled else "OFF (fast)"
            print(f"{Color.FINISH}Thinking mode: {m}{Color.RESET}")
            continue

        # --- Compaction commands (inline vì cần client + model từ closure) ---
        # `closure` = biến từ scope bên ngoài được dùng trong hàm/block bên trong.
        # Ở đây `client` và `model` được định nghĩa ở đầu hàm `chat()` nhưng
        # dùng được trong đoạn code này vì cùng phạm vi hàm.

        # /tokens: show estimate without doing anything. Useful trước khi
        # quyết định có /compact manually hay không.
        if low in ("/tokens", "/tok"):
            tok = estimate_tokens(messages)
            # `100 * tok / cfg.context_window` — tính phần trăm context đã dùng.
            # Mẫu số từ ModelConfig (models.json) — không còn hằng MAX_MODEL_LEN
            # riêng của file này có thể lệch với config thật.
            # `/` là chia thông thường (trả float). Nhân 100 để ra phần trăm.
            pct = 100 * tok / cfg.context_window
            # Màu cảnh báo theo mức độ gần threshold: đỏ = đã vượt (auto-compact
            # sẽ chạy ở turn sau), vàng = đang tiến sát, xanh = còn thoải mái.
            warn_level = COMPACT_THRESHOLD_TOKENS - 4000  # ~20K, ngưỡng "đang sát"
            # NESTED TERNARY: `a if cond1 else (b if cond2 else c)` — kiểm tra nhiều điều kiện.
            color = Color.WARN if tok > COMPACT_THRESHOLD_TOKENS else (Color.RESULT if tok > warn_level else Color.TOOL)
            # `cfg.context_window // 1000` — chia nguyên: 32768 // 1000 = 32 (bỏ phần lẻ).
            # `:.0f` trong f-string — format float với 0 chữ số thập phân.
            print(f"{color}Token estimate: ~{tok} / {cfg.context_window // 1000}K ({pct:.0f}%)  "
                  f"[threshold: {COMPACT_THRESHOLD_TOKENS}]{Color.RESET}")
            continue

        # /compact: trigger summarization NGAY, kể cả khi chưa đụng threshold.
        # Useful khi user biết tasks sắp tới sẽ tốn nhiều tokens và muốn pre-free
        # context budget.
        if low == "/compact":
            print(f"{Color.FINISH}Compacting conversation history...{Color.RESET}")
            try:
                # in-place replace: messages[:] = new_list.
                # `messages[:] = new_msgs` — SLICE ASSIGNMENT đặc biệt.
                # `messages[:]` → toàn bộ list (từ đầu đến cuối).
                # Gán vào `messages[:]` thay thế NỘI DUNG của list tại chỗ (in-place).
                # TẠI SAO KHÔNG DÙNG `messages = new_msgs`?
                #   `messages = new_msgs` tạo biến cục bộ mới trỏ đến list mới.
                #   Biến `messages` ở hàm chat() trỏ đến địa chỉ bộ nhớ CŨ.
                #   Sau khi hàm kết thúc, biến cục bộ biến mất, list gốc không đổi.
                # `messages[:] = new_msgs` thay đổi NỘI DUNG tại địa chỉ bộ nhớ cũ
                #   → mọi nơi đang ref đến `messages` đều thấy thay đổi.
                new_msgs, status = compact_messages(messages, client, model)
                messages[:] = new_msgs
                print(f"{Color.FINISH}{status}{Color.RESET}")
            except Exception as e:
                # `except Exception as e:` — bắt MỌI loại exception (Exception là base class).
                # `as e` — gán exception object vào biến `e` để có thể in thông báo lỗi.
                # `str(e)` — chuyển exception thành chuỗi mô tả lỗi.
                # Compaction là best-effort — nếu LLM call fail, KHÔNG được crash
                # REPL. Báo lỗi, để user tự xử lý (e.g. /clear).
                print(f"{Color.WARN}Compaction failed: {e}{Color.RESET}")
            continue

        # Catch-all: bắt đầu bằng "/" mà không khớp lệnh nào ở trên → báo lỗi
        # thay vì gửi nhầm cho LLM (user gõ sai lệnh không nên tốn 1 LLM call).
        # PHẢI đứng SAU mọi check lệnh cụ thể — nếu đặt trước, nó nuốt hết.
        if low.startswith("/"):
            print(f"{Color.WARN}Unknown command: {user_input}. Try /help.{Color.RESET}")
            continue

        # --- Append user message vào history (memory) ---
        # `messages.append({"role": "user", "content": user_input})` — thêm dict vào CUỐI list.
        # `.append()` vs `.extend()` — SỰ KHÁC BIỆT QUAN TRỌNG:
        #   `.append(x)` → thêm x như MỘT phần tử vào cuối.
        #     [1,2].append(3) → [1, 2, 3]        (list có 3 phần tử)
        #     [1,2].append([3,4]) → [1, 2, [3,4]] (list có 3 phần tử, phần tử cuối là list)
        #   `.extend(iterable)` → thêm TỪNG phần tử của iterable vào cuối.
        #     [1,2].extend([3,4]) → [1, 2, 3, 4]  (list có 4 phần tử, không lồng)
        # Ở đây: append 1 dict (1 message) → ĐÚNG.
        # Nếu dùng extend với dict: extend sẽ lặp qua KEYS của dict → SAI.
        messages.append({"role": "user", "content": user_input})

        # --- AUTO-COMPACT CHECK (before inner loop starts) ---
        # Kiểm tra token estimate TRƯỚC mỗi inner loop. Nếu vượt threshold,
        # tự động summarize trước khi gửi request → tránh "context length
        # exceeded" 400 từ vLLM.
        #
        # Trigger ở 75% context window (32K → ~24.5K) chứ không sát 100% —
        # để chừa buffer cho:
        #   - response tokens (cfg.max_tokens, ~2K)
        #   - inaccuracy của estimate_tokens (±20-30%)
        #   - tool results spike trong inner loop trước khi compact lần sau
        #
        # Compaction tốn 1 extra LLM call (~3-5s), nhưng rẻ hơn nhiều so với
        # context overflow crash buộc user gõ /clear (mất toàn bộ history).
        tok_estimate = estimate_tokens(messages)
        if tok_estimate > COMPACT_THRESHOLD_TOKENS:
            print(f"{Color.RESULT}[auto-compact] ~{tok_estimate} tokens > threshold "
                  f"{COMPACT_THRESHOLD_TOKENS}, summarizing history...{Color.RESET}")
            try:
                new_msgs, status = compact_messages(messages, client, model)
                messages[:] = new_msgs
                print(f"{Color.RESULT}[auto-compact] {status}{Color.RESET}")
            except Exception as e:
                # Best-effort: nếu compact fail, vẫn cứ thử gửi request original
                # (có thể vẫn dưới limit nếu estimate sai cao). Worse case
                # vLLM trả 400 và except block bên dưới handle.
                print(f"{Color.WARN}[auto-compact] failed: {e} — proceeding without compaction{Color.RESET}")

        # ---------------------------------------------------------------------------
        # VÒNG LẶP BÊN TRONG (INNER LOOP) — AGENT LOOP
        # ---------------------------------------------------------------------------
        # Sau khi user nói 1 câu, model có thể cần GỌI TOOL NHIỀU LẦN trước khi
        # đưa ra câu trả lời cuối. Mỗi vòng inner = 1 round-trip stream.
        # Vòng dừng khi model không gọi tool nào nữa (= câu trả lời cuối cho user).
        #
        # `for _turn in range(1, max_tool_turns + 1):` — lặp từ 1 đến max_tool_turns (gồm cả hai đầu).
        # `range(1, 16)` → tạo dãy số 1, 2, 3, ..., 15 (không gồm 16).
        # `range(start, stop)` — hàm built-in tạo dãy số nguyên.
        # `_turn` — biến với prefix `_` là quy ước Python báo "biến này không dùng trong body".
        # Ta chỉ cần range() để giới hạn iterations, không cần giá trị index thật.
        for _turn in range(1, max_tool_turns + 1):
            try:
                # `content_buf, tool_calls = stream_one_turn(...)` — TUPLE UNPACKING.
                # Hàm trả về tuple (chuỗi, list), ta "unpack" thành 2 biến riêng.
                # Cú pháp: `a, b = hàm_trả_tuple()` tương đương:
                #   temp = hàm_trả_tuple()
                #   a = temp[0]
                #   b = temp[1]
                content_buf, tool_calls = stream_one_turn(client, model, messages, thinking_enabled)
            except KeyboardInterrupt:
                # Ctrl+C giữa stream → cho user ngắt agent mà không thoát REPL.
                print(f"\n{Color.WARN}[interrupted]{Color.RESET}")
                # Append assistant placeholder để conversation không lệch.
                # Nếu không append, history sẽ kết thúc bằng role=user → model bị
                # confuse ở turn sau (nghĩ user chưa nhận được response).
                messages.append({"role": "assistant", "content": "[interrupted by user]"})
                break  # `break` — thoát khỏi vòng for NGAY LẬP TỨC (không chạy tiếp).
            except Exception as e:
                print(f"\n{Color.WARN}API error: {e}{Color.RESET}")
                # Rollback TOÀN BỘ messages thuộc turn này — nếu lỗi xảy ra GIỮA inner
                # loop (sau khi đã append assistant + role=tool messages), chỉ pop user
                # msg sẽ để lại orphan tool messages → API reject ở turn sau.
                # Cách an toàn: pop từ cuối cho tới khi gặp user message gần nhất, rồi
                # pop luôn nó để user gõ lại từ đầu.
                # `while messages and messages[-1].get("role") != "user":`
                #   `messages` — list không rỗng mới có giá trị truthy.
                #   `messages[-1]` — phần tử CUỐI CÙNG của list (index -1 = từ cuối về đầu).
                #     Python cho phép index âm: -1 = cuối, -2 = gần cuối, ...
                #   `messages.pop()` — xóa và trả về phần tử CUỐI LIST.
                while messages and messages[-1].get("role") != "user":
                    messages.pop()
                if messages and messages[-1].get("role") == "user":
                    messages.pop()
                break

            # --- Build assistant message để append vào history ---
            # Giữ NGUYÊN tool_calls field cho turn sau (giống run_agent — xem
            # comment về model_dump trong agent.py). Args để RAW kể cả khi JSON
            # hỏng: execute_turn bên dưới sẽ validate và sanitize bản trong
            # history thành "{}" nếu không parse được.
            asst_msg: dict = {"role": "assistant", "content": content_buf or None}
            # `content_buf or None` — API yêu cầu content là None (không phải "")
            # khi message chỉ có tool_calls.
            if tool_calls:
                asst_msg["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": tc["arguments"]},
                    }
                    for tc in tool_calls
                ]
            messages.append(asst_msg)

            # --- Model không gọi tool → câu trả lời cuối, thoát inner loop ---
            if not tool_calls:
                break

            # --- Thực thi lượt tool: execute_turn (src/agent.py) ---
            # CÙNG một cơ chế với run_agent: validate/repair JSON args → chạy
            # execute_tool → append đủ role:"tool" mỗi call (bất biến ghép cặp,
            # kể cả khi Ctrl+C giữa chừng). Trước đây khối này được REPL tự cài
            # lại và đã drift khỏi run_agent — giờ "một lượt agent diễn ra thế
            # nào" chỉ còn MỘT câu trả lời. REPL chỉ truyền style in riêng (▶/↳).
            try:
                finish_called = execute_turn(
                    tool_calls, messages, workspace,
                    on_call=lambda name, args: print(
                        f"{Color.TOOL}▶ {name}("
                        f"{args if len(args) <= 200 else args[:200] + '...[truncated]'}"
                        f"){Color.RESET}"),
                    on_result=lambda result: print(
                        f"{Color.RESULT}  ↳ "
                        f"{result if len(result) <= 500 else result[:500] + '...[truncated]'}"
                        f"{Color.RESET}"),
                )
            except KeyboardInterrupt:
                # execute_turn đã điền placeholder đủ cặp cho mọi tool_call rồi
                # mới re-raise — history hợp lệ. Chỉ dừng turn này, REPL sống tiếp.
                print(f"\n{Color.WARN}[interrupted]{Color.RESET}")
                break

            # --- Model gọi finish() = tuyên bố hoàn thành → dừng inner loop ---
            # Giống run_agent phân loại "finished". Trước đây REPL LỜ finish:
            # model gọi xong vẫn bị stream thêm turn nữa (lãng phí + khó hiểu).
            if finish_called:
                print(f"{Color.FINISH}✓ finish() — agent tuyên bố hoàn thành.{Color.RESET}")
                break

            # Loop sang turn tiếp theo — model sẽ "thấy" tool results vừa append.
            # Python tiếp tục lên đầu `for _turn in range(...)` và lặp tiếp.

        else:
            # `else` của vòng `for` — Python có tính năng độc đáo: `for...else`.
            # Khối `else` của `for` chạy khi vòng lặp KẾT THÚC TỰ NHIÊN (không bị `break`).
            # Nếu có `break` → `else` KHÔNG chạy.
            # Ở đây: chạy hết max_tool_turns mà không break → model vẫn gọi tool → cảnh báo.
            print(f"{Color.WARN}Hit max_tool_turns={max_tool_turns}. Stopping this turn.{Color.RESET}")


# ---------------------------------------------------------------------------
# HÀM main — ĐIỂM VÀO CHƯƠNG TRÌNH
# ---------------------------------------------------------------------------
# `def main() -> int:` — trả về int (exit code: 0 = thành công, khác 0 = lỗi).
# Tách main() ra khỏi logic thật (chat()) để dễ test và dễ import từ nơi khác.
def main() -> int:
    # `argparse.ArgumentParser(description=...)` — tạo object parser.
    # `description` là mô tả hiện trong `--help`.
    parser = argparse.ArgumentParser(
        description="Interactive REPL chat with the coding agent (Claude-Code-style).",
    )
    # `parser.add_argument("--workspace", ...)` — định nghĩa tham số `--workspace`.
    # `--workspace` là OPTIONAL argument (bắt đầu bằng --).
    # `default=...` — giá trị mặc định nếu user không truyền.
    # `str(Path(__file__).resolve().parent.parent / "demo_repo")`:
    #   - `Path(__file__).resolve().parent.parent` → project root (giải thích ở trên).
    #   - `/ "demo_repo"` — toán tử `/` trên Path object: nối path. Không phải chia số!
    #     Path("/home/user/project") / "demo_repo" → Path("/home/user/project/demo_repo")
    #   - `str(...)` → chuyển Path thành chuỗi cho argparse.
    # `help=...` — mô tả hiện khi user gõ `--help`.
    parser.add_argument(
        "--workspace",
        default=str(Path(__file__).resolve().parent.parent / "demo_repo"),
        help="Sandbox directory the tools may read/write/exec inside (default: demo_repo).",
    )
    # `type=int` — argparse tự động chuyển chuỗi argument thành int.
    # Nếu user truyền `--max-tool-turns abc` (không phải số), argparse báo lỗi.
    parser.add_argument(
        "--max-tool-turns", type=int, default=15,
        help="Max tool-call iterations between each user message (default: 15).",
    )
    # `args = parser.parse_args()` — phân tích sys.argv (list các argument dòng lệnh).
    # Trả về object Namespace với các thuộc tính tương ứng tên argument.
    # Ví dụ: `python chat.py --workspace /tmp` → args.workspace = "/tmp"
    # Lưu ý: `--max-tool-turns` (có dấu gạch ngang) → args.max_tool_turns (dấu gạch dưới).
    args = parser.parse_args()

    # Silence stdlib logging trong tools.py để không xen ngang stream output.
    # Chat REPL tự quản lý mọi print rồi.
    # `logging.basicConfig(level=logging.WARNING)` — chỉ in log từ WARNING trở lên.
    # DEBUG và INFO bị tắt → code trong tools.py dùng log.debug/info sẽ im lặng.
    logging.basicConfig(level=logging.WARNING)

    # `Path(args.workspace).resolve()` — chuyển chuỗi workspace thành Path tuyệt đối.
    # Ví dụ: "demo_repo" → "/home/tle/code/coding-agent/demo_repo" (absolute path).
    # Truyền Path (không phải chuỗi) vào chat() để type-safe và có .parent, .exists()...
    chat(Path(args.workspace).resolve(), args.max_tool_turns)
    # `return 0` — trả về 0 báo thành công (hàm main() xong).
    return 0


# `if __name__ == "__main__":` — chỉ chạy main() khi file được gọi trực tiếp
# (`python cli/chat.py`), không chạy khi bị import. Xem giải thích chi tiết
# về pattern này trong eval/run.py.
if __name__ == "__main__":
    sys.exit(main())
