"""
tools.py — The tools the agent can call (read_file, write_file, run_bash, and
the Phase 2 set: apply_patch, multi_edit, grep_files, glob_files, list_dir,
run_python, spawn_subagent).

Each tool is a Python function. The OpenAI-compatible API needs them described
as JSON schemas (TOOL_SCHEMAS below) so the model knows their shape. When the
model decides to call a tool, the SDK gives us back the name and a JSON string
of arguments — we route that through `execute_tool()`.

This file has three concerns kept side by side on purpose:
  1. The actual Python functions (what runs).
  2. The OpenAI schema for each (what the model sees).
  3. A single dispatch function `execute_tool()` (the glue).

Design note: adding an ordinary tool = append the function to TOOLS and its
JSON schema to TOOL_SCHEMAS — agent.py needs no changes (extensible registry
pattern). One exception: `finish` is special-cased by name in run_agent to
terminate the loop.

TRUST MODEL (đọc kỹ trước khi claim "sandbox" ở bất cứ đâu):
  - 7 tool nhận đường dẫn (read_file, write_file, apply_patch, multi_edit,
    grep_files, glob_files, list_dir) đi qua `_safe_path` — sandbox này chống
    TAI NẠN đường dẫn của model (path traversal, ghi nhầm ra ngoài workspace).
  - 3 tool thực thi (run_bash, run_python, spawn_subagent) là FULL-TRUST local
    execution: chỉ bị giới hạn cwd + timeout. Chúng có toàn quyền của user —
    đọc $HOME, gọi mạng, sửa chính src/ của agent qua đường dẫn tuyệt đối.
  - Nói cách khác: sandbox bảo vệ khỏi model VỤNG, không bảo vệ khỏi model
    (hoặc prompt) ÁC Ý. Cô lập thật sự cần container/bwrap — chưa làm ở đây.
"""

# `from __future__ import annotations` — câu lệnh đặc biệt cho Python, bật
# một tính năng mới: cho phép dùng type hint (kiểu dữ liệu) như `Path` trong
# khai báo hàm mà không cần import ở top. Luôn đặt ở dòng đầu tiên của file
# nếu dùng.
from __future__ import annotations

# `import` = "mang thư viện vào". Python có hàng nghìn thư viện sẵn (built-in)
# và hàng triệu thư viện bên ngoài (cài qua pip). Khi import, Python tìm file
# thư viện đó, chạy nó 1 lần, rồi gắn nó vào tên bạn đặt.

# `json` — thư viện xử lý định dạng JSON (JavaScript Object Notation).
# JSON là định dạng văn bản để truyền dữ liệu, ví dụ: {"name": "Alice", "age": 30}
# Model (AI) gửi arguments cho tool dưới dạng chuỗi JSON, không phải dict Python
# thực sự — đây là quy ước của OpenAI tool calling API.
import json

# `logging` — thư viện ghi log (thay cho print). Khác print ở chỗ:
# - Có cấp độ: DEBUG, INFO, WARNING, ERROR
# - Có thể redirect ra file log thay vì màn hình
# - Consistent với cách agent.py đang dùng
import logging

# `subprocess` — thư viện để chạy lệnh shell từ bên trong Python.
# Ví dụ: chạy `ls`, `pytest`, `pip install` như khi gõ trên terminal.
# Có thể đặt timeout (giới hạn thời gian), bắt stdout/stderr (kết quả lệnh).
import subprocess

# `sys` — thư viện truy cập thông tin về chính Python process đang chạy.
# Ở file này chỉ cần `sys.executable`: đường dẫn tuyệt đối đến Python
# interpreter hiện tại (vd `.venv/bin/python`). run_python/spawn_subagent dùng
# nó để spawn subprocess với CÙNG interpreter + libraries — an toàn hơn chữ
# "python" trần (phụ thuộc PATH, có thể trỏ sang version khác ngoài venv).
import sys

# `from pathlib import Path` — từ thư viện pathlib, lấy class Path.
# `class` là "khuôn mẫu" để tạo đối tượng. Path đại diện cho đường dẫn file/thư mục.
# Dùng Path thay cho string nối tay (`"/home/user" + "/" + "file.txt"`) vì:
# - An toàn hơn (tự xử lý "/" trên Linux vs "\" trên Windows)
# - Có nhiều method tiện lợi: .exists(), .read_text(), .write_text(), .parent, ...
from pathlib import Path

# `logging.getLogger(__name__)` — tạo một "logger" riêng cho file này.
# `__name__` là biến đặc biệt của Python, chứa tên module hiện tại
# (vd: "src.tools"). Mỗi module có logger riêng để biết log đến từ đâu.
# Kết quả gán vào biến `log` — ta sẽ gọi log.info(...) để ghi thông tin.
log = logging.getLogger(__name__)

# workspace = "sandbox dir" — giới hạn nơi agent được phép đọc/ghi.
# KHÔNG còn là global nữa: mỗi tool function nhận `workspace: Path` như tham số
# keyword-only, và execute_tool() inject nó vào mỗi call. Lý do bỏ global:
# state toàn cục khiến import có side-effect + không an toàn khi nhiều agent
# (vd subagent) chạy với workspace khác nhau trong cùng process.


# `def` = "define" = định nghĩa hàm. Hàm là khối code có tên, nhận tham số,
# chạy khi được gọi, có thể trả về giá trị.
# Cú pháp: def tên_hàm(tham_số_1: kiểu, tham_số_2: kiểu) -> kiểu_trả_về:
# Phần sau `:` (dấu hai chấm) là "type hint" — gợi ý kiểu dữ liệu, không bắt buộc
# nhưng giúp đọc code dễ hơn. Python không tự kiểm tra type hint lúc chạy.
def _safe_path(path: str, workspace: Path) -> Path:
    """Resolve path relative to `workspace` and refuse to escape it.

    Prevents the model from poking around /etc, ~/.ssh, etc.
    Cảnh báo: tên hàm bắt đầu bằng `_` là quy ước Python = "private", chỉ dùng
    nội bộ file này, không nên gọi từ ngoài.
    `workspace` được truyền vào (positional) thay cho global cũ — caller (mỗi
    tool function) đã có sẵn workspace từ keyword arg của nó.
    """
    # Resolve workspace NGAY TẠI ĐÂY: check `in p.parents` bên dưới chỉ đúng khi
    # cả hai vế đã chuẩn hóa — không tin caller đã resolve sẵn (precondition ngầm
    # xuyên file là chỗ dễ vỡ nhất của security kernel).
    workspace = workspace.resolve()

    # `workspace / path` — toán tử `/` với Path KHÔNG phải chia số.
    # Path ghi đè (override) toán tử `/` để có nghĩa là "nối đường dẫn".
    # Ví dụ: Path("/home/user") / "docs/file.txt"  →  Path("/home/user/docs/file.txt")
    # Đây gọi là "operator overloading" trong Python — class tự định nghĩa lại
    # hành vi của toán tử.
    #
    # `.resolve()` — method của Path, chuyển đường dẫn sang dạng tuyệt đối thực sự:
    # - Giải quyết `..` (lên thư mục cha): "/a/b/../c" → "/a/c"
    # - Giải quyết symlink (liên kết tượng trưng): đi theo link đến đích thật
    # - Kết quả luôn bắt đầu bằng "/" (tuyệt đối, không phải tương đối)
    # Tại sao cần resolve()? Vì model có thể gửi path như "../../etc/passwd" —
    # nếu không resolve, kiểm tra `in p.parents` sẽ bị qua mặt.
    p = (workspace / path).resolve()

    # `if` = "nếu". Cú pháp: if điều_kiện: (thụt lề) khối_code_nếu_đúng
    # Nếu điều kiện SAI (False), Python bỏ qua khối thụt lề và đi tiếp.
    #
    # `p.parents` — thuộc tính của Path, trả về tất cả thư mục cha của p.
    # Ví dụ: Path("/a/b/c.txt").parents  →  [Path("/a/b"), Path("/a"), Path("/")]
    # Đây là một iterable (có thể lặp qua), không phải list thực sự, nhưng `in`
    # vẫn hoạt động (Python kiểm tra từng phần tử).
    #
    # `workspace not in p.parents` — kiểm tra workspace có KHÔNG nằm trong danh
    # sách thư mục cha của p không.
    # Nếu p = /workspace/subdir/file.txt → parents = [/workspace/subdir, /workspace, /]
    # → workspace CÓ trong parents → check này PASS (False) → không raise
    # Nếu p = /etc/passwd → parents = [/etc, /] → workspace KHÔNG trong parents
    # → check này FAIL (True) → raise ValueError
    #
    # `p != workspace` — cho phép trường hợp path = "." tức p chính là workspace.
    # Trong trường hợp đó, workspace không trong parents (bởi vì parents không bao
    # gồm chính nó), nhưng p == workspace → điều kiện toàn phần là False → OK.
    if workspace not in p.parents and p != workspace:
        # `raise ValueError(...)` — "ném" (throw) ra một ngoại lệ (exception).
        # `ValueError` là loại exception chuẩn của Python: "giá trị không hợp lệ".
        # `raise` dừng hàm ngay lập tức và báo lỗi lên caller.
        # f"..." là f-string: chuỗi có thể nhúng biểu thức Python vào giữa {}.
        # {p} và {workspace} sẽ được thay bằng giá trị thực của biến đó.
        raise ValueError(f"path {p} escapes workspace {workspace}")

    # `return` — trả về giá trị từ hàm. Sau dòng này hàm kết thúc.
    # Caller sẽ nhận được Path object p.
    return p


def _cap(text: str, max_chars: int, *, tail: bool = False) -> str:
    """Cắt `text` nếu dài quá `max_chars`, kèm marker nói rõ đã mất bao nhiêu.

    TẠI SAO PHẢI CAP: model chỉ có 32K context. Một read_file trên file lớn,
    hay một `pytest -v` lắm lời, hiện đổ NGUYÊN VĂN vào context — turn kế tiếp
    vượt 32K và cả run chết với finish_reason="api_error". Cap ở tầng tool là
    chốt chặn cuối cùng: thà model thấy "[truncated]" rồi tự đọc đúng khúc cần,
    còn hơn chết cả run.

    tail=False (mặc định): giữ ĐẦU — hợp với nội dung file (imports/signatures
    nằm đầu). Marker nối vào CUỐI phần giữ lại.
    tail=True: giữ CUỐI — hợp với output lệnh (error + summary của pytest nằm
    cuối). Marker đứng TRƯỚC phần giữ lại để model thấy ngay là đã bị cắt đầu.
    """
    if len(text) <= max_chars:
        return text
    # Số ký tự bị vứt — báo trong marker để model ước được phần thiếu lớn cỡ nào.
    dropped = len(text) - max_chars
    if tail:
        return f"...[truncated {dropped} chars]\n" + text[-max_chars:]
    return text[:max_chars] + f"\n...[truncated {dropped} chars]"


def _run_captured(cmd, *, cwd: Path, timeout: int, shell: bool = False) -> str:
    """Chạy subprocess + format kết quả — phần ruột chung của run_bash/run_python.

    Trước đây hai tool đó chép tay cùng một khối subprocess.run + format
    exit_code/stdout/stderr — giờ sống MỘT chỗ ở đây.

    Các tham số subprocess.run (giải thích chung cho cả 2 tool):
      - `cmd` — string (khi shell=True, vd "ls -la | head") hoặc list args
        (khi shell=False, vd [python, "-c", code]). List args không qua shell
        parsing → không có shell injection; string + shell=True thì hỗ trợ
        pipe (|), redirect (>), &&, $VAR, wildcard... nhưng chạy full quyền user.
      - `cwd=cwd` — đặt "current working directory" cho subprocess. KHÔNG phải
        sandbox: lệnh vẫn với tới đường dẫn tuyệt đối, $HOME, mạng (TRUST MODEL).
      - `capture_output=True` — bắt stdout/stderr vào result, không in ra terminal.
      - `text=True` — tự decode bytes → str.
      - `timeout=timeout` — giết subprocess sau N giây nếu chưa xong, để lệnh
        hang không block agent mãi mãi.
    """
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        # Trước đây timeout vứt sạch output — model mù tịt lệnh chết ở đâu.
        # TimeoutExpired vẫn mang stdout/stderr thu được TRƯỚC khi bị kill;
        # trả lại phần đó (capped) để model debug. Gotcha CPython: e.stdout /
        # e.stderr là BYTES kể cả khi đã đặt text=True — phải tự decode.
        parts = [f"ERROR: command timed out after {timeout}s"]
        for label, raw in (("stdout", e.stdout), ("stderr", e.stderr)):
            if not raw:
                continue
            partial = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
            parts.append(f"{label} (partial):\n" + _cap(partial, 20000, tail=True))
        return "\n".join(parts)

    # Format: 3 sections (exit_code, stdout, stderr) — 1 format chung để model
    # học 1 lần dùng cho cả run_bash lẫn run_python. Section rỗng thì bỏ.
    # Mỗi stream cap 20K chars GIỮ CUỐI (tail=True) — với pytest/build, error
    # và summary nằm ở cuối; đầu output là phần ít giá trị nhất khi phải cắt.
    parts = [f"exit_code: {result.returncode}"]
    if result.stdout:
        parts.append("stdout:\n" + _cap(result.stdout, 20000, tail=True))
    if result.stderr:
        # stderr có thể chứa Python tracebacks — rất quan trọng để debug.
        parts.append("stderr:\n" + _cap(result.stderr, 20000, tail=True))
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Tool implementations — các hàm Python thật sự chạy khi model gọi tool
# ---------------------------------------------------------------------------

# `*` trong danh sách tham số: mọi tham số SAU dấu `*` phải được gọi theo tên
# (keyword argument), không thể truyền theo vị trí. Ví dụ:
#   read_file("myfile.txt", workspace=my_workspace)  ← đúng
#   read_file("myfile.txt", my_workspace)             ← lỗi
# Tại sao? Vì `workspace` là tham số "nội bộ" — model không bao giờ gửi nó,
# chỉ execute_tool() mới inject. Dấu `*` làm rõ sự phân biệt đó.
def read_file(path: str, *, workspace: Path) -> str:
    """Return the contents of a text file inside the workspace (capped at 40K chars)."""
    # Gọi hàm _safe_path để kiểm tra và chuyển đổi path.
    # Kết quả là một Path object tuyệt đối, đã được xác nhận nằm trong workspace.
    # Nếu path thoát khỏi workspace, _safe_path sẽ raise ValueError — ngoại lệ
    # đó sẽ bubble lên execute_tool() và được bắt ở đó, convert thành error string.
    p = _safe_path(path, workspace)

    # `p.exists()` — method của Path, trả về True nếu file/thư mục tồn tại,
    # False nếu không. Dấu `not` đảo ngược: `not p.exists()` = "nếu KHÔNG tồn tại".
    # KHÔNG raise exception → vì exception sẽ bubble lên agent.py và crash agent.
    # Trả error string cho model tự đọc và quyết định làm gì tiếp.
    if not p.exists():
        # f-string: {path} được thay bằng giá trị biến `path`.
        return f"ERROR: file not found: {path}"

    # `p.read_text(encoding="utf-8", errors="replace")` — method của Path,
    # đọc toàn bộ nội dung file và trả về string.
    # `encoding="utf-8"` — dùng bảng mã UTF-8 để giải mã byte thành ký tự.
    #   UTF-8 là chuẩn phổ biến nhất, hỗ trợ tiếng Việt, tiếng Trung, emoji,...
    # `errors="replace"` — nếu gặp byte KHÔNG hợp lệ trong UTF-8 (ví dụ file binary
    #   bị lẫn vào), thay bằng ký tự "?" thay vì crash toàn bộ hàm.
    #   Lựa chọn an toàn cho môi trường sandbox không kiểm soát được file type.
    text = p.read_text(encoding="utf-8", errors="replace")

    # Cap 40K chars (~10K tokens) — file lớn hơn sẽ nuốt trọn 32K context trong
    # 1 turn và giết cả run (xem _cap). Giữ ĐẦU file: imports/signatures nằm đó;
    # cần khúc sau thì model dùng grep_files định vị rồi đọc có chủ đích.
    return _cap(text, 40000)


def write_file(path: str, content: str, *, workspace: Path) -> str:
    """Overwrite (or create) a text file inside the workspace.

    The agent MUST send the full new content — there is no patch/diff format
    in this version. Keep files small for the demo.
    """
    # Sandbox check — xem _safe_path ở trên để hiểu tại sao.
    p = _safe_path(path, workspace)

    # `p.parent` — thuộc tính của Path, trả về thư mục chứa file.
    # Ví dụ: Path("/a/b/c.txt").parent  →  Path("/a/b")
    #
    # `.mkdir(parents=True, exist_ok=True)` — tạo thư mục.
    # `parents=True` — tạo tất cả thư mục cha nếu chưa có.
    #   Ví dụ: p = "/ws/new/deep/file.txt", nếu "/ws/new/deep/" chưa tồn tại,
    #   Python sẽ tạo luôn "new/" rồi "deep/" trong đó thay vì báo lỗi.
    # `exist_ok=True` — không báo lỗi nếu thư mục đã tồn tại.
    #   Không có flag này: nếu thư mục đã có → FileExistsError.
    #   Với flag này: bỏ qua silently. An toàn để gọi nhiều lần.
    p.parent.mkdir(parents=True, exist_ok=True)

    # `p.write_text(content, encoding="utf-8")` — ghi chuỗi `content` vào file.
    # OVERWRITE hoàn toàn — nội dung cũ bị xóa, thay bằng `content`.
    # Không có chế độ append (nối vào cuối) ở đây — agent phải gửi FULL content.
    # Phase 2 có thể thêm tool patch_file kiểu diff cho hiệu quả hơn.
    p.write_text(content, encoding="utf-8")

    # `len(content)` — hàm built-in của Python, đếm số ký tự (characters) trong
    # chuỗi `content`. Ví dụ: len("hello") = 5.
    # Trả về chuỗi xác nhận cho model — model biết tool đã hoàn thành.
    return f"wrote {len(content)} chars to {path}"


def run_bash(command: str, timeout: int = 600, *, workspace: Path) -> str:
    """Run a shell command with cwd=workspace, capturing stdout+stderr.

    Default timeout 600s (10 phút) — đủ cho pytest, pip install, build nhỏ.
    Nếu cần lâu hơn, model có thể tự pass `timeout` lớn hơn (có trong JSON schema).

    `shell=True` — command đi qua shell (/bin/sh) để hỗ trợ pipe (|), redirect
    (>), &&, $VAR, wildcard... Trade-off CÓ THẬT: command của model chạy với
    toàn quyền user. Chấp nhận vì đây là máy local của mình + workload là eval
    tasks; KHÔNG claim "sandboxed bash" ở docs.

    TRUST: tool này KHÔNG bị _safe_path sandbox — `cwd` chỉ đặt thư mục làm
    việc mặc định, không ngăn lệnh chạm vào đường dẫn tuyệt đối, $HOME, hay
    mạng. Xem TRUST MODEL ở docstring đầu file.
    """
    # `log.info(...)` — ghi một dòng log cấp INFO để developer thấy mỗi lệnh
    # bash nào được chạy trong console (Rule C: verbose by default).
    log.info(f"[tools] bash> {command}")

    # Ruột subprocess + format exit_code/stdout/stderr + cap output nằm ở
    # _run_captured (dùng chung với run_python) — xem comment ở đó.
    return _run_captured(command, cwd=workspace, timeout=timeout, shell=True)


# ---------------------------------------------------------------------------
# Phase 2 tools — surgical edits, search, sub-agent, exec
# ---------------------------------------------------------------------------

def apply_patch(path: str, old_text: str, new_text: str, *, workspace: Path) -> str:
    """Surgical search-and-replace edit. `old_text` PHẢI xuất hiện CHÍNH XÁC 1 LẦN.

    DESIGN RATIONALE:
      Đây là tool chính cho mọi edit nhỏ (1-10 dòng) — tránh dùng write_file để
      ghi đè cả file (tốn token + dễ corrupt file lớn). Pattern giống Claude
      Code's Edit tool: đơn giản hơn unified-diff, không cần parse hunks,
      không cần line-number tracking. Trade-off: model phải gửi đúng bytes
      (kể cả whitespace), không tolerate fuzzy match.

    UNIQUENESS CONSTRAINT:
      `old_text` phải xuất hiện CHÍNH XÁC 1 LẦN. Tại sao?
      - 0 lần: không có gì để replace → error, model phải read lại file
      - >1 lần: ambiguous — không biết replace cái nào → error, model phải
                mở rộng context (thêm dòng xung quanh) để unique-ify.
      Đây là safety property: không cho phép "blind replace all" để tránh
      sửa nhầm 1 occurrence trong khi muốn sửa khác.

    IMPLEMENTATION — delegate xuống multi_edit:
      apply_patch chính là multi_edit với danh sách đúng 1 edit. Trước đây hai
      tool chép tay cùng một core replace-unique và đã DRIFT (error message
      khác nhau, hint "Read the file" chỉ 1 bên có). Giờ logic sống MỘT chỗ —
      sandbox check, uniqueness check, error contract "ERROR: ..." và tính
      atomic (không ghi đĩa khi fail) thừa hưởng nguyên vẹn từ multi_edit.
      Giữ cả 2 tên tool vì interface với model (TOOL_SCHEMAS) không đổi:
      apply_patch vẫn là dạng gọn cho 1 edit (đỡ nesting JSON).
    """
    return multi_edit(path, [{"old_text": old_text, "new_text": new_text}],
                      workspace=workspace)


def multi_edit(path: str, edits: list, *, workspace: Path) -> str:
    """Apply MULTIPLE edits to ONE file atomically (all-or-nothing).

    SIGNATURE:
      edits = [{"old_text": "...", "new_text": "..."}, {...}, ...]

    Đây là NƠI DUY NHẤT chứa core replace-unique — apply_patch chỉ là wrapper
    gọi xuống đây với list 1 edit (xem docstring apply_patch).

    DESIGN RATIONALE — tại sao không gọi apply_patch nhiều lần?
      1. Atomicity: nếu edit #3 fail, không muốn edit #1 và #2 đã commit lên đĩa
         (file bị partial-edit không recoverable từ model perspective).
      2. Efficiency: 1 read + 1 write thay vì N reads + N writes (disk I/O đắt).
      3. Sequential dependencies: edit #2 có thể tìm text mà chỉ tồn tại SAU
         khi edit #1 đã apply. Multi_edit honor order.

    GOTCHA — sequential apply, NOT parallel:
      Edits apply theo thứ tự. Nếu edit #1 thay "foo" → "bar" và edit #2 thay
      "bar" → "baz", kết quả cuối là "baz" (không phải "bar"). Model phải
      hiểu order matters. Cẩn thận khi edits có overlapping content.

    ATOMICITY MECHANISM:
      Đọc file 1 lần vào memory → apply tuần tự lên biến `content` (string)
      → write 1 lần ra đĩa. Nếu bất kỳ edit nào fail uniqueness check,
      return error TRƯỚC KHI write — file gốc trên đĩa không bị động.
    """
    # Sandbox check — same pattern as apply_patch.
    p = _safe_path(path, workspace)
    if not p.exists():
        return f"ERROR: file not found: {path}"

    # `isinstance(edits, list)` — hàm built-in kiểm tra kiểu dữ liệu.
    # Trả về True nếu `edits` là một list, False nếu không.
    # `not isinstance(edits, list)` = "nếu edits KHÔNG phải list".
    # `or not edits` — `or` là "hoặc". `not edits` = "edits rỗng" (list rỗng là falsy).
    # Defensive type check — model có thể emit edits dạng dict thay vì list,
    # hoặc list rỗng (no-op should be explicit error, not silent success).
    if not isinstance(edits, list) or not edits:
        return "ERROR: edits must be a non-empty list of {old_text, new_text}"

    # Read 1 lần. Tất cả replace ops sẽ chạy trên biến `content` (in-memory).
    content = p.read_text(encoding="utf-8", errors="replace")

    # Lưu độ dài ban đầu của file để báo cáo khi thành công.
    # `len(content)` đếm số ký tự trong chuỗi `content`.
    original_len = len(content)

    # `for i, edit in enumerate(edits, 1):` — vòng lặp "for" duyệt qua từng phần tử.
    # Cú pháp cơ bản: `for biến in iterable:` — lặp qua từng item, gán vào `biến`.
    # `enumerate(edits, 1)` — bọc list edits lại, trả về cặp (số_thứ_tự, phần_tử).
    #   Tham số `1` = bắt đầu đếm từ 1 (thay vì 0 mặc định của Python).
    #   Mỗi lần lặp: `i` = số thứ tự (1, 2, 3,...), `edit` = phần tử tương ứng.
    # `i, edit` — "tuple unpacking": Python tự tách cặp (i, edit) ra thành 2 biến.
    for i, edit in enumerate(edits, 1):
        # Defensive: từng edit phải là dict (model có thể emit list/string nhầm).
        # `dict` là kiểu dữ liệu "từ điển" trong Python: ánh xạ key → value.
        # Ví dụ: {"old_text": "foo", "new_text": "bar"} là dict.
        if not isinstance(edit, dict):
            return f"ERROR: edit #{i} not a dict (file not modified)"

        # `edit.get("old_text", "")` — method của dict, lấy giá trị theo key.
        # Nếu key `"old_text"` TỒN TẠI trong dict → trả về giá trị đó.
        # Nếu key KHÔNG tồn tại → trả về giá trị mặc định `""` (chuỗi rỗng).
        # An toàn hơn `edit["old_text"]` vì cái sau raise KeyError nếu thiếu key.
        # Validation sẽ xảy ra ngay sau (empty old_text → error).
        old = edit.get("old_text", "")
        new = edit.get("new_text", "")

        # `not old` — chuỗi rỗng "" là "falsy" trong Python, nên `not old` = True
        # khi old là chuỗi rỗng hoặc None. Empty old_text = invalid (không có gì để search).
        # Note: empty new_text vẫn OK — đó là delete operation hợp lệ.
        if not old:
            return f"ERROR: edit #{i} has empty old_text (file not modified)"

        # Uniqueness check — đây là core replace-unique DÙNG CHUNG (apply_patch
        # delegate vào đây) nhưng chạy trên `content` đã bị mutate bởi các edit
        # trước. Đây là điểm "sequential" quan trọng: edit #2 search trên kết
        # quả của edit #1, không phải file gốc.
        count = content.count(old)
        # CASE 0: không tìm thấy. Lý do thường gặp: model nhớ sai bytes (thiếu
        # indent, sai whitespace) hoặc file đã bị sửa bởi tool call trước →
        # model có stale view. Hint "Read the file" (trước đây chỉ apply_patch
        # có) giờ nằm ở core chung nên CẢ HAI tool đều coach model refresh.
        if count == 0:
            return (f"ERROR: edit #{i}: old_text not found in {path} "
                    "(file not modified). Read the file to get exact bytes.")
        # CASE >1: ambiguous match — yêu cầu model expand context để unique-ify.
        if count > 1:
            return (f"ERROR: edit #{i}: old_text matches {count} places in {path} "
                    "(file not modified). Add more context (surrounding lines) "
                    "to make it unique.")

        # `content = content.replace(old, new, 1)` — tạo chuỗi MỚI với old thay bằng new.
        # Lưu ý kỹ thuật: string trong Python là IMMUTABLE (bất biến) — không thể
        # sửa trực tiếp. `str.replace` trả về chuỗi MỚI, không sửa chuỗi gốc.
        # `content = ...` gán chuỗi mới vào lại biến `content` (ghi đè tham chiếu cũ).
        # NẾU loop break sau dòng này do edit sau fail, `content` đã chứa partial edits,
        # NHƯNG ta CHƯA write ra đĩa — atomicity preserved (file gốc an toàn).
        content = content.replace(old, new, 1)

    # Reach here = tất cả edits passed uniqueness check (vòng for không bị return sớm).
    # Commit 1 lần ra đĩa — đây là điểm duy nhất file vật lý bị thay đổi.
    p.write_text(content, encoding="utf-8")

    # `len(edits)` — số phần tử trong list edits.
    # Success: report số edits + size delta.
    return f"applied {len(edits)} edits to {path} ({original_len} → {len(content)} chars)"


def grep_files(pattern: str, path: str = ".", file_glob: str = "", *, workspace: Path) -> str:
    """Regex search trong workspace. Output capped tại 50 dòng match.

    PARAMS:
      pattern: regex extended POSIX (flag `-E`). Hỗ trợ `|`, `+`, `?`, `()`.
      path: thư mục bắt đầu (relative to workspace). Default "." = whole repo.
      file_glob: optional shell glob ('*.py') giới hạn file scan. Không default
                 vì grep `--include` với empty string match nothing.

    DESIGN RATIONALE — tại sao không dùng Python re.compile + Path.rglob?
      1. Performance: GNU grep được optimize cho text scan, nhanh hơn Python
         loop 10-100x trên file lớn.
      2. Regex syntax: model quen với POSIX/PCRE regex hơn Python re flavor.
      3. Output format: `path:lineno:line` chuẩn — model parse dễ.
      Trade-off: phụ thuộc vào hệ thống có `grep` (mọi Linux/Mac có).

    WHY NOT run_bash("grep ..."):
      Quote-escaping. Model phải double-escape regex chars trong JSON.
      Vd pattern `def foo` qua run_bash cần `\"def foo\"`. Tool này tránh
      tầng quote thứ 2 — args đi thẳng vào subprocess.run as list elements.

    OUTPUT FORMAT:
      Mỗi line: `relative/path:line_number:matched_line`
      Truncated ở 50 lines + suffix "[truncated, N more]" để giữ context budget.
    """
    # Sandbox: path phải nằm trong workspace.
    p = _safe_path(path, workspace)
    if not p.exists():
        return f"ERROR: path not found: {path}"

    # `cmd = [...]` — list chứa các phần của câu lệnh shell.
    # Khi truyền list (không phải string) cho subprocess.run, mỗi phần tử là
    # một argument riêng — tránh shell parsing, an toàn hơn với ký tự đặc biệt.
    # Flags grep:
    #   -r = recursive (duyệt qua tất cả subdirectory)
    #   -n = in số dòng kèm theo mỗi match (ví dụ: "file.py:42:def foo")
    #   -E = Extended Regex: cho phép dùng +, ?, |, () không cần backslash
    #   --exclude-dir = bỏ qua thư mục máy-sinh: match trong .git objects /
    #     .venv site-packages / __pycache__ chỉ là noise — nuốt mất budget
    #     50 dòng mà không bao giờ là code model cần sửa.
    cmd = ["grep", "-rnE",
           "--exclude-dir=.git", "--exclude-dir=.venv", "--exclude-dir=__pycache__"]

    # `if file_glob:` — True nếu file_glob không rỗng (khác "" và None).
    # `cmd.extend([...])` — thêm nhiều phần tử vào cuối list `cmd`.
    #   Khác `.append()` (thêm 1 phần tử) — extend "trải phẳng" list được truyền vào.
    #   Ví dụ: [1,2].extend([3,4])  →  [1,2,3,4]  (không phải [1,2,[3,4]])
    # --include filter chỉ scan file matching glob. Truyền RIÊNG (không gộp
    # vào pattern) vì grep `--include=*.py` vs `--include *.py` cùng work.
    # Nếu file_glob rỗng, BỎ flag — không pass --include "" (sẽ match nothing).
    if file_glob:
        cmd.extend(["--include", file_glob])

    # `p.relative_to(workspace)` — tính đường dẫn TƯƠNG ĐỐI của p so với workspace.
    # Ví dụ: p = Path("/ws/src/tools.py"), workspace = Path("/ws")
    #   → p.relative_to(workspace) = Path("src/tools.py")
    # Lý do dùng relative: nếu pass absolute str(p), grep in ra absolute path trong
    # mỗi dòng match — noisy và khó tái sử dụng trong các tool call sau.
    rel = p.relative_to(workspace)
    # `str(rel)` — chuyển Path object thành string thông thường.
    # `if str(rel) != "." else "."` — toán tử ternary của Python:
    #   value_if_true if condition else value_if_false
    #   Tương đương: if str(rel) != ".": target = str(rel) else: target = "."
    target = str(rel) if str(rel) != "." else "."

    # `--` separator — quy ước POSIX: mọi argument sau `--` là operand (tên file/dir),
    # không phải option flag. Phòng trường hợp pattern bắt đầu bằng `-` (ví dụ "-foo")
    # bị grep hiểu nhầm là flag.
    # `cmd.extend(["--", pattern, target])` thêm 3 phần tử cuối vào cmd:
    #   ["grep", "-rnE", "--include", "*.py", "--", "def foo", "src/"]
    cmd.extend(["--", pattern, target])

    # Subprocess với timeout = 30s. Grep với regex evil có thể gây
    # ReDoS (catastrophic backtracking) nhưng 30s đủ để fail-safe.
    # cwd=workspace để grep emit path relative to workspace.
    try:
        result = subprocess.run(cmd, cwd=workspace, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        return "ERROR: grep timed out after 30s"

    # Grep exit codes (quy ước POSIX):
    #   0 = ít nhất 1 match được tìm thấy
    #   1 = không có match nào (KHÔNG phải lỗi — grep báo "không tìm thấy" qua exit code)
    #   2 = lỗi thật sự (regex không hợp lệ, permission denied, ...)
    if result.returncode == 1:
        return f"no matches for pattern: {pattern}"
    if result.returncode != 0:
        # `result.stderr.strip()` — `strip()` là method của string, xóa whitespace
        # (space, tab, newline) ở đầu và cuối chuỗi. Làm sạch error message.
        return f"ERROR: grep failed (exit {result.returncode}): {result.stderr.strip()}"

    # `result.stdout.splitlines()` — method của string, tách chuỗi thành list các dòng.
    # `splitlines()` xử lý được cả \n (Unix), \r\n (Windows), \r (old Mac) —
    # robust hơn `.split("\n")` chỉ xử lý được Unix newline.
    # Ví dụ: "a\nb\nc".splitlines()  →  ["a", "b", "c"]
    lines = result.stdout.splitlines()

    # Truncation: 50 lines là sweet spot — đủ context cho model nhưng không
    # blow up token budget (50 lines × ~80 chars ≈ 4K tokens typical case).
    # `len(lines) > 50` — True nếu có nhiều hơn 50 dòng.
    if len(lines) > 50:
        # `lines[:50]` — "slice" của list: lấy các phần tử từ index 0 đến 49 (không gồm 50).
        # Cú pháp slice: list[start:stop] — start (inclusive), stop (exclusive).
        # Ví dụ: [1,2,3,4,5][:3]  →  [1,2,3]
        out = "\n".join(lines[:50]) + f"\n... [truncated, {len(lines) - 50} more matches]"
    else:
        # `lines if lines else "no matches"` — toán tử ternary:
        # Nếu lines không rỗng: dùng lines. Nếu rỗng: trả về "no matches".
        # Empty stdout với exit 0 cực kỳ rare nhưng handle defensive.
        out = "\n".join(lines) if lines else "no matches"

    # Chốt chặn KÝ TỰ sau line cap: 50 dòng match trong file minified/log vẫn
    # có thể dài hàng trăm KB — _cap giữ ĐẦU (match đầu thường relevant nhất).
    return _cap(out, 20000)


def glob_files(pattern: str, path: str = ".", *, workspace: Path) -> str:
    """List files matching shell-glob pattern. Use ** for recursive.

    EXAMPLES:
      pattern='*.md', path='.'       → top-level markdown files only
      pattern='**/*.py', path='.'    → mọi Python file recursively
      pattern='src/**/*test*'        → file có 'test' trong tên dưới src/
      pattern='[A-Z]*.py'            → Python file bắt đầu bằng uppercase

    GLOB vs GREP — khi nào dùng cái nào?
      glob_files: tìm FILE theo TÊN/PATH pattern (cheap, không đọc content)
      grep_files: tìm DÒNG theo CONTENT regex (đắt hơn, scan body)
      Typical workflow: glob_files để locate candidate files, sau đó grep_files
      hoặc read_file vào từng cái.

    PATHLIB.GLOB BEHAVIOR:
      - `*` match 1 segment (không cross `/`)
      - `**` match nhiều segment (cần `pathlib` Python 3.5+)
      - `?` match 1 char
      - `[abc]` character class
      Lưu ý: khác `glob` module, `pathlib.Path.glob` CÓ match file ẩn —
      `*.py` match cả `.hidden.py`, và `**/*.py` đi vào cả `.git/`.

    OUTPUT: relative path đến workspace, 1/line, truncated tại 50.
    """
    # Sandbox check — `path` là điểm bắt đầu glob, không phải pattern.
    p = _safe_path(path, workspace)
    if not p.exists():
        return f"ERROR: path not found: {path}"

    # `p.glob(pattern)` — method của Path, trả về generator các Path objects khớp pattern.
    # Generator là kiểu đặc biệt: lazily computed (tính từng phần tử khi cần),
    # không load hết vào memory cùng lúc. Tốt cho thư mục lớn.
    #
    # `sorted(...)` — hàm built-in, nhận bất kỳ iterable (kể cả generator) và
    # trả về LIST đã sắp xếp theo thứ tự. Cụ thể, Path được so sánh theo string
    # đường dẫn → sắp xếp alphabetical. Output deterministic (không phụ thuộc OS).
    #
    # `try/except Exception as e:` — bắt MỌI loại exception (vì `Exception` là
    # base class của hầu hết exception trong Python). Glob pattern xấu (vd "[abc")
    # thiếu dấu "]") có thể raise ValueError hoặc OSError tùy Python version.
    # `as e` — gán exception object vào biến `e` để in ra message lỗi.
    try:
        matches = sorted(p.glob(pattern))
    except Exception as e:
        return f"ERROR: invalid glob pattern: {e}"

    # `not matches` — list rỗng là falsy, nên `not matches` = True nếu không có match.
    if not matches:
        return f"no files match {pattern} in {path}"

    # `rel = []` — tạo list rỗng để chứa đường dẫn tương đối.
    rel = []

    # `for m in matches:` — vòng lặp qua từng Path object trong list `matches`.
    for m in matches:
        # Bao từng lần gọi relative_to trong try/except riêng vì có thể fail
        # nếu m nằm ngoài workspace (hiếm nhưng phòng thủ).
        try:
            # `m.relative_to(workspace)` — tính đường dẫn tương đối so với workspace.
            # `str(...)` — chuyển Path object thành string thông thường.
            # `rel.append(...)` — thêm string này vào cuối list `rel`.
            rel.append(str(m.relative_to(workspace)))
        except ValueError:
            # `relative_to` raises ValueError nếu m không phải descendant của workspace.
            # Defensive — không nên trigger trong practice vì _safe_path đã check.
            # Fallback: dùng absolute path string thay vì relative.
            rel.append(str(m))

    # Cùng line cap 50 như grep_files — sweet spot cho token budget. Không cần
    # thêm _cap ký tự ở đây: mỗi entry chỉ là 1 path ngắn, không phải dòng code.
    if len(rel) > 50:
        return "\n".join(rel[:50]) + f"\n... [truncated, {len(rel) - 50} more]"

    # `"\n".join(rel)` — ghép tất cả đường dẫn thành chuỗi, mỗi đường dẫn 1 dòng.
    return "\n".join(rel)


def list_dir(path: str = ".", *, workspace: Path) -> str:
    """Liệt kê nội dung thư mục — sạch hơn run_bash('ls -la').

    OUTPUT FORMAT:
      path/
        dir   subdir1/
        dir   subdir2/
        file  foo.py  (724 bytes)
        file  README.md  (2048 bytes)

    DESIGN RATIONALE — tại sao có cả glob_files mà vẫn cần list_dir?
      list_dir tốt cho ORIENTATION ("repo này có gì?") — non-recursive,
      shows both files AND directories với size.
      glob_files tốt cho SEARCH ("tìm file matching X") — có pattern.
      Workflow: list_dir để xem layout, sau đó glob_files/read_file targeted.

    HIDDEN FILES (dot-prefix):
      Skip mặc định để output gọn — repo nhiều khi có .git/, .venv/, .pytest_cache/
      làm noisy. Nếu model thực sự cần check hidden, có thể list_dir(".git")
      explicit (path bắt đầu bằng "." được phép vào subdirectory cụ thể).

    SORTING:
      Directories trước (model thường care về structure trước content), rồi
      files. Trong mỗi nhóm, alphabetical sort.
    """
    # Sandbox check.
    p = _safe_path(path, workspace)
    if not p.exists():
        return f"ERROR: path not found: {path}"

    # `p.is_dir()` — method của Path, trả về True nếu p là thư mục (directory),
    # False nếu là file hoặc không tồn tại. Tách biệt với exists() vì user có thể
    # truyền path đến 1 file (vd "calculator.py") — đó không phải use case của list_dir.
    if not p.is_dir():
        return f"ERROR: {path} is not a directory"

    # Tạo 2 list rỗng để chứa entries theo loại.
    # Tách 2 list để sort dirs-first trong output.
    dirs = []
    files = []

    # `p.iterdir()` — method của Path, trả về generator các Path objects là
    # con trực tiếp của thư mục p (không đệ quy). Bao gồm cả file và thư mục con.
    #
    # `sorted(p.iterdir())` — ép generator thành list và sắp xếp alphabetical.
    # Sort key mặc định cho Path là string path của nó.
    for child in sorted(p.iterdir()):
        # `child.name` — thuộc tính của Path, chỉ lấy tên file/thư mục cuối cùng.
        # Ví dụ: Path("/a/b/file.txt").name  →  "file.txt"
        # `child.name.startswith(".")` — method của string, True nếu chuỗi bắt đầu bằng ".".
        # Dùng để skip hidden files (dot-prefix như .git, .venv, .env).
        if child.name.startswith("."):
            # `continue` — bỏ qua phần còn lại của vòng lặp, nhảy sang phần tử tiếp theo.
            # Tương đương "next" trong một số ngôn ngữ khác.
            continue

        if child.is_dir():
            # Trailing "/" sau tên giúp model nhận ra đây là thư mục (không phải file).
            dirs.append(f"  dir   {child.name}/")
        else:
            # `child.stat()` — lấy metadata của file (kích thước, ngày tạo, permissions,...).
            # `.st_size` — thuộc tính trong metadata, kích thước file tính bằng bytes.
            # Bao trong try/except vì có thể fail với symlink bị hỏng hoặc permission denied.
            try:
                size = child.stat().st_size
                file_entry = f"  file  {child.name}  ({size} bytes)"
            except OSError:
                # `OSError` — exception chuẩn cho lỗi liên quan đến hệ điều hành/file system.
                # Bao gồm: permission denied, broken symlink, file đang bị lock,...
                # Fallback: vẫn list được tên nhưng không lấy được size.
                file_entry = f"  file  {child.name}"
            files.append(file_entry)

    # `dirs + files` — nối 2 list lại. Trong Python, `+` với list = ghép thành list mới.
    # Ví dụ: [1, 2] + [3, 4]  →  [1, 2, 3, 4]
    # Dirs trước, files sau (visual hierarchy: structure trước content).
    items = dirs + files

    # `not items` — True nếu items là list rỗng. Explicit message tốt hơn empty string.
    if not items:
        return f"{path}/ is empty"

    # Header line "path/" + indent body cho readable formatting.
    # `"\n".join(items)` — ghép tất cả entries thành chuỗi, mỗi entry 1 dòng.
    return f"{path}/\n" + "\n".join(items)


def run_python(code: str, timeout: int = 60, *, workspace: Path) -> str:
    """Eval Python snippet trong sandbox. Capture stdout+stderr+exit_code.

    USE CASES:
      - Quick calc: `print(2**32)` thay vì gọi calculator tool ngoài.
      - Regex test: `import re; print(re.findall(r'\\d+', 'abc 123 def'))`.
      - Data exploration: `import json; print(json.load(open('x.json'))[0])`.
      - Format check: `import ast; ast.parse(open('foo.py').read())`.

    NOT FOR:
      - Running pytest → dùng run_bash("pytest").
      - Modifying files → dùng write_file/apply_patch/multi_edit.
      - Interactive REPL → subprocess không có stdin connection.

    SUBPROCESS ISOLATION:
      Mỗi call spawn 1 Python process MỚI. Không share state với main process.
      Pros: không pollute, GC reset, không risk infinite import loop.
      Cons: startup cost ~50ms, không persist variables giữa calls (model
            phải gom tất cả vào 1 snippet).

    sys.executable VS "python":
      sys.executable = path đến chính Python interpreter đang chạy (vd
      `.venv/bin/python`). An toàn hơn "python" vì user có thể có multiple
      Python versions, hoặc PATH không include venv.

    TIMEOUT:
      Default 60s = ngắn hơn run_bash (600s) vì snippets không nên long-running.
      Nếu cần lâu hơn, model có thể pass timeout cao hơn.
    """
    # `[sys.executable, "-c", code]` — chạy Python interpreter với flag -c,
    # tương đương gõ `python -c "print('hello')"` trên terminal.
    # Truyền list args (không shell=True) = không qua shell parsing, nên không
    # có shell injection. NHƯNG bản thân `code` vẫn là Python chạy full quyền
    # user — chỉ cwd + timeout giới hạn nó. Xem TRUST MODEL ở docstring đầu file.
    # Ruột subprocess + format + cap output nằm ở _run_captured (chung run_bash).
    return _run_captured([sys.executable, "-c", code], cwd=workspace, timeout=timeout)


def spawn_subagent(goal: str, max_iters: int = 8, *, workspace: Path) -> str:
    """Spawn child agent process để xử lý 1 subtask độc lập.

    USE CASES (chia để trị):
      - "count all Python files in this repo" (context-isolated, fast subagent)
      - "check if function foo_bar exists anywhere" (search-style query)
      - "summarize the test suite structure" (read-heavy exploration)

    DO NOT USE FOR:
      - Tasks needing PARENT's conversation context (subagent starts fresh).
      - Trivial 1-tool tasks (vd "list_dir(.)" — gọi tool trực tiếp rẻ hơn).
      - Editing tasks affecting state parent later depends on (subagent có
        thể edit file, parent không biết nếu không re-read).

    ARCHITECTURE — tại sao subprocess thay vì in-process recursion?
      1. Isolation: subagent có messages list RIÊNG, không share với parent.
         → context savings (parent không bloat by subagent reasoning).
      2. No stack growth: in-process recursion có thể stack-overflow nếu
         subagent thêm spawn_subagent nữa. Subprocess isolation phẳng hơn.
      3. Crash containment: nếu subagent crash, parent vẫn alive.
      4. Easy timeout enforcement: SIGKILL subprocess sau 300s là 1 call.

    TIMEOUT POLICY:
      Hardcoded 300s = 5 phút. Đủ cho subagent chạy 8 turns × ~20s/turn.
      Không expose timeout param vì model có thể abuse (set 1 giờ).

    RETURN VALUE:
      Last 2000 chars của stdout+stderr. Tail (not head) vì assistant final
      message + "Agent finished" line nằm ở cuối.
    """
    # ─────────────────────────────────────────────────────────────────
    # STEP 1: Locate project root.
    # Subagent invoked as `python -m src.agent <goal>` — cần cwd có
    # thư mục `src/` chứa `agent.py`. `workspace` thường là `demo_repo/`
    # (descendant của project root), nên phải walk lên tới khi tìm.
    # ─────────────────────────────────────────────────────────────────

    # `project_root = None` — khởi tạo biến với giá trị None (không có gì).
    # None là giá trị đặc biệt trong Python = "không có giá trị" (như null/nil).
    project_root = None

    # `cur = workspace` — gán workspace vào biến `cur` (current).
    # Sẽ walk lên từng thư mục cha để tìm project root.
    cur = workspace

    # `for _ in range(10):` — lặp đúng 10 lần.
    # `range(10)` tạo dãy số 0,1,2,...,9 (10 phần tử, không gồm 10).
    # `_` là tên biến đặc biệt trong Python = "tôi không cần dùng biến vòng lặp".
    # Quy ước: dùng `_` khi muốn bỏ qua giá trị nhưng Python yêu cầu có biến.
    for _ in range(10):
        # `(cur / "src" / "agent.py").exists()` — kiểm tra file tồn tại tại đường dẫn đó.
        # Nối path: cur / "src" / "agent.py" = /current_dir/src/agent.py
        # Nếu tìm thấy = đây là project root.
        if (cur / "src" / "agent.py").exists():
            project_root = cur
            # `break` — thoát khỏi vòng lặp ngay lập tức, không chờ hết 10 lần.
            break

        # `cur == cur.parent` — kiểm tra đã đến gốc filesystem chưa.
        # Ở đường dẫn gốc "/" (Linux) hoặc "C:\" (Windows), parent chính là nó.
        # Path("/").parent == Path("/") → True → đã đến đỉnh, không lên được nữa.
        if cur == cur.parent:
            break

        # `cur = cur.parent` — di chuyển lên thư mục cha 1 cấp.
        # Ví dụ: /home/user/project → /home/user → /home → /
        cur = cur.parent

    # `if project_root is None:` — kiểm tra có tìm được project root không.
    # `is None` (không phải `== None`) là cách Pythonic để so sánh với None.
    if project_root is None:
        return "ERROR: cannot find src/agent.py (project root not located)"

    # ─────────────────────────────────────────────────────────────────
    # STEP 2: Run subprocess.
    # `python -m src.agent <goal> --workspace <ws> --max-iters <n>` → invoke
    # agent.py __main__ block với CÙNG workspace như parent. Trước đây child
    # luôn dùng demo_repo (hardcoded) — đó là bug lâu năm. Giờ ta pass
    # `--workspace str(workspace)` để child sandbox đúng chỗ parent đang làm.
    # `--max-iters` cũng từng là bug kiểu đó: schema quảng cáo knob này nhưng
    # giá trị không bao giờ được truyền xuống child (child luôn chạy default
    # của run_agent). Giờ truyền thật để schema nói đúng sự thật.
    # ─────────────────────────────────────────────────────────────────
    try:
        # `-m src.agent` — chạy module `src.agent` như script (gọi __main__).
        # `str(workspace)` / `str(max_iters)` — argv phải là string, không phải
        # Path/int object.
        result = subprocess.run(
            [sys.executable, "-m", "src.agent", goal,
             "--workspace", str(workspace), "--max-iters", str(max_iters)],
            cwd=project_root,        # cwd phải là project root để Python tìm thấy package `src`
            capture_output=True,     # bắt stdout+stderr (subagent verbose log)
            text=True,
            timeout=300,             # 5 phút hard limit
        )
    except subprocess.TimeoutExpired:
        # Subagent stuck. Process đã bị SIGKILL bởi subprocess.run.
        return "ERROR: subagent timed out after 300s"

    # ─────────────────────────────────────────────────────────────────
    # STEP 3: Truncate output.
    # Subagent có thể verbose (mỗi turn log đầy đủ tool call + result).
    # 2000 chars tail = đủ thấy:
    #   - Last 1-2 tool calls + results
    #   - Assistant final message ("All tests pass" hoặc tương tự)
    #   - "Agent finished." marker
    # ─────────────────────────────────────────────────────────────────

    # `result.stdout or ""` — nếu stdout là None (không capture được), dùng "".
    # Toán tử `or` trong Python: trả về vế trái nếu "truthy", vế phải nếu không.
    # None là falsy → `None or ""` trả về "".
    # `(a or "") + (b or "")` — ghép chuỗi. Toán tử `+` với string = nối chuỗi.
    output = (result.stdout or "") + (result.stderr or "")

    # `_cap(..., tail=True)` — giữ 2000 ký tự CUỐI, marker đứng trước (xem _cap).
    # Cùng helper truncation với mọi tool khác — một logic, một chỗ sửa.
    output = _cap(output, 2000, tail=True)

    # Final format: exit code + output.
    # Exit code 0 = subagent finished normally; non-zero = crash/timeout/abort.
    return f"subagent exit_code: {result.returncode}\n{output}"


def finish(summary: str = "", *, workspace: Path) -> str:
    """Signal that the task is fully complete so the agent loop can stop.

    Unlike every other tool, finish() does not touch the workspace — it is a
    pure "I'm done" signal (it accepts `workspace` only because execute_tool
    injects it into every tool, but ignores it). Giving the model an explicit
    completion ACTION means it no longer has to end a task by replying in prose,
    which the loop cannot tell apart from "gave up without acting" (the no_action
    failure). run_agent detects a finish call and returns finish_reason="finished".
    """
    summary = (summary or "").strip()
    return f"Task marked complete. {summary}" if summary else "Task marked complete."


# ---------------------------------------------------------------------------
# Registry + JSON schemas
# ---------------------------------------------------------------------------

# `TOOLS` — một dict (từ điển) map tên tool → hàm Python tương ứng.
# `dict` trong Python: tập hợp cặp key → value.
# Cú pháp: {key1: value1, key2: value2, ...}
# Ví dụ: {"name": "Alice", "age": 30} — key là chuỗi, value là bất kỳ thứ gì.
# Ở đây: key = tên tool (string), value = hàm Python (function object — trong Python,
# hàm cũng là object, có thể gán vào biến, truyền làm tham số, lưu trong dict).
#
# `execute_tool()` sẽ lookup ở đây: TOOLS["read_file"] → hàm read_file.
# Phase 2+ có thể thêm new tools vào dict này MÀ KHÔNG cần sửa agent.py.
# Đó là pattern "extensible registry" — design choice quan trọng cho self-evolution.
TOOLS = {
    "read_file": read_file,
    "write_file": write_file,
    "run_bash": run_bash,
    # Phase 2 additions:
    "apply_patch": apply_patch,
    "multi_edit": multi_edit,
    "grep_files": grep_files,
    "glob_files": glob_files,
    "list_dir": list_dir,
    "run_python": run_python,
    "spawn_subagent": spawn_subagent,
    # Pi-redesign: explicit completion signal (productizes the no_action finding).
    "finish": finish,
}

# `TOOL_SCHEMAS` — một list (danh sách) các dict mô tả schema của từng tool.
# `list` trong Python: mảng có thứ tự, ký hiệu bằng [...].
# Ví dụ: [1, "hello", True, {"key": "val"}] — list có thể chứa mọi kiểu.
# Ở đây: mỗi phần tử là 1 dict mô tả 1 tool theo format OpenAI.
#
# Format OpenAI "function calling" schema — chuẩn được GPT-4, Claude, vLLM,
# Ollama và nhiều model khác hỗ trợ. Mỗi entry gồm:
#   "type": "function"           — loại tool (OpenAI định nghĩa, hiện chỉ có "function")
#   "function": {                — nested dict mô tả chi tiết hàm:
#     "name": "..."              — tên tool, PHẢI khớp với key trong TOOLS dict
#     "description": "..."      — model đọc đây để hiểu tool dùng vào việc gì
#     "parameters": {           — JSON Schema mô tả các tham số được phép gửi
#       "type": "object"        — tham số luôn là JSON object (dict)
#       "properties": {...}     — từng field: tên → {"type": kiểu, "description": ...}
#       "required": [...]       — list tên field BẮT BUỘC (không có default)
#     }
#   }
# Model đọc TOOL_SCHEMAS để biết: tool này tên gì, làm gì, nhận tham số nào.
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "Call this when the task is fully complete to END the session, passing a one-line summary of what you did. IMPORTANT: replying in prose WITHOUT any tool call does NOT end the task — to finish you must call this tool.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "One-line summary of what was accomplished."},
                },
                "required": ["summary"],
            },
        },
    },
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
            "description": "Run a shell command in the workspace. Use for tasks not covered by other tools (e.g. pytest, git, pip). For file listing prefer list_dir; for search prefer grep_files/glob_files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute."},
                    "timeout": {"type": "integer", "description": "Seconds before kill (default 600). Increase for long pip installs / builds."},
                },
                "required": ["command"],
            },
        },
    },
    # ------------------------------------------------------------------
    # Phase 2 tool schemas
    # ------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "apply_patch",
            "description": "Surgical search-and-replace edit on a single file. old_text MUST appear exactly once. Use this for small edits (1-10 lines) instead of write_file (which rewrites the whole file).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to the file."},
                    "old_text": {"type": "string", "description": "Exact substring to replace. Must be unique in the file — include enough surrounding context."},
                    "new_text": {"type": "string", "description": "Replacement text. Can be empty string to delete."},
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "multi_edit",
            "description": "Apply multiple atomic edits to ONE file in sequence. All-or-nothing: if any edit fails, the file is not modified. Use this when you have several small edits to the same file — more efficient than multiple apply_patch calls.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to the file."},
                    "edits": {
                        "type": "array",
                        "description": "List of edits to apply in order. Each must have unique old_text.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "old_text": {"type": "string"},
                                "new_text": {"type": "string"},
                            },
                            "required": ["old_text", "new_text"],
                        },
                    },
                },
                "required": ["path", "edits"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep_files",
            "description": "Regex search across files in the workspace. Returns matching lines with file:lineno prefix. Use this to find symbols, references, or text patterns — much cheaper than reading whole files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Extended regex (-E). Escape special chars."},
                    "path": {"type": "string", "description": "Starting directory relative to workspace. Default '.'."},
                    "file_glob": {"type": "string", "description": "Optional shell glob to restrict files (e.g. '*.py')."},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "glob_files",
            "description": "List files matching a shell glob pattern. Use ** for recursive. Example: '**/*.py' returns all Python files. Truncated at 50 entries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob pattern like '*.py' or '**/*.md'."},
                    "path": {"type": "string", "description": "Starting directory relative to workspace. Default '.'."},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List a directory's contents (files + sub-directories) with sizes. Cleaner than run_bash('ls -la'). Hidden files (starting with .) are skipped.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to the directory. Default '.'."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": "Execute a short Python snippet via 'python -c'. Use for quick calculations, regex testing, data exploration. NOT for running tests (use run_bash pytest) or modifying files (use write_file/apply_patch).",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python source code to execute. Use print() to get output."},
                    "timeout": {"type": "integer", "description": "Seconds before kill (default 60)."},
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "spawn_subagent",
            "description": "Spawn a child agent (separate process) to handle an independent subtask. Child returns its final answer as a string. Use for divide-and-conquer (e.g. 'check if function X exists in the repo'). DO NOT use for tasks that need parent's context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal": {"type": "string", "description": "Self-contained task description for the child agent."},
                    "max_iters": {"type": "integer", "description": "Child max iterations (default 8)."},
                },
                "required": ["goal"],
            },
        },
    },
]

# Lưu ý: `workspace` CỐ TÌNH không có trong TOOL_SCHEMAS — model không bao giờ
# truyền nó. execute_tool() tự inject `workspace=...` vào mỗi call.

# `assert` — câu lệnh kiểm tra điều kiện, chạy lúc IMPORT (load module), không phải
# lúc gọi hàm. Nếu điều kiện SAI → AssertionError được raise ngay lập tức,
# chương trình không chạy được. Đây là "fail fast" pattern.
#
# MỤC ĐÍCH: đảm bảo TOOLS dict và TOOL_SCHEMAS list không bị "drift" (lệch nhau).
# Trường hợp drift xảy ra khi:
#   - Thêm hàm vào TOOLS nhưng quên thêm schema vào TOOL_SCHEMAS
#   - Đổi tên tool trong TOOLS nhưng quên đổi tên trong TOOL_SCHEMAS
#   - Xóa tool khỏi 1 nơi nhưng không xóa nơi kia
#
# `set(TOOLS)` — `set()` chuyển dict thành tập hợp (set) các KEY.
#   set({"a": 1, "b": 2})  →  {"a", "b"}
#   Set = tập hợp không có thứ tự, không có phần tử trùng lặp.
#   Dùng set để so sánh "có cùng phần tử không" bất kể thứ tự.
#
# `{s["function"]["name"] for s in TOOL_SCHEMAS}` — "set comprehension":
#   Cú pháp ngắn gọn để tạo set từ iterable.
#   `for s in TOOL_SCHEMAS` — duyệt qua từng schema dict trong list.
#   `s["function"]["name"]` — lấy tên tool từ nested dict.
#   `{...}` bao ngoài — tạo set từ tất cả tên đó.
#   Kết quả: {"read_file", "write_file", "run_bash", ...}
#
# `==` — so sánh bằng. Với set: so sánh có cùng phần tử không (bất kể thứ tự).
# Nếu hai set KHÔNG bằng nhau → assert thất bại → AssertionError với message "TOOLS vs TOOL_SCHEMAS drift".
# Thông báo lỗi ngay lúc import thay vì lỗi mơ hồ lúc runtime (ví dụ: model
# gọi tool mà schema không tồn tại).
assert set(TOOLS) == {s["function"]["name"] for s in TOOL_SCHEMAS}, "TOOLS vs TOOL_SCHEMAS drift"


def execute_tool(name: str, arguments: str, workspace: Path) -> str:
    """Dispatch a tool call by name with a JSON string of arguments.

    The model gives us `arguments` as a string of JSON (never a dict). We parse,
    look up the function, call it, and stringify the result for the model.
    `workspace` is injected by the caller (run_agent) — the model never sends it;
    we append it as a keyword arg to every tool call.
    """
    # BƯỚC 1: Kiểm tra tên tool có hợp lệ không.
    # `name not in TOOLS` — `in` kiểm tra key có tồn tại trong dict không.
    # `not in` = ngược lại: "nếu tên KHÔNG có trong dict".
    if name not in TOOLS:
        # `list(TOOLS)` — chuyển dict thành list các key (tên tool) để hiển thị.
        # Giúp model biết có thể gọi tool nào hợp lệ.
        return f"ERROR: unknown tool {name}. Available: {list(TOOLS)}"

    # BƯỚC 2: Parse arguments từ JSON string → dict Python.
    # Model gửi arguments dưới dạng chuỗi JSON, ví dụ: '{"path": "file.py"}'
    # Phải convert thành dict Python để có thể gọi hàm với `**args`.
    #
    # `json.loads(arguments)` — hàm của module json.
    #   "loads" = "load from string" (khác "load" đọc từ file).
    #   Chuyển chuỗi JSON → đối tượng Python tương ứng:
    #     '{"key": "val"}' → {"key": "val"}  (dict)
    #     '[1, 2, 3]'       → [1, 2, 3]       (list)
    #     '"hello"'          → "hello"          (string)
    #
    # `if arguments else {}` — toán tử ternary:
    #   Nếu arguments không rỗng/None: parse JSON.
    #   Nếu rỗng/None: trả về dict rỗng {} (tool không cần args, vd list_dir mặc định).
    try:
        args = json.loads(arguments) if arguments else {}
    except json.JSONDecodeError as e:
        # `json.JSONDecodeError` — exception được raise khi chuỗi không phải JSON hợp lệ.
        # Ví dụ: json.loads("{bad json}") → JSONDecodeError.
        # Trả error string cho model thấy và sửa.
        return f"ERROR: bad JSON arguments: {e}"

    # BƯỚC 3: Gọi hàm tool với arguments đã parse.
    #
    # `TOOLS[name]` — lookup hàm từ dict theo tên. Ví dụ:
    #   TOOLS["read_file"] → <function read_file at 0x...> (function object)
    #
    # `**args` — "double star unpacking" hay "kwargs unpacking".
    #   Nếu args = {"path": "file.py", "content": "hello"}, thì:
    #   func(**args) tương đương func(path="file.py", content="hello")
    #   Python tự "trải phẳng" dict thành keyword arguments.
    #
    # `workspace=workspace` — inject workspace vào mỗi tool call.
    #   Model không gửi workspace (không có trong TOOL_SCHEMAS),
    #   nhưng mọi tool function đều cần nó (keyword-only arg `*, workspace: Path`).
    #   execute_tool() thêm nó vào như một phụ gia tự động.
    #
    # Try/except để bắt mọi exception từ bên trong tool function.
    # Tại sao? Exception trong tool sẽ crash agent.py loop nếu không bắt.
    # Mình muốn agent được "thấy" error qua tool result string và tự sửa,
    # không crash toàn bộ chương trình.
    try:
        result = TOOLS[name](**args, workspace=workspace)
    except TypeError as e:
        # `TypeError` — exception được raise khi gọi hàm với sai arguments:
        #   - Thiếu required arg (vd quên truyền `path`)
        #   - Truyền extra arg không có trong signature hàm
        #   - Truyền giá trị sai kiểu (vd truyền list thay vì string)
        return f"ERROR: bad args for {name}: {e}"
    except Exception as e:
        # `Exception` là base class của hầu hết exception trong Python.
        # `except Exception` = bắt MỌI loại exception khác (FileNotFoundError,
        # PermissionError, ValueError từ _safe_path, OSError, ...).
        # `e` là exception object — có message mô tả lỗi khi convert sang string.
        return f"ERROR: {name} crashed: {e}"

    # BƯỚC 4: Trả về kết quả.
    # Contract: mọi tool function PHẢI return str (model chỉ đọc được string).
    # Tất cả tool hiện tại đều khai báo `-> str` và thỏa contract,
    # nên không cần wrap str(result). Nếu sau này thêm tool return non-str,
    # coerce ở chính tool đó — không phải ở dispatcher này.
    return result
