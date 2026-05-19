"""
tools.py — The three tools the agent can call: read_file, write_file, run_bash.

Each tool is a Python function. The OpenAI-compatible API needs them described
as JSON schemas (TOOL_SCHEMAS below) so the model knows their shape. When the
model decides to call a tool, the SDK gives us back the name and a JSON string
of arguments — we route that through `execute_tool()`.

This file has three concerns kept side by side on purpose:
  1. The actual Python functions (what runs).
  2. The OpenAI schema for each (what the model sees).
  3. A single dispatch function `execute_tool()` (the glue).

Design note for the future: Phase 2+ will add more tools. Just append to TOOLS
and TOOL_SCHEMAS — agent.py needs no changes.
"""

from __future__ import annotations

# `json` để parse arguments mà model gửi (model gửi arguments dưới dạng JSON string,
# không phải dict — đây là quy ước của OpenAI tool calling API).
import json

# `logging` thay cho print — consistent với agent.py, có thể redirect ra file.
import logging

# `subprocess` để chạy lệnh shell từ Python. Có timeout, capture stdout/stderr.
import subprocess

# `pathlib.Path` để xử lý đường dẫn an toàn (thay cho string concat dễ lỗi).
from pathlib import Path

log = logging.getLogger(__name__)

# WORKSPACE = "sandbox dir" — giới hạn nơi agent được phép đọc/ghi.
# Mặc định là cwd, nhưng sẽ được set_workspace() override trước khi run_agent().
# Lý do dùng `global`: tools.py không nhận workspace như param mỗi lần gọi —
# nó là state toàn cục để mỗi tool function tự dùng được.
WORKSPACE = Path.cwd()


def set_workspace(path: str | Path) -> None:
    """Pin file operations to a directory. Call this once before run_agent()."""
    global WORKSPACE
    # `.resolve()` = chuyển path tương đối → tuyệt đối + giải symlink.
    # Bắt buộc cho việc check sandbox bên dưới.
    WORKSPACE = Path(path).resolve()
    log.info(f"[tools] workspace = {WORKSPACE}")


def _safe_path(path: str) -> Path:
    """Resolve path relative to WORKSPACE and refuse to escape it.

    Prevents the model from poking around /etc, ~/.ssh, etc.
    Cảnh báo: tên hàm bắt đầu bằng `_` là quy ước Python = "private", chỉ dùng
    nội bộ file này, không nên gọi từ ngoài.
    """
    # Ghép WORKSPACE + path → resolve → đường dẫn tuyệt đối.
    p = (WORKSPACE / path).resolve()

    # Kiểm tra path có nằm trong WORKSPACE không. `p.parents` là list các thư
    # mục cha của p (vd: /a/b/c.txt → /a/b, /a, /). Nếu WORKSPACE KHÔNG nằm
    # trong list cha → p đang ở ngoài sandbox → reject.
    # `p != WORKSPACE` để cho phép case `path = "."` (chính workspace).
    if WORKSPACE not in p.parents and p != WORKSPACE:
        raise ValueError(f"path {p} escapes workspace {WORKSPACE}")
    return p


# ---------------------------------------------------------------------------
# Tool implementations — 3 hàm Python thật sự chạy khi model gọi tool
# ---------------------------------------------------------------------------

def read_file(path: str) -> str:
    """Return the full contents of a text file inside the workspace."""
    # Resolve path qua _safe_path để chắc chắn nằm trong WORKSPACE.
    p = _safe_path(path)

    # Kiểm tra file tồn tại — nếu không, trả về error string (model sẽ thấy).
    # KHÔNG raise exception → vì exception sẽ bubble lên agent.py và crash agent.
    # Trả error string cho model tự đọc và quyết định làm gì tiếp.
    if not p.exists():
        return f"ERROR: file not found: {path}"

    # `errors="replace"` = nếu file có ký tự không decode được, thay bằng "?"
    # thay vì crash. An toàn cho file binary lẫn vào.
    text = p.read_text(encoding="utf-8", errors="replace")
    return text


def write_file(path: str, content: str) -> str:
    """Overwrite (or create) a text file inside the workspace.

    The agent MUST send the full new content — there is no patch/diff format
    in this version. Keep files small for the demo.
    """
    p = _safe_path(path)

    # `mkdir(parents=True, exist_ok=True)` = tạo parent dirs nếu chưa có,
    # không crash nếu đã tồn tại. Cho phép agent tạo file ở subdir mới.
    p.parent.mkdir(parents=True, exist_ok=True)

    # `write_text` overwrite hoàn toàn (không phải append) — agent phải gửi
    # FULL new content. Phase 2 có thể thêm tool patch_file kiểu diff cho hiệu quả.
    p.write_text(content, encoding="utf-8")

    # Trả về 1 chuỗi xác nhận cho model — model biết tool đã hoàn thành.
    return f"wrote {len(content)} chars to {path}"


def run_bash(command: str, timeout: int = 30) -> str:
    """Run a shell command inside the workspace, capturing stdout+stderr."""
    log.info(f"[tools] bash> {command}")
    try:
        # subprocess.run = chạy command đồng bộ, đợi xong mới return.
        # shell=True → command là chuỗi 1 dòng (cho phép pipe, redirect, etc.)
        # cwd=WORKSPACE → CWD của subprocess = workspace, nên `ls` ra files
        # trong demo_repo, không phải project root.
        # capture_output=True → stdout/stderr không in ra terminal, lưu vào result.
        # text=True → stdout/stderr là string thay vì bytes.
        # timeout=30 → giết command sau 30s nếu chưa xong (chống hang infinite).
        result = subprocess.run(
            command,
            shell=True,
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        # Trả error string, không raise. Model đọc string này và quyết định.
        return f"ERROR: command timed out after {timeout}s"

    # Ghép kết quả thành 1 string đẹp cho model đọc: exit code + stdout + stderr.
    parts = [f"exit_code: {result.returncode}"]
    if result.stdout:
        parts.append(f"stdout:\n{result.stdout}")
    if result.stderr:
        parts.append(f"stderr:\n{result.stderr}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Registry + JSON schemas
# ---------------------------------------------------------------------------

# TOOLS dict: name -> Python function. execute_tool() lookup ở đây.
# Phase 2+ có thể thêm new tools vào dict này MÀ KHÔNG cần sửa agent.py.
# Đó là pattern "extensible registry" — design choice quan trọng cho self-evolution.
TOOLS = {
    "read_file": read_file,
    "write_file": write_file,
    "run_bash": run_bash,
}

# TOOL_SCHEMAS: danh sách JSON schema mô tả từng tool cho model.
# Format này là chuẩn OpenAI — cùng schema model GPT-4, Claude, vLLM, Ollama đều hiểu.
# Mỗi schema có:
#   type: "function" (OpenAI define)
#   function:
#     name: tên gọi tool (phải khớp với key trong TOOLS)
#     description: model đọc cái này để hiểu tool dùng vào việc gì
#     parameters: JSON Schema mô tả các tham số (type + required + description)
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the full contents of a text file (path relative to workspace).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to the file."},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Overwrite (or create) a text file with the given content. Send the FULL new file body, not a diff.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to the file."},
                    "content": {"type": "string", "description": "Full new file content."},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_bash",
            "description": "Run a shell command in the workspace. Use for running tests (pytest), listing files (ls), etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute."},
                    "timeout": {"type": "integer", "description": "Seconds before kill (default 30)."},
                },
                "required": ["command"],
            },
        },
    },
]


def execute_tool(name: str, arguments_json: str) -> str:
    """Dispatch a tool call by name with a JSON string of arguments.

    The model gives us `arguments` as a string of JSON (never a dict). We parse,
    look up the function, call it, and stringify the result for the model.
    """
    # 1. Validate tool name. Nếu model gọi tool không tồn tại, trả error string.
    if name not in TOOLS:
        return f"ERROR: unknown tool {name}. Available: {list(TOOLS)}"

    # 2. Parse arguments JSON. Nếu rỗng → dict rỗng (cho tools không args).
    # Nếu malformed JSON → trả error string cho model thấy (model có thể sửa).
    try:
        args = json.loads(arguments_json) if arguments_json else {}
    except json.JSONDecodeError as e:
        return f"ERROR: bad JSON arguments: {e}"

    # 3. Gọi function với args (`**args` = unpack dict thành keyword args).
    # Try/except để bắt mọi exception, convert thành error string.
    # Tại sao? Vì exception trong tool sẽ crash agent.py loop. Mình muốn agent
    # được "thấy" error qua tool result và tự sửa, không crash.
    try:
        result = TOOLS[name](**args)
    except TypeError as e:
        # TypeError thường = sai args (vd thiếu required, hoặc type không đúng).
        return f"ERROR: bad args for {name}: {e}"
    except Exception as e:
        # Catch-all cho mọi loại exception khác (FileNotFoundError, etc.).
        return f"ERROR: {name} crashed: {e}"

    # 4. Stringify result (model chỉ đọc được string, không đọc được Python object).
    return str(result)
