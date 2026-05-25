"""
02_one_tool.py — Đưa cho model ĐÚNG MỘT tool, và xử lý MỘT tool_call bằng tay.

LESSON 2 of the ladder (sau 01_chat.py, trước 03_react_loop.py).
  Lesson 01 chỉ có `messages` + `content`: model nói, ta in, hết.
  Ở đây model có thể NHỜ ta chạy 1 việc (đọc 1 file) rồi mới trả lời.
  Đó là bước nhảy quan trọng nhất: từ "chatbot" sang "agent biết hành động".

Ở lesson này ta cố tình KHÔNG dùng vòng lặp. Ta xử lý ĐÚNG MỘT lần tool_call,
bằng tay, để bạn nhìn rõ TỪNG mảnh ghép. Lesson 03 mới gói nó vào ReAct loop.

LUỒNG MỘT LẦN GỌI TOOL (ghi nhớ 4 bước này — cả agent thật cũng chỉ là nó lặp lại):
  1) Ta gửi messages + danh sách tool (schema) lên server.
  2) Model trả về 1 message có `tool_calls` (nó muốn ta chạy read_file) —
     lúc này `content` thường là None: model CHƯA trả lời, nó đang "xin dữ liệu".
  3) Ta chạy tool đó (execute_tool), gói kết quả vào 1 message role="tool",
     gắn đúng `tool_call_id` để server biết kết quả này trả lời cho call nào.
  4) Ta gửi LẠI toàn bộ messages (giờ đã có cả tool_call + tool result).
     Lần này model đọc kết quả và trả lời bằng `content` thật.

WORKSPACE = sandbox
  Tool đọc/ghi file luôn bị kẹp trong 1 thư mục (workspace). execute_tool()
  nhận `workspace: Path` và tự truyền xuống tool. Ở đây ta dựng 1 thư mục tạm
  /tmp/lesson02_ws với sẵn 1 file để model có cái mà đọc. (Vì sao sandbox lại
  quan trọng — để dành lesson 04.)

CHẠY THỬ
  $ python examples/02_one_tool.py
  Sẽ thấy: model gọi read_file -> ta chạy -> model đọc nội dung -> trả lời.
"""

from __future__ import annotations

# os/Path: đọc config + dựng đường dẫn sandbox. json: model trả arguments dưới
# dạng JSON STRING (không phải dict) — ta cần json.loads để in/đọc cho rõ.
import json
import os
import sys
from pathlib import Path

# Khi chạy `python examples/02_one_tool.py`, Python chỉ đặt thư mục `examples/`
# vào sys.path, nên `from src.tools import ...` sẽ KHÔNG tìm thấy. Thêm project
# root (cha của examples/) vào sys.path để import được package `src`. Đây là
# plumbing duy nhất; bỏ dòng này nếu bạn chạy bằng `python -m examples.02_one_tool`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

# Tái dùng dispatcher THẬT của agent: execute_tool(name, json_args, workspace).
# Đây chính là hàm src/agent.py gọi — ta không tự viết lại read_file, mà mượn
# luôn để lesson phản ánh đúng API hiện tại của repo.
from src.tools import execute_tool


# ===================================================================
# SECTION 1 — CONFIG + CLIENT (giống hệt lesson 01)
# ===================================================================
load_dotenv()
BASE_URL = os.environ["VLLM_BASE_URL"]
MODEL = os.environ["VLLM_MODEL_NAME"]
API_KEY = os.environ.get("VLLM_API_KEY", "not-needed")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)


# ===================================================================
# SECTION 2 — DỰNG SANDBOX (workspace) ĐỂ CÓ FILE CHO MODEL ĐỌC
# ===================================================================
# execute_tool() cần 1 `workspace: Path`. Mọi đường dẫn model gửi sẽ được hiểu
# là TƯƠNG ĐỐI so với workspace này (read_file("notes.txt") -> ws/notes.txt).
# Ta tạo thư mục tạm + ghi sẵn 1 file để demo có dữ liệu thật.
WORKSPACE = Path("/tmp/lesson02_ws")
WORKSPACE.mkdir(parents=True, exist_ok=True)
(WORKSPACE / "notes.txt").write_text(
    "Project: from-scratch coding agent\n"
    "Model: Qwen3-14B served by local vLLM\n"
    "Secret number: 42\n",
    encoding="utf-8",
)


# ===================================================================
# SECTION 3 — TOOL SCHEMA: MÔ TẢ TOOL CHO MODEL BẰNG JSON
# ===================================================================
# Model KHÔNG nhìn thấy hàm Python read_file. Nó chỉ thấy 1 mô tả JSON: tên,
# công dụng, và các tham số. Đây là "hợp đồng" giữa model và ta.
#
# Cấu trúc chuẩn OpenAI (GPT, Claude, vLLM, Ollama đều hiểu format này):
#   type: "function"
#   function:
#     name        -> tên tool; PHẢI khớp tên ta dùng khi gọi execute_tool().
#     description  -> model đọc dòng này để quyết định KHI NÀO nên gọi.
#     parameters  -> JSON Schema: tham số nào, kiểu gì, cái nào bắt buộc.
#
# Lưu ý: ta KHÔNG khai báo `workspace` ở đây. Sandbox là việc của ta, model
# không bao giờ được chọn workspace — execute_tool() tự gắn workspace vào.
READ_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read the full contents of a text file (path relative to the workspace).",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file, e.g. 'notes.txt'.",
                },
            },
            "required": ["path"],
        },
    },
}


# ===================================================================
# SECTION 4 — KHỞI TẠO MESSAGES (sổ ký ức, như lesson 01)
# ===================================================================
# system: nói cho model biết nó CÓ tool và nên dùng khi cần dữ liệu file.
# user:   1 câu hỏi mà muốn trả lời ĐÚNG thì BẮT BUỘC phải đọc file trước.
messages: list[ChatCompletionMessageParam] = [
    {
        "role": "system",
        "content": (
            "You are a helpful coding assistant with a read_file tool. "
            "When a question is about the contents of a file, call read_file "
            "first, then answer from what you read."
        ),
    },
    {
        "role": "user",
        "content": "What is the 'Secret number' written in notes.txt?",
    },
]


def main() -> None:
    print(f"Connected to {MODEL} at {BASE_URL}")
    print(f"Workspace: {WORKSPACE}\n")

    # ---------------------------------------------------------------
    # BƯỚC 1 — GỬI messages + tool schema, ĐỂ MODEL TỰ QUYẾT
    # ---------------------------------------------------------------
    # Khác lesson 01 ở đúng 2 tham số:
    #   tools=[READ_FILE_SCHEMA]  -> đưa danh sách tool cho model.
    #   tool_choice="auto"         -> để model TỰ chọn gọi tool hay không
    #                                 (KHÔNG ép buộc; model phải được phép
    #                                  "không gọi tool" để còn trả lời cuối cùng).
    print("  -> turn 1: sending question + 1 tool schema")
    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=[READ_FILE_SCHEMA],
        tool_choice="auto",
        max_tokens=512,
    )

    # Bóc message ra như lesson 01 — nhưng message này có thêm field tool_calls.
    msg = resp.choices[0].message

    # ---------------------------------------------------------------
    # BƯỚC 2 — ĐỌC tool_calls. KHI MODEL MUỐN GỌI TOOL, content THƯỜNG = None
    # ---------------------------------------------------------------
    # msg.tool_calls là 1 list (model có thể xin chạy NHIỀU tool 1 lúc). Ở lesson
    # này ta chỉ xử lý 1 cái -> lấy phần tử [0]. Nếu model KHÔNG gọi tool (trả
    # lời thẳng), ta in content rồi dừng — không phải câu hỏi nào cũng cần tool.
    if not msg.tool_calls:
        print("\n[assistant] (model answered without a tool)")
        print(msg.content or "")
        return

    # PHẢI append message assistant này (NGUYÊN VẸN, gồm tool_calls) vào sổ ký
    # ức TRƯỚC khi append kết quả tool. Đây là bất biến ghép cặp: 1 assistant
    # mang tool_calls phải đứng ngay trước message kết quả tool tương ứng, nếu
    # không server sẽ báo lỗi 400 (tool result không biết trả lời cho call nào).
    # model_dump(exclude_none=True): Pydantic -> dict, bỏ field None (như
    # content=None) nhưng GIỮ nguyên tool_calls + id.
    messages.append(msg.model_dump(exclude_none=True))  # type: ignore[arg-type]

    # Lấy ĐÚNG MỘT tool_call để xử lý bằng tay.
    tc = msg.tool_calls[0]

    # Mỗi tool_call gồm 3 phần quan trọng:
    #   tc.id                  -> mã định danh DUY NHẤT của call này. Lát nữa ta
    #                             gắn đúng id này vào message kết quả (pairing).
    #   tc.function.name        -> tên tool model muốn gọi ("read_file").
    #   tc.function.arguments   -> arguments dạng JSON STRING, vd '{"path": "notes.txt"}'.
    #                             KHÔNG phải dict! Muốn đọc field phải json.loads.
    tool_name = tc.function.name
    raw_args = tc.function.arguments
    print(f"\n[model wants tool] {tool_name}({raw_args})")
    print(f"[tool_call_id]     {tc.id}")

    # json.loads chỉ để IN cho bạn thấy nội dung (debug). execute_tool() bên dưới
    # tự parse lại JSON string này — ta không cần truyền dict đã parse vào nó.
    parsed = json.loads(raw_args)
    print(f"[parsed args]      {parsed}")

    # ---------------------------------------------------------------
    # BƯỚC 3 — CHẠY TOOL, GÓI KẾT QUẢ THÀNH MESSAGE role="tool"
    # ---------------------------------------------------------------
    # execute_tool(name, json_args_string, workspace):
    #   - tự parse JSON, tra hàm theo name, gọi với workspace ta đưa vào.
    #   - LUÔN trả về string (kể cả khi lỗi: chuỗi bắt đầu "ERROR:"). Nó không
    #     bao giờ raise — đó là "error contract" (chi tiết ở lesson 04).
    result = execute_tool(tool_name, raw_args, WORKSPACE)
    print(f"\n[tool result]\n{result}\n")

    # Message kết quả tool theo format CHUẨN OpenAI — 3 key bắt buộc:
    #   role: "tool"
    #   tool_call_id: PHẢI bằng tc.id ở trên -> đây là "dây nối" giữa lời nhờ và
    #                 kết quả. Sai/thiếu id = server 400.
    #   content: chuỗi kết quả; model sẽ đọc nó ở lần gọi sau.
    messages.append({
        "role": "tool",
        "tool_call_id": tc.id,
        "content": result,
    })

    # ---------------------------------------------------------------
    # BƯỚC 4 — GỬI LẠI messages (đã có kết quả tool) -> MODEL TRẢ LỜI THẬT
    # ---------------------------------------------------------------
    # Giờ sổ ký ức có: system, user, assistant(tool_calls), tool(result).
    # Model đọc kết quả file và lần này trả về content thật (thường KHÔNG gọi
    # tool nữa vì đã đủ thông tin). Vẫn truyền tools=[...] để model có quyền
    # gọi tiếp nếu nó muốn — nhưng ở demo này nó sẽ trả lời luôn.
    print(f"  -> turn 2: sending {len(messages)} messages (incl. tool result)")
    resp2 = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=[READ_FILE_SCHEMA],
        tool_choice="auto",
        max_tokens=512,
    )
    final = resp2.choices[0].message

    # reasoning (nếu server bật reasoning parser) chỉ là scratchpad — in cho vui,
    # KHÔNG append lại vào messages (giống lesson 01).
    reasoning = getattr(final, "reasoning", None)
    if reasoning:
        print(f"\n[reasoning]\n{reasoning}")
    print(f"\n[assistant]\n{final.content or ''}")


if __name__ == "__main__":
    main()
