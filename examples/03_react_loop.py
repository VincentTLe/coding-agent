"""
03_react_loop.py — Vòng lặp ReAct tối thiểu (reason -> act -> observe).

LESSON 3 of the ladder (sau 02_one_tool.py, trước 04_sandbox_safety.py).
  Lesson 02 xử lý ĐÚNG MỘT tool_call bằng tay rồi dừng. Nhưng một task thật
  cần NHIỀU bước: liệt kê thư mục -> đọc file -> ghi file -> đọc lại để kiểm
  tra... Mỗi bước model lại "thấy" kết quả bước trước rồi quyết định bước kế.
  Biến "xử lý 1 lần" thành "lặp tới khi xong" — đó chính là ReAct loop.

  Đây là TRÁI TIM của src/agent.py, rút gọn để học. agent.py thêm màu mè,
  logging, time-budget, "nudge" khi model lười gọi tool... nhưng khung xương
  thì đúng bằng vòng for dưới đây.

REACT = REASON + ACT, xen kẽ. Mỗi vòng lặp:
  - REASON : gửi messages + tool schema -> model suy nghĩ (có thể có content).
  - ACT    : model phát ra tool_calls (muốn làm gì đó) HOẶC không (đã xong).
  - OBSERVE: ta chạy từng tool, gắn kết quả (role="tool") vào messages.
  Rồi LẶP LẠI: vòng sau model đọc được kết quả vừa quan sát.

HAI BẤT BIẾN PHẢI GIỮ (sai 1 trong 2 là loop hỏng):
  (1) PAIRING — ghép cặp tool_call <-> tool result:
      Mỗi assistant message mang `tool_calls` PHẢI được theo sau bởi đúng MỘT
      message role="tool" cho MỖI tool_call_id. Thiếu/lệch id => server trả
      400. Vì 1 turn có thể có NHIỀU tool_calls, ta append đủ N kết quả.
  (2) TERMINATION — điều kiện dừng:
      Dừng khi model trả về KHÔNG có tool_calls (nó tự nhận đã xong), HOẶC khi
      chạm max_iters (lưới an toàn chống lặp vô tận). Không có (2) thì 1 model
      bị kẹt có thể gọi tool mãi mãi.

CHẠY THỬ
  $ python examples/03_react_loop.py
  Task mẫu: đọc input.txt, viết hoa, ghi ra output.txt, rồi xác nhận.
  Bạn sẽ thấy nhiều Turn nối nhau tới khi model dừng gọi tool.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Thêm project root vào sys.path để import được `src` khi chạy như script
# (`python examples/03_react_loop.py`). Xem giải thích ở lesson 02.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

# Mượn ĐÚNG dispatcher + schema THẬT của repo. Ta KHÔNG tự viết lại tool —
# chỉ lọc ra vài tool cho gọn (lesson này dạy VÒNG LẶP, không phải tool).
#   TOOL_SCHEMAS: list schema JSON của cả 11 tool (gồm finish).
#   execute_tool(name, json_args, workspace): chạy 1 tool, luôn trả string.
from src.tools import TOOL_SCHEMAS, execute_tool


# ===================================================================
# SECTION 1 — CONFIG + CLIENT (giống lesson 01/02)
# ===================================================================
load_dotenv()
BASE_URL = os.environ["VLLM_BASE_URL"]
MODEL = os.environ["VLLM_MODEL_NAME"]
API_KEY = os.environ.get("VLLM_API_KEY", "not-needed")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)


# ===================================================================
# SECTION 2 — CHỌN MỘT TẬP NHỎ TOOL
# ===================================================================
# agent.py đưa cho model cả 11 tool. Để học vòng lặp, 3 tool là đủ và dễ theo
# dõi: liệt kê (list_dir), đọc (read_file), ghi (write_file). Ta LỌC TOOL_SCHEMAS
# THẬT theo tên thay vì chép tay — đảm bảo schema khớp với hàm trong src/tools.py.
ALLOWED = {"list_dir", "read_file", "write_file"}
SCHEMAS = [s for s in TOOL_SCHEMAS if s["function"]["name"] in ALLOWED]


# ===================================================================
# SECTION 3 — SANDBOX có sẵn dữ liệu cho task mẫu
# ===================================================================
WORKSPACE = Path("/tmp/lesson03_ws")
WORKSPACE.mkdir(parents=True, exist_ok=True)
(WORKSPACE / "input.txt").write_text(
    "hello react loop\nthis is lesson three\n",
    encoding="utf-8",
)


# ===================================================================
# SECTION 4 — VÒNG LẶP ReAct
# ===================================================================
def run_react(goal: str, max_iters: int = 8) -> str:
    """Lặp reason->act->observe tới khi model hết gọi tool hoặc chạm max_iters.

    Trả về finish_reason ("finished" / "max_iters") để biết loop kết thúc kiểu gì.
    Đây là phiên bản tối giản của run_agent() trong src/agent.py.
    """
    # Sổ ký ức: system (cho biết có tool gì) + user (goal). Mỗi vòng ta gửi LẠI
    # TOÀN BỘ list này (server stateless — bài học cốt lõi từ lesson 01).
    messages: list[ChatCompletionMessageParam] = [
        {
            "role": "system",
            "content": (
                "You are a coding agent. Use the provided tools to accomplish the "
                "task. Call tools to inspect and change files; when the task is fully "
                "done, reply with a short final message and DO NOT call any more tools."
            ),
        },
        {"role": "user", "content": goal},
    ]

    # Vòng for có CHẶN TRÊN = max_iters. Đây là nửa thứ hai của bất biến
    # TERMINATION: dù model có "ngoan cố" gọi tool mãi, loop vẫn thoát sau
    # max_iters vòng. range(1, n+1) để đánh số turn từ 1 cho dễ đọc.
    for i in range(1, max_iters + 1):
        print(f"\n=== Turn {i} (history: {len(messages)} messages) ===")

        # -----------------------------------------------------------
        # REASON — gửi messages + tool schema, để model tự quyết định.
        # tool_choice="auto": model ĐƯỢC PHÉP không gọi tool (cần thế để nó
        # còn "kết thúc" bằng một câu trả lời trần). "required" sẽ ép gọi tool
        # mỗi turn -> không bao giờ dừng được -> hỏng bất biến TERMINATION.
        # -----------------------------------------------------------
        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=SCHEMAS,
            tool_choice="auto",
            max_tokens=1024,
        )
        msg = resp.choices[0].message

        # APPEND assistant message NGUYÊN VẸN (model_dump) — KHÔNG tự dựng
        # {"role":"assistant","content":...} như lesson 01. Lý do là bất biến
        # PAIRING: nếu tự dựng, ta đánh rơi field tool_calls, và message
        # role="tool" ở dưới sẽ tham chiếu tool_call_id không tồn tại -> 400.
        # exclude_none=True bỏ các field None (vd content=None khi chỉ gọi tool)
        # nhưng GIỮ tool_calls + id nguyên vẹn.
        messages.append(msg.model_dump(exclude_none=True))  # type: ignore[arg-type]

        # Nếu model có nói gì (narrate), in ra. Có thể None khi nó chỉ gọi tool.
        if msg.content:
            print(f"[assistant] {msg.content}")

        # -----------------------------------------------------------
        # ĐIỀU KIỆN DỪNG (bất biến TERMINATION, nửa thứ nhất):
        # KHÔNG có tool_calls = model tự nhận đã xong -> ta tin và thoát.
        # `not msg.tool_calls` đúng cả khi tool_calls là None lẫn list rỗng.
        # -----------------------------------------------------------
        if not msg.tool_calls:
            print("\n[finished] model stopped calling tools.")
            return "finished"

        # -----------------------------------------------------------
        # ACT + OBSERVE — chạy MỌI tool_call trong turn này.
        # Một turn có thể chứa NHIỀU tool_calls (model gọi song song). Bất biến
        # PAIRING đòi ta append ĐÚNG MỘT message role="tool" cho TỪNG cái, với
        # tool_call_id khớp. Thiếu một kết quả thôi là API sẽ từ chối turn sau.
        # -----------------------------------------------------------
        for tc in msg.tool_calls:
            name = tc.function.name
            raw_args = tc.function.arguments  # JSON string, KHÔNG phải dict
            print(f"[tool] {name}({raw_args})")

            # execute_tool tự parse JSON args + chạy hàm với workspace ta đưa.
            # Luôn trả string (kể cả lỗi -> "ERROR: ..."), không bao giờ raise
            # => 1 tool fail không làm sập loop; model đọc ERROR và tự sửa ở
            # turn sau (chi tiết "error contract" ở lesson 04).
            result = execute_tool(name, raw_args, WORKSPACE)

            # Cắt ngắn khi IN cho đỡ rối terminal; model vẫn nhận FULL kết quả
            # qua messages.append bên dưới.
            preview = result if len(result) < 300 else result[:300] + "...[truncated]"
            print(f"[result] {preview}")

            # Mắt xích PAIRING: role="tool" + tool_call_id == tc.id + content.
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })
        # Hết for tool_calls -> quay lại đầu vòng for: model sẽ "thấy" mọi kết
        # quả vừa append và quyết định bước tiếp theo (hoặc dừng).

    # Thoát for mà chưa return = đã dùng hết max_iters mà model vẫn đòi gọi tool.
    # Đây là lưới an toàn, không hẳn là bug — có thể task quá khó hoặc model kẹt.
    print(f"\n[max_iters] hit {max_iters} turns without finishing.")
    return "max_iters"


def main() -> None:
    print(f"Connected to {MODEL} at {BASE_URL}")
    print(f"Workspace: {WORKSPACE}")
    print(f"Tools available to the model: {sorted(ALLOWED)}")

    goal = (
        "Read input.txt, convert its text to UPPERCASE, and write the result to "
        "output.txt. Then read output.txt back to confirm it was written correctly."
    )
    print(f"\nGOAL: {goal}")

    reason = run_react(goal, max_iters=8)
    print(f"\nfinish_reason = {reason}")

    # Cho bạn thấy kết quả thật trên đĩa sau khi loop chạy xong.
    out = WORKSPACE / "output.txt"
    if out.exists():
        print(f"\n[output.txt on disk]\n{out.read_text(encoding='utf-8')}")


if __name__ == "__main__":
    main()
