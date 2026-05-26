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
     riêng. Mình in màu xám ngay khi nó chảy về.
  3. TOOL CALL STEP-BY-STEP: hiện ngay tool name + args (green) và result (yellow)
     trước khi model viết câu trả lời tiếp.

LỆNH SLASH
  /exit, /quit, /q     thoát
  /clear, /reset       xoá history (giữ system prompt)
  /think               bật chế độ deep thinking (model thinks before each turn)
  /nothink             tắt thinking (fast mode — mặc định)
  /mode                xem mode hiện tại
  /help                hiện help

CÁCH CHẠY
  cd ~/code/coding-agent && source .venv/bin/activate
  python cli/chat.py                              # workspace = demo_repo
  python cli/chat.py --workspace /tmp/playground  # workspace khác
"""

# ---------------------------------------------------------------------------
# `from __future__ import annotations`
# ---------------------------------------------------------------------------
# `from __future__ import annotations` là câu lệnh ĐẶC BIỆT của Python.
# Từ khóa `from` nghĩa là "lấy từ module nào đó".
# `__future__` là module đặc biệt để bật các tính năng Python MỚI HƠN ngay
# trong phiên bản Python hiện tại.
# `import annotations` bật tính năng: type hints (như `list[dict]`) sẽ KHÔNG
# được Python tính toán ngay khi đọc code — chỉ là chuỗi ký tự. Nhờ đó có
# thể viết `list[dict]` trên Python 3.8 mà không bị lỗi (Python 3.9+ mới
# hỗ trợ `list[dict]` natively, nhưng dòng này giúp tương thích cả 3.8).
# QUY TẮC: dòng này PHẢI đứng đầu tiên, trước mọi import khác.
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

# `json` — thư viện chuẩn để làm việc với định dạng JSON.
# JSON (JavaScript Object Notation) là cách biểu diễn dữ liệu dạng văn bản,
# ví dụ: {"name": "Alice", "age": 30}
# json.dumps() → chuyển dict Python thành chuỗi JSON (serialization).
# json.loads() → chuyển chuỗi JSON thành dict Python (deserialization).
import json

# `logging` — thư viện chuẩn để in thông báo debug/info/warning ra console
# hoặc file. Khác print() ở chỗ: có level (DEBUG/INFO/WARNING/ERROR) và
# có thể bật/tắt theo level.
import logging

# `os` — thư viện chuẩn để tương tác với hệ điều hành.
# os.environ["KEY"] → đọc biến môi trường (environment variable).
# Biến môi trường là các cặp KEY=VALUE mà OS cung cấp cho chương trình,
# ví dụ: VLLM_BASE_URL=http://localhost:8000
import os

# `sys` — thư viện chuẩn để tương tác với Python runtime.
# sys.path → danh sách thư mục Python tìm kiếm khi import.
# sys.exit(0) → thoát chương trình với mã 0 (0 = thành công).
# sys.stdin → luồng đầu vào chuẩn (keyboard).
import sys

# `Path` từ thư viện `pathlib` — class đại diện cho đường dẫn file/thư mục.
# Dùng Path thay vì chuỗi thuần giúp code portable (Windows dùng \, Linux/Mac
# dùng /) và có nhiều phương thức tiện lợi như .parent, .resolve(), .exists().
from pathlib import Path

# ---------------------------------------------------------------------------
# SỬA sys.path ĐỂ IMPORT ĐƯỢC src/
# ---------------------------------------------------------------------------
# VẤNỀ: Khi bạn gõ `python cli/chat.py`, Python tự động thêm thư mục `cli/`
# vào sys.path (danh sách nơi tìm kiếm module). Vì vậy nếu bạn viết
# `import agent`, Python tìm trong `cli/agent.py` — nhưng agent.py nằm ở
# `src/agent.py`, không phải trong `cli/`.
#
# GIẢI PHÁP: Thêm project root vào sys.path trước khi import src/.
#
# GIẢI THÍCH TỪNG PHẦN của `Path(__file__).resolve().parent.parent`:
#   - `__file__` (đọc là "dunder file") là biến đặc biệt Python tự đặt, chứa
#     đường dẫn đến file đang chạy. Ví dụ: `/home/tle/code/coding-agent/cli/chat.py`
#   - `.resolve()` là phương thức của Path, chuyển đường dẫn tương đối thành
#     tuyệt đối và giải quyết symlinks (shortcut). Kết quả: đường dẫn đầy đủ.
#   - `.parent` là thuộc tính của Path, trả về thư mục cha (parent directory).
#     Ví dụ: Path("/home/tle/code/coding-agent/cli/chat.py").parent
#              → Path("/home/tle/code/coding-agent/cli")
#   - `.parent` lần 2: thư mục cha của thư mục cha.
#     Path("/home/tle/code/coding-agent/cli").parent
#              → Path("/home/tle/code/coding-agent")   ← đây là project root!
#
# `str(...)` — chuyển Path object thành chuỗi vì sys.path chứa chuỗi, không
# chứa Path object.
#
# `sys.path.insert(0, ...)` — chèn vào VỊ TRÍ 0 (đầu tiên) của danh sách.
# Tại sao không dùng `.append()` (thêm vào cuối)? Vì Python tìm kiếm theo
# thứ tự từ đầu đến cuối sys.path. Đặt ở đầu đảm bảo project root được tìm
# TRƯỚC CÁC THƯ VIỆN HỆ THỐNG — tránh bị che khuất bởi package cùng tên.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# `from dotenv import load_dotenv` — import hàm load_dotenv từ thư viện dotenv.
# `dotenv` đọc file `.env` (chứa KEY=VALUE) và nạp vào os.environ.
# Nhờ đó code đọc os.environ["VLLM_BASE_URL"] mà không cần bạn export thủ công.
from dotenv import load_dotenv

# `from openai import OpenAI` — import class OpenAI để tạo API client.
# Class = bản thiết kế để tạo object. OpenAI client biết cách gửi HTTP request
# đến server (dù server là OpenAI thật hay vLLM local giả lập API tương thích).
from openai import OpenAI

# Tái dùng tools + prompt y nguyên — không duplicate.
# `TOOL_SCHEMAS` là list mô tả các tool (hàm) mà model có thể gọi.
# `execute_tool` là hàm thực thi tool khi model yêu cầu.
from src.tools import TOOL_SCHEMAS, execute_tool

# `SYSTEM_PROMPT` là chuỗi văn bản định nghĩa "nhân cách" và quy tắc của agent.
# Luôn được đặt là message đầu tiên với role="system".
from src.prompts import SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# ANSI colors — em tô màu để phân biệt: bạn / thinking / assistant / tool / result.
# ---------------------------------------------------------------------------
# ANSI escape codes là các chuỗi ký tự đặc biệt mà terminal (console) hiểu
# và hiển thị thành màu sắc. Định dạng: "\033[<code>m" để bật, "\033[0m" để tắt.
# `\033` là ký tự ESC (Escape) trong mã ASCII. `[97m` là code màu.
# Cách dùng: print(f"{BLUE}Hello{RESET}") → in "Hello" màu xanh, sau đó reset.
WHITE = "\033[97m"       # thinking (trắng sáng, dễ nhìn trên nền tối)
BLUE = "\033[1;34m"      # banner + turn header
                         # `1;` = bold, `34` = màu xanh dương
GREEN = "\033[1;32m"     # tool call (đang gọi tool)
YELLOW = "\033[33m"      # tool result
MAGENTA = "\033[1;35m"   # assistant content (visible reply)
CYAN = "\033[1;36m"      # user prompt + system info
RED = "\033[1;31m"       # error / warn
RESET = "\033[0m"        # reset về màu mặc định của terminal


# ---------------------------------------------------------------------------
# Auto-compaction — giữ conversation history dưới context limit
# ---------------------------------------------------------------------------
#
# PROBLEM: Qwen3-14B `max_model_len=32768`. Mỗi turn append assistant + tool
# messages — qua 20-30 turns, history dễ vượt 32K → vLLM trả 400 "context
# length exceeded" và REPL crash. Claude Code giải quyết bằng auto-summarize:
# khi history quá dài, gom các turn cũ thành 1 summary và giữ recent turns
# nguyên xi. Tool ở đây implement đúng pattern đó.
#
# THRESHOLDS (tunable constants):
#   COMPACT_THRESHOLD_TOKENS = 24000 → trigger ở ~75% context (chừa headroom)
#   KEEP_RECENT_MESSAGES     = 10    → giữ 10 message gần nhất verbatim
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# HẰNG SỐ (CONSTANTS)
# ---------------------------------------------------------------------------
# Hằng số là biến mà giá trị KHÔNG thay đổi trong suốt chương trình.
# Quy ước Python: viết HOA toàn bộ tên (ví dụ COMPACT_THRESHOLD_TOKENS).
# Đây chỉ là quy ước — Python không ngăn bạn thay đổi, nhưng viết hoa
# báo hiệu "đừng sửa cái này trong lúc chạy".

# Trigger point: khi estimated tokens vượt threshold, auto-compact TRƯỚC
# stream call tiếp theo. 24K = ~75% của max_model_len 32K, đủ headroom cho
# next response (~2K tokens) + tool results.
# `=` là toán tử gán: đặt tên bên trái bằng giá trị bên phải.
# `24000` là số nguyên (integer), không cần dấu ngoặc hay ký tự đặc biệt.
COMPACT_THRESHOLD_TOKENS = 24000

# max_model_len của Qwen3-14B trong vLLM. Dùng làm mẫu số khi hiển thị %
# context đã dùng (/tokens). Để hằng số riêng thay vì hardcode 32768 rải rác.
MAX_MODEL_LEN = 32768

# Số messages cuối giữ nguyên không summarize. 10 = đủ cho model nhớ context
# 5-6 turn gần nhất (user + assistant + tool, mix 2-3 messages/turn).
# Tăng → ít compaction lợi ích nhưng tốn tokens; giảm → mất context dễ.
KEEP_RECENT_MESSAGES = 10


# ---------------------------------------------------------------------------
# HÀM estimate_tokens
# ---------------------------------------------------------------------------
# `def` là từ khóa Python để ĐỊNH NGHĨA hàm (function).
# Cú pháp: def tên_hàm(tham_số_1, tham_số_2, ...) -> kiểu_trả_về:
# Dấu hai chấm `:` ở cuối dòng `def` báo bắt đầu KHỐI CODE của hàm.
# Khối code phải THỤT VÀO (indent) — Python dùng thụt đầu dòng để phân
# cấp code, không dùng { } như Java/C.
#
# `messages: list` — type hint: tham số `messages` phải là list.
# Type hints chỉ là "chú thích" cho lập trình viên, Python KHÔNG ép kiểu.
# `-> int` — hàm này TRẢ VỀ một số nguyên (int).
def estimate_tokens(messages: list) -> int:
    """Ước lượng số token của messages list. KHÔNG cần exact.

    HEURISTIC: tổng chars / 4. Tại sao 4?
      - Qwen3 tokenizer (BPE) trung bình ~3.5-4.5 chars/token cho English
      - Vietnamese hơi tốn hơn (~3 chars/token) vì có diacritics
      - Code (Python) thường ~3.5 chars/token
      - Lấy 4 làm middle ground, sai số ~20-30% nhưng OK cho trigger decision
        (chúng ta chỉ cần biết "có gần limit chưa?", không cần exact count)

    Tại sao không dùng tiktoken/transformers tokenizer thật?
      - tiktoken là OpenAI tokenizer, không khớp Qwen3
      - HuggingFace tokenizer cần load weights (~50MB), startup cost
      - Khác biệt 20% không impact correctness — threshold có buffer rồi

    COUNTED:
      - message['content'] (str hoặc None)
      - message['tool_call_id'] (cho role=tool messages)
      - tool_calls[i].function.name + arguments (cho role=assistant)
    """
    # `total = 0` — khởi tạo biến `total` với giá trị 0.
    # Biến này sẽ tích lũy tổng số ký tự của tất cả messages.
    total = 0

    # `for m in messages:` — VÒNG LẶP FOR.
    # `for` là từ khóa, `m` là biến tạm, `in` là từ khóa, `messages` là list.
    # Mỗi lần lặp: `m` nhận giá trị tiếp theo trong danh sách `messages`.
    # Ví dụ: messages = [{"role": "user"}, {"role": "assistant"}]
    #   Lần 1: m = {"role": "user"}
    #   Lần 2: m = {"role": "assistant"}
    for m in messages:
        # content có thể None khi assistant message chỉ chứa tool_calls.
        # `m.get("content")` — phương thức `.get()` của dict.
        # Dict là kiểu dữ liệu ánh xạ key → value, ví dụ: {"role": "user", "content": "Hi"}
        # `.get("content")` trả về giá trị tương ứng với key "content", hoặc
        # `None` nếu key không tồn tại (an toàn hơn m["content"] vì không crash
        # khi key vắng mặt).
        # `or ""` — toán tử `or` trong Python: nếu vế trái là "falsy" (None,
        # False, 0, [], ""), trả về vế phải. Vậy: None or "" → "".
        # Mục đích: đảm bảo `content` luôn là chuỗi, không bao giờ là None,
        # để `len(content)` không crash.
        content = m.get("content") or ""

        # `len(content)` — hàm built-in `len()` trả về độ dài (số ký tự) của chuỗi.
        # `total += len(content)` viết tắt của `total = total + len(content)`.
        # `+=` là toán tử gán kết hợp (augmented assignment).
        total += len(content)

        # role=tool messages có tool_call_id (~10 chars/UUID-like) — nhỏ
        # nhưng cộng dồn 30 turns có thể đáng kể.
        # `if m.get("tool_call_id"):` — kiểm tra xem key "tool_call_id" có tồn
        # tại và có giá trị "truthy" không. Chuỗi rỗng "" và None đều là falsy.
        if m.get("tool_call_id"):
            total += len(m["tool_call_id"])
            # `m["tool_call_id"]` — truy cập dict bằng key trực tiếp (khác .get(),
            # cách này crash nếu key không có — nhưng ở đây ta đã kiểm tra ở `if`
            # rồi nên an toàn).

        # role=assistant với tool_calls — đếm function name + arguments JSON.
        # Đây thường là phần lớn nhất của 1 turn (write_file content có thể
        # vài KB).
        # `m.get("tool_calls") or []` — nếu không có key "tool_calls" hoặc giá
        # trị là None/[], trả về list rỗng [] để vòng for bên dưới không crash.
        for tc in m.get("tool_calls") or []:
            # `tc.get("function", {})` — lấy dict "function", mặc định là dict
            # rỗng `{}` nếu không có key "function". `{}` là dict rỗng trong Python.
            fn = tc.get("function", {})
            # `fn.get("name", "")` — lấy tên hàm, mặc định chuỗi rỗng.
            # `fn.get("arguments", "")` — lấy chuỗi JSON arguments, mặc định "".
            # `+` giữa hai len() — cộng hai số nguyên.
            total += len(fn.get("name", "")) + len(fn.get("arguments", ""))

    # `//` là phép chia lấy PHẦN NGUYÊN (integer division / floor division).
    # Ví dụ: 10 // 4 = 2 (không phải 2.5).
    # Khác `/` (chia thông thường trả float): 10 / 4 = 2.5.
    # Dùng `//` để trả về int, vì caller so sánh với COMPACT_THRESHOLD_TOKENS
    # là int — Python không ép kiểu, so sánh int với float vẫn work nhưng `//`
    # làm rõ ý định "ta muốn số nguyên".
    # INTEGER DIVISION là khái niệm quan trọng: 4 chars ≈ 1 token (xấp xỉ),
    # nên tổng_chars // 4 ≈ số_token.
    return total // 4


# ---------------------------------------------------------------------------
# HÀM compact_messages
# ---------------------------------------------------------------------------
# `def compact_messages(messages, client, model, keep_recent=KEEP_RECENT_MESSAGES)`
# Hàm có 4 tham số:
#   - `messages: list` — danh sách message (kiểu list)
#   - `client: OpenAI` — object API client (kiểu OpenAI)
#   - `model: str` — tên model (kiểu str = chuỗi)
#   - `keep_recent: int = KEEP_RECENT_MESSAGES` — tham số có GIÁ TRỊ MẶC ĐỊNH.
#     Nếu caller không truyền `keep_recent`, Python tự dùng KEEP_RECENT_MESSAGES.
#
# `-> tuple[list, str]` — hàm trả về tuple gồm 2 phần tử: (list, str).
# `tuple` là kiểu dữ liệu bất biến (immutable) chứa nhiều giá trị theo thứ tự.
# Ví dụ: (["a", "b"], "ok") là tuple của (list, str).
def compact_messages(
    messages: list,
    client: OpenAI,
    model: str,
    keep_recent: int = KEEP_RECENT_MESSAGES,
) -> tuple[list, str]:
    """Summarize old messages thành 1 system msg, giữ recent N verbatim.

    INPUT: messages list (mutable, NOT modified in-place — return new list).
    RETURN: (new_messages, status_message_for_user).

    STRATEGY:
      Before:  [system, m1, m2, m3, ..., m25]   (vd 26 messages)
      After:   [system, summary_system, m16, ..., m25]  (12 messages)
                ↑       ↑               ↑
                kept    new (LLM-gen)   last 10 verbatim

    CRITICAL — SPLIT POINT MUST BE 'user' role:
      OpenAI API yêu cầu MỌI role=tool message phải có assistant.tool_calls
      ở phía trước với matching tool_call_id. Nếu compact cắt giữa pair
      (vd assistant.tool_calls -> tool_result), tool message thành orphan
      → API reject 400.

      Solution: walk FORWARD từ initial split point đến khi gặp user message.
      User messages luôn là turn boundaries clean (không có tool dependency).
      `recent` bắt đầu tại đúng 1 user message → tool message đầu tiên trong
      `recent` (nếu có) chắc chắn có assistant.tool_calls đi trước nó BÊN TRONG
      `recent` → không bao giờ orphan.

      Vì sao walk FORWARD (giảm số message giữ lại) chứ không BACKWARD?
      Forward chỉ làm `recent` ngắn hơn → an toàn với context budget. Backward
      sẽ kéo thêm message vào `recent`, có thể làm history phình to — đi ngược
      mục tiêu compact. Worst case forward không thấy user → bail (không compact).

    LLM CALL FOR SUMMARY:
      - thinking=OFF cho speed (summary là deterministic, không cần reason)
      - max_tokens=600 đủ cho ~400 words summary
      - Prompt yêu cầu preserve: tool calls, file paths, decisions, errors
        (đây là info quan trọng nhất cho model resume task)
    """
    # GUARD: nếu history quá ngắn, không có gì để compact. +1 để account
    # cho system message ở index 0 (luôn giữ).
    # `len(messages)` — hàm len() trả về số phần tử trong list.
    # `<=` là toán tử so sánh "nhỏ hơn hoặc bằng".
    # `if ... :` — câu lệnh điều kiện: thực hiện khối code bên dưới nếu điều
    # kiện đúng (True).
    # `return messages, "..."` — trả về tuple hai giá trị. Python cho phép viết
    # không cần dấu ngoặc: `return a, b` tương đương `return (a, b)`.
    if len(messages) <= keep_recent + 1:
        return messages, "no compaction needed (too few messages)"

    # STEP 1: Tìm split point — bắt đầu từ -keep_recent, walk forward đến
    # khi gặp user message (clean turn boundary).
    # `len(messages) - keep_recent` — tính vị trí cắt ban đầu.
    # Ví dụ: 26 messages, keep_recent=10 → split = 16 (giữ messages[16..25]).
    split = len(messages) - keep_recent

    # `while condition:` — VÒNG LẶP WHILE: lặp LIÊN TỤC miễn điều kiện còn đúng.
    # Khác for (lặp qua danh sách cố định), while lặp không biết trước số lần.
    # Điều kiện: `split < len(messages)` AND `messages[split].get("role") != "user"`
    # `and` — toán tử logic AND: cả hai phải đúng thì điều kiện mới đúng.
    # `!=` — toán tử "không bằng".
    # Vòng này tìm vị trí đầu tiên trong recent window mà role là "user".
    while split < len(messages) and messages[split].get("role") != "user":
        # `split += 1` — tăng split lên 1, tiến về phía sau trong danh sách.
        split += 1

    # Nếu walk hết list mà không thấy user (rare edge case — vd toàn tool
    # messages cuối), bail. Tốt hơn không compact còn hơn compact sai.
    # `>=` — toán tử "lớn hơn hoặc bằng".
    if split >= len(messages):
        return messages, "compaction skipped (no clean user boundary in recent window)"

    # STEP 2: Tách messages thành 3 phần.
    # `messages[0]` — indexing: lấy phần tử ở vị trí 0 (đầu tiên).
    # Python đánh số từ 0: phần tử đầu = index 0, thứ hai = index 1, v.v.
    system_msg = messages[0]                # giữ nguyên — định nghĩa agent persona

    # `messages[1:split]` — SLICING: lấy một đoạn của list.
    # Cú pháp: list[start:stop] → lấy từ index `start` đến `stop-1` (không gồm stop).
    # Ví dụ: [a, b, c, d, e][1:3] → [b, c]  (index 1 và 2, không gồm 3)
    # `messages[1:split]` → từ index 1 đến split-1 (bỏ system_msg ở index 0).
    to_summarize = messages[1:split]        # phần này sẽ bị compact thành 1 summary

    # `messages[split:]` — slicing không có stop: lấy từ split đến hết list.
    recent = messages[split:]               # giữ nguyên — model cần immediate context

    # Edge: nếu nothing to summarize (split=1), bail.
    # `not to_summarize` — `not` là toán tử logic NOT, đảo ngược True/False.
    # List rỗng `[]` là falsy, nên `not []` = True → điều kiện đúng khi list rỗng.
    if not to_summarize:
        return messages, "no compaction needed (nothing between system and recent)"

    # STEP 3: Render to_summarize thành plain text cho LLM đọc.
    # Format thân thiện với model — không cần re-serialize full JSON, chỉ
    # cần text representation của (role, content, tool calls).
    # `rendered = []` — tạo list rỗng để tích lũy các chuỗi.
    rendered = []
    for m in to_summarize:
        # `m.get("role", "?")` — lấy role, mặc định "?" nếu không có key "role".
        role = m.get("role", "?")

        # `if role == "tool":` — so sánh bằng (==). "tool" là role cho kết quả
        # thực thi tool (ví dụ: kết quả của read_file, bash...).
        if role == "tool":
            # Tool result — cap 500 chars per (tool results có thể rất dài,
            # vd pytest output 5KB). Summary không cần full content, chỉ
            # cần biết "tool X returned roughly Y".
            # `(m.get("content") or "")[:500]` — slicing string: lấy 500 ký tự đầu.
            # Cú pháp: chuỗi[start:stop], bỏ start → từ đầu; stop=500 → đến index 499.
            content = (m.get("content") or "")[:500]
            # `rendered.append(...)` — phương thức `.append()` thêm 1 phần tử vào
            # CUỐI danh sách. Khác `.extend()`: append thêm 1 phần tử,
            # extend thêm nhiều phần tử từ iterable.
            # f-string: chuỗi bắt đầu bằng `f"..."`, dấu `{}` chứa biểu thức Python
            # sẽ được thay thế bằng giá trị thực.
            rendered.append(f"[tool result] {content}")

        elif role == "assistant":
            # `elif` = "else if": kiểm tra điều kiện tiếp theo nếu `if` trước đó sai.
            # Assistant: content (visible text) + tool_calls (actions taken)
            content = m.get("content") or ""
            # `m.get("tool_calls") or []` — lấy list tool calls, mặc định [].
            tcs = m.get("tool_calls") or []
            line = f"[assistant] {content}"

            # List tool calls model đã emit — chỉ name + first 200 chars args
            # (đủ để summarizer hiểu "agent đã làm gì").
            for tc in tcs:
                fn = tc.get("function", {})
                # `(fn.get("arguments", "") or "")[:200]` — lấy 200 chars đầu.
                args_preview = (fn.get("arguments", "") or "")[:200]
                # `line +=` — nối thêm vào chuỗi `line`. Trong Python, chuỗi
                # có thể cộng với `+`. `\n` là ký tự xuống dòng (newline).
                line += f"\n  → {fn.get('name', '?')}({args_preview})"
            rendered.append(line)

        else:
            # `else:` — khối code chạy khi TẤT CẢ điều kiện `if/elif` trên đều sai.
            # Ở đây: role=user hoặc role=system.
            # role=user or system — chỉ content. Cap 500 chars để safe.
            rendered.append(f"[{role}] {(m.get('content') or '')[:500]}")

    # `"\n".join(rendered)` — phương thức `.join()` nối các phần tử list thành
    # một chuỗi duy nhất, ngăn cách bởi `"\n"` (ký tự xuống dòng).
    # Ví dụ: "\n".join(["a", "b", "c"]) → "a\nb\nc"
    # Khác: `" ".join(["a", "b"]) → "a b"` (ngăn cách bởi dấu cách).
    history_text = "\n".join(rendered)

    # STEP 4: Gọi LLM để summarize. Dùng SEPARATE message list (không phải
    # `messages` đang summarize) — đây là fresh "summarization session".
    # Thinking OFF cho speed; max_tokens=600 (≈400 words).
    # `client.chat.completions.create(...)` — gọi phương thức tạo completion.
    # `.` là toán tử truy cập thuộc tính/phương thức: client.chat → object chat,
    # .completions → object completions, .create(...) → gọi hàm create.
    # `# type: ignore[...]` — chú thích cho type checker (Pylance/mypy) bỏ qua
    # dòng này, vì ta truyền dict thông thường thay vì TypedDict OpenAI yêu cầu.
    summary_resp = client.chat.completions.create(  # type: ignore[arg-type,call-overload]
        model=model,
        # `messages=[{...}, {...}]` — list các dict message, mỗi dict có
        # "role" và "content". Đây là format chuẩn OpenAI Chat API.
        messages=[
            {
                "role": "system",
                "content": (
                    "You summarize agent conversation history concisely. "
                    "Be terse (<400 words). PRESERVE: tool calls made (with names "
                    "and file paths), files touched, key decisions, errors encountered, "
                    "current state of the work. DROP: chit-chat, redundant restating."
                ),
            },
            {
                "role": "user",
                "content": f"Summarize this agent trajectory:\n\n{history_text}",
            },
        ],
        max_tokens=600,
        # `extra_body={"chat_template_kwargs": {"enable_thinking": False}}` —
        # tham số bổ sung gửi kèm request (không nằm trong spec OpenAI chuẩn).
        # vLLM forward `extra_body` thẳng vào body HTTP request.
        # `enable_thinking: False` tắt thinking của Qwen3 cho lần gọi này.
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    # `summary_resp.choices[0].message.content` — truy cập chuỗi cấp sâu:
    #   .choices → list các lựa chọn (thường model trả 1 choice)
    #   [0]      → lấy choice đầu tiên (index 0)
    #   .message → object message của choice đó
    #   .content → chuỗi nội dung (có thể None nếu model không trả text)
    # `or ""` → đảm bảo không None.
    # `.strip()` — phương thức chuỗi, xóa khoảng trắng (space, tab, newline)
    # ở ĐẦU và CUỐI chuỗi. Ví dụ: "  hello \n".strip() → "hello".
    summary = (summary_resp.choices[0].message.content or "").strip()

    # STEP 5: Build new messages list.
    # [original system, summary as system, ...recent verbatim]
    # Prefix "[Earlier conversation summary]" giúp model phân biệt với
    # original system prompt khi đọc.
    # `[item1, item2, *recent]` — UNPACKING với dấu `*`.
    # `*recent` "trải" list `recent` ra thành các phần tử riêng lẻ bên trong list mới.
    # Ví dụ: [1, 2, *[3, 4, 5]] → [1, 2, 3, 4, 5]
    # Nếu viết [item1, item2, recent] (không có *), recent sẽ là phần tử thứ 3
    # dưới dạng list lồng (nested): [item1, item2, [3, 4, 5]] — sai ý.
    new_messages = [
        system_msg,
        {
            "role": "system",
            "content": f"[Earlier conversation summary]\n{summary}",
        },
        *recent,
    ]

    # STEP 6: Build status message — show savings cho user/log.
    before_tok = estimate_tokens(messages)
    after_tok = estimate_tokens(new_messages)
    # `f"..."` — f-string với biểu thức phức tạp hơn:
    # `{100 * (1 - after_tok/max(before_tok, 1)):.0f}` — tính phần trăm giảm.
    #   `max(before_tok, 1)` — tránh chia cho 0 (nếu before_tok=0).
    #   `:.0f` — format số thực với 0 chữ số thập phân (làm tròn nguyên).
    #   Ví dụ: 73.6 → "74" (in là "74%").
    status = (f"compacted {len(messages)}→{len(new_messages)} messages, "
              f"~{before_tok}→~{after_tok} tokens "
              f"({100 * (1 - after_tok/max(before_tok, 1)):.0f}% reduction)")

    # `return new_messages, status` — trả về TUPLE gồm list mới và chuỗi trạng thái.
    # Caller dùng: `new_msgs, status = compact_messages(...)` để "unpack" tuple.
    return new_messages, status


# ---------------------------------------------------------------------------
# HÀM handle_slash
# ---------------------------------------------------------------------------
# Hàm xử lý các lệnh slash (bắt đầu bằng `/`).
# `cmd: str` — tham số là chuỗi.
# `messages: list` — tham số là list (để có thể xóa history).
# `system_prompt: str` — tham số là chuỗi.
# `-> bool` — trả về bool (True/False).
#   True = đã xử lý xong lệnh, KHÔNG cần gọi LLM.
#   False = không phải lệnh slash, cần gọi LLM bình thường.
def handle_slash(cmd: str, messages: list, system_prompt: str) -> bool:
    """Xử lý slash command. Return True nếu đã xử lý xong (skip LLM call)."""
    # `.strip()` xóa khoảng trắng đầu/cuối.
    # `.lower()` chuyển tất cả ký tự thành chữ thường (lowercase).
    # Ví dụ: "  /EXIT  ".strip().lower() → "/exit"
    # Gán vào `c` để không phải gọi lại hai lần (hiệu suất + dễ đọc).
    c = cmd.strip().lower()

    # `in` — toán tử kiểm tra thành viên: `x in container` → True nếu x tồn tại
    # trong container (list, tuple, set, chuỗi...).
    # `("/exit", "/quit", "/q")` là TUPLE — nhóm các giá trị liên quan.
    # Kiểm tra `c` có nằm trong tuple này không.
    if c in ("/exit", "/quit", "/q"):
        # `print(...)` — hàm built-in in ra console. Không trả về gì cả (trả về None).
        # `f"{CYAN}Bye.{RESET}"` — f-string với màu CYAN, reset sau chữ "Bye."
        print(f"{CYAN}Bye.{RESET}")
        # `sys.exit(0)` — thoát chương trình hoàn toàn.
        # `0` = exit code = 0 nghĩa là "thành công" (quy ước Unix).
        # Khác `return`: `return` thoát khỏi HÀM, `sys.exit()` thoát cả CHƯƠNG TRÌNH.
        sys.exit(0)

    if c in ("/clear", "/reset"):
        # Xoá history nhưng giữ lại system prompt — mỗi conversation cần system.
        # `messages.clear()` — phương thức xóa TẤT CẢ phần tử trong list.
        # Khác `messages = []`: câu sau tạo list MỚI và gán tên `messages` vào đó,
        # nhưng caller vẫn giữ ref đến list CŨ. `.clear()` xóa tại chỗ (in-place),
        # caller thấy list rỗng ngay.
        messages.clear()
        # `messages.append({...})` — thêm 1 dict vào list.
        # Sau clear() + append() này: messages = [{"role": "system", "content": ...}]
        # Giữ system prompt để model luôn biết mình là ai.
        messages.append({"role": "system", "content": system_prompt})
        print(f"{CYAN}Conversation cleared.{RESET}")
        # `return True` — báo caller "đã xử lý rồi, không cần gọi LLM".
        return True

    if c in ("/help", "/?"):
        # Liệt kê ĐẦY ĐỦ slash commands — kể cả những lệnh xử lý inline trong chat()
        # (/think /nothink /mode /compact /tokens). User gõ /help phải thấy mọi lệnh có thể dùng.
        print(f"{CYAN}Commands: /exit  /clear  /help  /think  /nothink  /mode  /compact  /tokens{RESET}")
        return True

    # `c.startswith("/")` — phương thức chuỗi: trả về True nếu chuỗi BẮT ĐẦU bằng "/".
    # Ví dụ: "/unknown".startswith("/") → True; "hello".startswith("/") → False.
    if c.startswith("/"):
        print(f"{RED}Unknown command: {cmd}. Try /help.{RESET}")
        return True

    # Nếu không phải slash command, trả về False (để caller gọi LLM).
    return False


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
    # khi model tạo xong toàn bộ response rồi mới trả về. Với văn bản dài (2048
    # tokens), bạn có thể chờ 10-30 giây trước khi thấy bất kỳ chữ nào.
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
        max_tokens=2048,         # giới hạn độ dài response (tính bằng token)
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
                print(f"\n{CYAN}[thinking]{RESET}", flush=True)
                in_thinking = True
                in_content = False
            # `end=""` — tham số của print(): mặc định print thêm "\n" (xuống dòng)
            # sau mỗi lần gọi. `end=""` thay bằng chuỗi rỗng → không xuống dòng.
            # Nhờ vậy các mảnh thinking nối liền nhau thành 1 đoạn văn liên tục.
            # `flush=True` — ghi ngay, không đợi buffer đầy.
            print(f"{WHITE}{r}{RESET}", end="", flush=True)

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
                print(f"\n{MAGENTA}[assistant]{RESET}", flush=True)
                in_content = True
                in_thinking = False
            # `end=""` + `flush=True` → in mảnh ngay, không xuống dòng.
            # `content_buf += delta.content` — cộng dồn mảnh mới vào buffer.
            print(f"{MAGENTA}{delta.content}{RESET}", end="", flush=True)
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
    # `load_dotenv()` — đọc file .env và nạp vào os.environ.
    # Sau lệnh này: os.environ["VLLM_BASE_URL"] có giá trị từ file .env.
    load_dotenv()
    # `os.environ["KEY"]` — truy cập biến môi trường. Crash nếu key không tồn tại.
    base_url = os.environ["VLLM_BASE_URL"]
    model = os.environ["VLLM_MODEL_NAME"]
    # `os.environ.get("KEY", "default")` — lấy biến môi trường, có giá trị mặc định
    # nếu không tìm thấy. An toàn hơn os.environ["KEY"].
    api_key = os.environ.get("VLLM_API_KEY", "not-needed")

    # `OpenAI(base_url=..., api_key=...)` — tạo instance (object) của class OpenAI.
    # `base_url` chỉ đến vLLM local (ví dụ http://localhost:8000/v1) thay vì
    # api.openai.com — ta dùng OpenAI SDK vì vLLM implement OpenAI-compatible API.
    client = OpenAI(base_url=base_url, api_key=api_key)
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
    print(f"{BLUE}{'═' * 60}{RESET}")
    print(f"{BLUE}  coding-agent (REPL chat){RESET}")
    print(f"  model     : {model}")
    print(f"  endpoint  : {base_url}")
    print(f"  workspace : {workspace}")
    print(f"  commands  : /exit  /clear  /help  /think  /nothink  /mode  /compact  /tokens")
    print(f"  mode      : fast (thinking off) — gõ /think để bật deep thinking")
    print(f"  compact   : auto-trigger ở ~{COMPACT_THRESHOLD_TOKENS} tokens (giữ {KEEP_RECENT_MESSAGES} msg gần nhất)")
    print(f"{BLUE}{'═' * 60}{RESET}")

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
            user_input = input(f"\n{CYAN}you> {RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            # `EOFError` — xảy ra khi stdin đóng (ví dụ: pipe bị đứt, file input kết thúc).
            # `KeyboardInterrupt` — xảy ra khi user bấm Ctrl+C.
            # Cả hai đều là tín hiệu "user muốn thoát" → thoát gracefully (không crash).
            print(f"\n{CYAN}Bye.{RESET}")
            return  # `return` trong hàm không có giá trị trả về → thoát hàm chat().

        # `if not user_input:` — nếu user_input là chuỗi rỗng "" (sau strip()).
        # Xảy ra khi user bấm Enter mà không gõ gì → bỏ qua, lấy input tiếp.
        if not user_input:
            continue  # `continue` — bỏ qua phần còn lại của vòng while, lặp từ đầu.

        # --- Thinking mode toggle (sticky) ---
        # Tách riêng khỏi handle_slash vì cần mutate `thinking_enabled` (closure var).
        # `low = user_input.lower()` — chuyển thành lowercase để so sánh không phân biệt hoa/thường.
        # Ví dụ: "/THINK" → "/think"
        low = user_input.lower()

        # `/think` — BẬT thinking mode.
        # `thinking_enabled = True` — gán True vào biến.
        # `continue` — quay lại đầu vòng while, bỏ qua phần gọi LLM.
        if low in ("/think", "/deep"):
            thinking_enabled = True
            print(f"{CYAN}Thinking mode: ON (deep — model thinks before each turn){RESET}")
            continue

        # `/nothink` — TẮT thinking mode.
        if low in ("/nothink", "/fast"):
            thinking_enabled = False
            print(f"{CYAN}Thinking mode: OFF (fast — model responds directly){RESET}")
            continue

        # `/mode` — xem thinking mode hiện tại.
        if low == "/mode":
            # `m = "ON (deep)" if thinking_enabled else "OFF (fast)"` —
            # CONDITIONAL EXPRESSION (ternary operator) — cú pháp rút gọn của if/else:
            # `giá_trị_nếu_true if điều_kiện else giá_trị_nếu_false`
            # Nếu thinking_enabled là True → m = "ON (deep)"
            # Nếu thinking_enabled là False → m = "OFF (fast)"
            m = "ON (deep)" if thinking_enabled else "OFF (fast)"
            print(f"{CYAN}Thinking mode: {m}{RESET}")
            continue

        # --- Compaction commands (inline vì cần client + model từ closure) ---
        # `closure` = biến từ scope bên ngoài được dùng trong hàm/block bên trong.
        # Ở đây `client` và `model` được định nghĩa ở đầu hàm `chat()` nhưng
        # dùng được trong đoạn code này vì cùng phạm vi hàm.

        # /tokens: show estimate without doing anything. Useful trước khi
        # quyết định có /compact manually hay không.
        if low in ("/tokens", "/tok"):
            tok = estimate_tokens(messages)
            # `100 * tok / MAX_MODEL_LEN` — tính phần trăm.
            # `/` là chia thông thường (trả float). Nhân 100 để ra phần trăm.
            pct = 100 * tok / MAX_MODEL_LEN
            # Màu cảnh báo theo mức độ gần threshold: đỏ = đã vượt (auto-compact
            # sẽ chạy ở turn sau), vàng = đang tiến sát, xanh = còn thoải mái.
            warn_level = COMPACT_THRESHOLD_TOKENS - 4000  # ~20K, ngưỡng "đang sát"
            # NESTED TERNARY: `a if cond1 else (b if cond2 else c)` — kiểm tra nhiều điều kiện.
            color = RED if tok > COMPACT_THRESHOLD_TOKENS else (YELLOW if tok > warn_level else GREEN)
            # `MAX_MODEL_LEN // 1000` — chia nguyên: 32768 // 1000 = 32 (bỏ phần lẻ).
            # `:.0f` trong f-string — format float với 0 chữ số thập phân.
            print(f"{color}Token estimate: ~{tok} / {MAX_MODEL_LEN // 1000}K ({pct:.0f}%)  "
                  f"[threshold: {COMPACT_THRESHOLD_TOKENS}]{RESET}")
            continue

        # /compact: trigger summarization NGAY, kể cả khi chưa đụng threshold.
        # Useful khi user biết tasks sắp tới sẽ tốn nhiều tokens và muốn pre-free
        # context budget.
        if low == "/compact":
            print(f"{CYAN}Compacting conversation history...{RESET}")
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
                print(f"{CYAN}{status}{RESET}")
            except Exception as e:
                # `except Exception as e:` — bắt MỌI loại exception (Exception là base class).
                # `as e` — gán exception object vào biến `e` để có thể in thông báo lỗi.
                # `str(e)` — chuyển exception thành chuỗi mô tả lỗi.
                # Compaction là best-effort — nếu LLM call fail, KHÔNG được crash
                # REPL. Báo lỗi, để user tự xử lý (e.g. /clear).
                print(f"{RED}Compaction failed: {e}{RESET}")
            continue

        # `handle_slash(user_input, messages, SYSTEM_PROMPT)` — gọi hàm đã định nghĩa trên.
        # Nếu trả về True (đã xử lý lệnh slash) → continue (bỏ qua LLM call).
        if handle_slash(user_input, messages, SYSTEM_PROMPT):
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
        # Trigger ở threshold 24K (~75% của 32K) chứ không 31K — để chừa
        # buffer cho:
        #   - response tokens (~2K max_tokens)
        #   - inaccuracy của estimate_tokens (±20-30%)
        #   - tool results spike trong inner loop trước khi compact lần sau
        #
        # Compaction tốn 1 extra LLM call (~3-5s), nhưng rẻ hơn nhiều so với
        # context overflow crash buộc user gõ /clear (mất toàn bộ history).
        tok_estimate = estimate_tokens(messages)
        if tok_estimate > COMPACT_THRESHOLD_TOKENS:
            print(f"{YELLOW}[auto-compact] ~{tok_estimate} tokens > threshold "
                  f"{COMPACT_THRESHOLD_TOKENS}, summarizing history...{RESET}")
            try:
                new_msgs, status = compact_messages(messages, client, model)
                messages[:] = new_msgs
                print(f"{YELLOW}[auto-compact] {status}{RESET}")
            except Exception as e:
                # Best-effort: nếu compact fail, vẫn cứ thử gửi request original
                # (có thể vẫn dưới limit nếu estimate sai cao). Worse case
                # vLLM trả 400 và except block bên dưới handle.
                print(f"{RED}[auto-compact] failed: {e} — proceeding without compaction{RESET}")

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
                print(f"\n{RED}[interrupted]{RESET}")
                # Append assistant placeholder để conversation không lệch.
                # Nếu không append, history sẽ kết thúc bằng role=user → model bị
                # confuse ở turn sau (nghĩ user chưa nhận được response).
                messages.append({"role": "assistant", "content": "[interrupted by user]"})
                break  # `break` — thoát khỏi vòng for NGAY LẬP TỨC (không chạy tiếp).
            except Exception as e:
                print(f"\n{RED}API error: {e}{RESET}")
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

            # --- Validate JSON args TRƯỚC KHI append vào history ---
            # Nếu model emit bad JSON (vd Python triple-quote `"""..."""`),
            # vLLM sẽ trả 400 ở turn sau vì history chứa tool_call args không
            # parse được. Mark broken để:
            #   (a) Thay arguments bằng "{}" trong history → vLLM happy.
            #   (b) Trả error message rõ cho model retry với JSON đúng.
            for tc in tool_calls:
                try:
                    if tc["arguments"]:
                        # `json.loads(chuỗi)` — JSON DESERIALIZATION.
                        # JSON là định dạng dữ liệu dạng văn bản, ví dụ: '{"path": "/etc/hosts"}'
                        # `json.loads()` chuyển chuỗi JSON thành dict/list Python.
                        # Nếu chuỗi không hợp lệ JSON → ném `json.JSONDecodeError`.
                        # Ở đây ta chỉ kiểm tra (không dùng kết quả), nên không gán vào biến.
                        json.loads(tc["arguments"])
                except json.JSONDecodeError as e:
                    # `json.JSONDecodeError` — loại exception cụ thể khi JSON parse fail.
                    # `tc["_bad_json"] = True` — thêm key "_bad_json" vào dict tc.
                    # Dấu `_` đầu tên key là quy ước "key nội bộ, không phải data thật".
                    tc["_bad_json"] = True
                    tc["_bad_json_error"] = str(e)

            # --- Build assistant message để append vào history ---
            # Phải giữ NGUYÊN `tool_calls` field cho turn sau, giống agent.py
            # (xem comment dài về model_dump trong agent.py line 154-163).
            # `asst_msg: dict = {...}` — khai báo type hint cho biến cục bộ.
            asst_msg: dict = {"role": "assistant", "content": content_buf or None}
            # `content_buf or None` — nếu content_buf rỗng (""), dùng None.
            # API yêu cầu content là None (không phải "") khi chỉ có tool_calls.

            if tool_calls:
                # `asst_msg["tool_calls"] = [...]` — gán list vào key mới.
                # List comprehension tạo list các dict từ `tool_calls`:
                # `[{...} for tc in tool_calls]` — với mỗi tc trong tool_calls, tạo dict.
                asst_msg["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            # Bad JSON → "{}" để history hợp lệ. Tool result vẫn nói lỗi.
                            # CONDITIONAL EXPRESSION: nếu có _bad_json → "{}", ngược lại → arguments gốc.
                            "arguments": "{}" if tc.get("_bad_json") else tc["arguments"],
                        },
                    }
                    for tc in tool_calls
                ]
            # `messages.append(asst_msg)` — thêm assistant message vào history.
            # Sau bước này, history có dạng: [..., user_msg, assistant_msg]
            messages.append(asst_msg)

            # --- Nếu model không gọi tool → câu trả lời cuối, ra ngoài inner loop ---
            # `if not tool_calls:` — tool_calls là list rỗng [] → falsy → `not []` = True.
            if not tool_calls:
                break  # Thoát inner for loop, quay lại outer while để nhận input tiếp.

            # --- Thực thi từng tool call, append result vào history ---
            # INVARIANT: asst_msg vừa append có N tool_calls. API yêu cầu MỖI
            # tool_call phải có đúng 1 role=tool result với matching id ở phía
            # sau. Nếu thiếu (vd Ctrl+C giữa execute_tool của tool dài như
            # run_tests), tool_call thành orphan → vLLM 400 ở turn sau. Vì vậy
            # ta dùng `interrupted` flag: khi user ngắt, vẫn append placeholder
            # result cho MỌI tool còn lại để giữ pairing hợp lệ, rồi mới break.
            interrupted = False
            for tc in tool_calls:
                args_str = tc["arguments"]
                # Cắt args dài cho gọn khi in (model vẫn nhận full qua history).
                # `len(args_str) <= 200` — nếu ngắn hơn 200 chars → in nguyên.
                # `args_str[:200] + "...[truncated]"` — cắt 200 chars + thêm hậu tố.
                args_preview = args_str if len(args_str) <= 200 else args_str[:200] + "...[truncated]"
                print(f"{GREEN}▶ {tc['name']}({args_preview}){RESET}")

                if interrupted:
                    # Đã bị Ctrl+C ở tool trước — không chạy nữa, chỉ điền
                    # placeholder để tool_call này không bị orphan.
                    result = "[skipped: user interrupted tool execution]"
                elif tc.get("_bad_json"):
                    # Không gọi execute_tool — args không parse được.
                    # Error message này được gửi NGƯỢC lại model. Giữ ENGLISH-ONLY
                    # vì Qwen3 instruct tuned trên English; trộn Vietnamese giảm
                    # tỉ lệ retry thành công (em đã quan sát qua demo trước).
                    result = (
                        f"ERROR: invalid JSON in arguments: {tc['_bad_json_error']}\n"
                        "Retry with valid JSON. Escape newlines as \\n and double-quotes as \\\". "
                        "Do NOT use Python triple-quote (\"\"\") inside JSON strings."
                    )
                else:
                    try:
                        # `execute_tool(name, args_str, workspace)` — thực thi tool.
                        # Hàm này được import từ src/tools.py. Trả về chuỗi kết quả.
                        result = execute_tool(tc["name"], args_str, workspace)
                    except KeyboardInterrupt:
                        # Ctrl+C giữa 1 tool dài. Đánh dấu interrupted để các tool
                        # còn lại chỉ điền placeholder (giữ pairing), không crash REPL.
                        print(f"\n{RED}[interrupted]{RESET}")
                        interrupted = True
                        result = "[interrupted: user cancelled tool execution]"

                # In preview của kết quả (500 chars đầu).
                result_preview = result if len(result) <= 500 else result[:500] + "...[truncated]"
                print(f"{YELLOW}  ↳ {result_preview}{RESET}")

                # role=tool message — tool_call_id PHẢI khớp với tc.id để API
                # link result với call. Sai id → API reject conversation.
                # `messages.append({...})` — thêm tool result vào history.
                # Sau bước này: [..., user, assistant(tool_calls), tool_result, ...]
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })

            # Nếu user đã ngắt giữa tool execution → kết thúc turn này (history
            # vẫn hợp lệ vì mọi tool_call đã có result). Không chạy stream tiếp.
            if interrupted:
                break
            # Loop sang turn tiếp theo — model sẽ "thấy" tool results vừa append.
            # Python tiếp tục lên đầu `for _turn in range(...)` và lặp tiếp.

        else:
            # `else` của vòng `for` — Python có tính năng độc đáo: `for...else`.
            # Khối `else` của `for` chạy khi vòng lặp KẾT THÚC TỰ NHIÊN (không bị `break`).
            # Nếu có `break` → `else` KHÔNG chạy.
            # Ở đây: chạy hết max_tool_turns mà không break → model vẫn gọi tool → cảnh báo.
            print(f"{RED}Hit max_tool_turns={max_tool_turns}. Stopping this turn.{RESET}")


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


# ---------------------------------------------------------------------------
# ENTRY POINT — ĐIỂM KHỞI CHẠY
# ---------------------------------------------------------------------------
# `if __name__ == "__main__":` — đây là PATTERN chuẩn Python.
#
# `__name__` là biến đặc biệt Python tự đặt:
#   - Khi file được CHẠY TRỰC TIẾP (`python chat.py`): __name__ = "__main__"
#   - Khi file được IMPORT bởi file khác (`import chat`): __name__ = "chat"
#
# `__main__` là chuỗi đặc biệt — không phải tên biến, là chuỗi ký tự "__main__".
#
# Ý nghĩa của pattern:
#   - `python chat.py` → __name__ == "__main__" → True → chạy `sys.exit(main())`
#   - `import chat` (từ file khác) → __name__ == "chat" → False → KHÔNG chạy
#     sys.exit(main()). Chỉ import hàm/biến mà không chạy ngay.
#
# TẠI SAO QUAN TRỌNG?
#   Nếu không có block này, `sys.exit(main())` sẽ chạy MỖI KHI file được import —
#   kể cả khi test runner import để kiểm thử. Block này ngăn điều đó.
#
# `sys.exit(main())`:
#   - Gọi `main()` trước, lấy exit code (int) trả về.
#   - Truyền exit code vào `sys.exit()` → thoát chương trình với code đó.
#   - Exit code 0 = thành công (convention Unix/Linux/macOS).
if __name__ == "__main__":
    sys.exit(main())
