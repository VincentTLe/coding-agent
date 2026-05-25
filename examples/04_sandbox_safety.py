"""
04_sandbox_safety.py — Lớp an toàn: sandbox (_safe_path) + "error contract".

LESSON 4 of the ladder (sau 03_react_loop.py — lesson cuối trước khi đọc src/).
  Lesson 03 cho model gọi tool trong vòng lặp. Nhưng model là 1 hộp đen KHÔNG
  đáng tin tuyệt đối: nó có thể (vô tình hoặc do prompt injection) thử đọc
  ~/.ssh/id_rsa, ghi đè /etc/passwd, hay gửi arguments rác. Lớp an toàn là thứ
  đứng GIỮA model và máy thật. Hai trụ cột:

  TRỤ CỘT 1 — SANDBOX qua _safe_path(path, workspace):
    Mọi thao tác file bị KẸP trong 1 thư mục (workspace). Đường dẫn nào resolve
    ra NGOÀI workspace (vd "../../etc/passwd") bị từ chối thẳng. Không có lớp
    này, 1 dòng model sinh ra có thể đọc/xoá bất cứ thứ gì user có quyền.

  TRỤ CỘT 2 — ERROR CONTRACT ("trả ERROR string, không bao giờ raise"):
    Tool gặp lỗi (file không tồn tại, JSON hỏng, path escape, tool lạ...) thì
    TRẢ VỀ 1 string bắt đầu "ERROR: ...", chứ KHÔNG raise exception. Vì sao?
    Một exception sẽ nổ ngược lên vòng lặp ReAct và GIẾT cả agent giữa chừng.
    Trả ERROR string biến lỗi thành "một quan sát nữa": model đọc nó, hiểu mình
    sai ở đâu, rồi tự sửa ở turn sau. Lỗi trở thành recoverable thay vì fatal.

  Cả hai đều ở src/tools.py THẬT. Lesson này IMPORT chúng và CHỨNG MINH hành vi,
  không tự dựng lại — để bạn tin rằng agent thật cư xử đúng như mô tả.

CHẠY THỬ
  $ python examples/04_sandbox_safety.py
  Phần A + B chạy offline (assert -> luôn deterministic). Phần C gọi model thật
  để cho thấy nó PHỤC HỒI từ 1 ERROR string (bỏ qua êm nếu không có server).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Thêm project root vào sys.path để import được `src` khi chạy như script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# IMPORT trực tiếp lớp an toàn THẬT của repo để demo:
#   _safe_path(path, workspace) -> Path; RAISE ValueError nếu path escape sandbox.
#   execute_tool(name, json_args, workspace) -> str; dispatcher, LUÔN trả string.
from src.tools import _safe_path, execute_tool


# Dựng 1 workspace sandbox để demo. Mọi thao tác file hợp lệ phải nằm trong đây.
WORKSPACE = Path("/tmp/lesson04_ws")
WORKSPACE.mkdir(parents=True, exist_ok=True)
(WORKSPACE / "ok.txt").write_text("i live safely inside the sandbox\n", encoding="utf-8")


def demo_a_safe_path() -> None:
    """TRỤ CỘT 1 — _safe_path cho qua đường dẫn TRONG sandbox, CHẶN đường dẫn ra ngoài."""
    print("=" * 64)
    print("A) SANDBOX — _safe_path confines every file op to the workspace")
    print("=" * 64)

    # (1) Đường dẫn hợp lệ: "ok.txt" nằm trong workspace -> _safe_path trả về
    # đường dẫn tuyệt đối đã resolve, KHÔNG raise.
    good = _safe_path("ok.txt", WORKSPACE)
    print(f"  OK   _safe_path('ok.txt')            -> {good}")
    assert good == (WORKSPACE / "ok.txt")

    # (2) Đường dẫn ĐỘC: "../../../../etc/passwd" cố leo RA NGOÀI workspace.
    # _safe_path resolve nó thành /etc/passwd, thấy nó KHÔNG nằm trong workspace
    # -> RAISE ValueError. Đây là "path traversal attack" kinh điển bị chặn.
    escaped = False
    try:
        _safe_path("../../../../etc/passwd", WORKSPACE)
    except ValueError as e:
        escaped = True
        print(f"  BLOCK _safe_path('../../etc/passwd') -> ValueError: {e}")
    # Nếu KHÔNG raise nghĩa là sandbox thủng — đó là lỗi nghiêm trọng.
    assert escaped, "SECURITY BUG: path escape was NOT blocked!"

    # (3) Vài biến thể tấn công khác cũng phải bị chặn (đường dẫn tuyệt đối,
    # leo nhiều cấp). Đường dẫn tuyệt đối "/etc/hosts" khi nối vào workspace vẫn
    # resolve ra ngoài -> chặn. Ta khẳng định tất cả đều raise.
    for bad in ("/etc/hosts", "../", "../../"):
        try:
            _safe_path(bad, WORKSPACE)
            assert False, f"SECURITY BUG: {bad!r} escaped the sandbox!"
        except ValueError:
            print(f"  BLOCK _safe_path({bad!r}) rejected")

    print("  => Sandbox holds: only paths inside the workspace are allowed.\n")


def demo_b_error_contract() -> None:
    """TRỤ CỘT 2 — execute_tool TRẢ string 'ERROR:' cho mọi lỗi, KHÔNG raise."""
    print("=" * 64)
    print("B) ERROR CONTRACT — tools return 'ERROR:' strings, never raise")
    print("=" * 64)

    # Bốn kiểu hỏng thường gặp. Với MỖI cái, ta khẳng định execute_tool:
    #   (a) KHÔNG raise (nếu raise, dòng assert phía dưới không bao giờ chạy tới),
    #   (b) trả về string bắt đầu "ERROR:" để model đọc và tự sửa.
    cases = [
        # (mô tả, tên tool, arguments-JSON-string)
        ("missing file",
         "read_file", json.dumps({"path": "does_not_exist.txt"})),
        ("path escape (ValueError nuốt thành ERROR string)",
         "read_file", json.dumps({"path": "../../../../etc/passwd"})),
        ("unknown tool name",
         "frobnicate", json.dumps({"x": 1})),
        ("malformed JSON arguments",
         "read_file", "{not valid json"),
        ("bad args (thiếu 'path' bắt buộc)",
         "read_file", json.dumps({"wrong_key": "x"})),
    ]

    for desc, name, args in cases:
        # execute_tool nuốt MỌI exception bên trong (kể cả ValueError từ
        # _safe_path) và biến thành string. Nên dòng này không bao giờ ném ra.
        result = execute_tool(name, args, WORKSPACE)
        oneline = result.splitlines()[0] if result else ""
        print(f"  {desc}:")
        print(f"    -> {oneline}")
        assert result.startswith("ERROR:"), f"expected ERROR string, got: {result!r}"

    # Đối chứng: 1 lời gọi HỢP LỆ trả về NỘI DUNG (không phải ERROR) — để thấy
    # contract chỉ gắn "ERROR:" cho lỗi, còn happy path trả dữ liệu bình thường.
    ok = execute_tool("read_file", json.dumps({"path": "ok.txt"}), WORKSPACE)
    print(f"  valid call:\n    -> {ok.strip()}")
    assert not ok.startswith("ERROR:")
    print("  => Every failure is a readable string the model can recover from.\n")


def demo_c_model_recovers() -> None:
    """Cho thấy ERROR contract có ÍCH: model đọc ERROR rồi TỰ SỬA (cần server).

    Đây là phần "sống": ta cố tình để model gọi sai (file không tồn tại), trả về
    ERROR string, rồi xem nó tự đổi sang đường dẫn đúng ở turn sau. Nếu không có
    vLLM, ta bỏ qua êm — phần A/B đã chứng minh hợp đồng an toàn rồi.
    """
    print("=" * 64)
    print("C) WHY IT MATTERS — the model RECOVERS from an ERROR string")
    print("=" * 64)

    # load_dotenv + client dựng TRONG hàm để phần A/B chạy được kể cả khi thiếu
    # .env / server (lỗi import openai vẫn ở top, nhưng config thì lười ở đây).
    from dotenv import load_dotenv
    from openai import OpenAI, OpenAIError
    from openai.types.chat import ChatCompletionMessageParam
    from src.tools import TOOL_SCHEMAS

    load_dotenv()
    try:
        base_url = os.environ["VLLM_BASE_URL"]
        model = os.environ["VLLM_MODEL_NAME"]
    except KeyError:
        print("  (skipped: VLLM_BASE_URL / VLLM_MODEL_NAME not set)\n")
        return
    client = OpenAI(base_url=base_url, api_key=os.environ.get("VLLM_API_KEY", "not-needed"))

    # Chỉ đưa read_file để câu chuyện gọn. Đáng chú ý: file thật tên "ok.txt",
    # nhưng ta "gài" model nghĩ tên là "okay.txt" để nó gọi trượt lần đầu.
    schemas = [s for s in TOOL_SCHEMAS if s["function"]["name"] == "read_file"]
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content":
            "You have a read_file tool. If a read fails with an ERROR, do not give "
            "up: reconsider the filename and try a corrected path."},
        {"role": "user", "content":
            "Read the file 'okay.txt' and tell me its contents. (Hint: the real file "
            "in this workspace might be named slightly differently — if your first "
            "read errors, try the obvious corrected name.)"},
    ]

    # Vòng lặp ReAct y hệt lesson 03, rút gọn còn 5 turn. Điểm cần NHÌN: turn đầu
    # model đọc 'okay.txt' -> nhận ERROR string -> turn sau nó tự sửa thành
    # 'ok.txt'. KHÔNG có chỗ nào crash; lỗi chỉ là một quan sát.
    try:
        for i in range(1, 6):
            print(f"\n  --- Turn {i} ---")
            resp = client.chat.completions.create(
                model=model, messages=messages, tools=schemas,
                tool_choice="auto", max_tokens=512,
            )
            msg = resp.choices[0].message
            messages.append(msg.model_dump(exclude_none=True))  # type: ignore[arg-type]
            if msg.content:
                print(f"  [assistant] {msg.content.strip()}")
            if not msg.tool_calls:
                break
            for tc in msg.tool_calls:
                result = execute_tool(tc.function.name, tc.function.arguments, WORKSPACE)
                tag = "ERROR" if result.startswith("ERROR:") else "ok"
                print(f"  [tool] {tc.function.name}({tc.function.arguments}) -> [{tag}] {result.strip()}")
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
    except OpenAIError as e:
        print(f"  (skipped: API error: {e})")
        return
    print("\n  => The model turned a failed read into a corrected one — no crash.\n")


def main() -> None:
    demo_a_safe_path()      # offline, deterministic
    demo_b_error_contract() # offline, deterministic
    demo_c_model_recovers() # live (skips cleanly without a server)
    print("Both safety pillars demonstrated. Now read src/tools.py + src/agent.py.")


if __name__ == "__main__":
    main()
