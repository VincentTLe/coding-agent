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

Design note: adding a tool = append the function to TOOLS and its JSON schema
to TOOL_SCHEMAS — agent.py needs no changes (extensible registry pattern).
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
# Tool implementations — các hàm Python thật sự chạy khi model gọi tool
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


def run_bash(command: str, timeout: int = 600) -> str:
    """Run a shell command inside the workspace, capturing stdout+stderr.

    Default timeout 600s (10 phút) — đủ cho pytest, pip install, build nhỏ.
    Nếu cần lâu hơn, model có thể tự pass `timeout` lớn hơn (có trong JSON schema).
    """
    log.info(f"[tools] bash> {command}")
    try:
        # subprocess.run = chạy command đồng bộ, đợi xong mới return.
        # shell=True → command là chuỗi 1 dòng (cho phép pipe, redirect, etc.)
        # cwd=WORKSPACE → CWD của subprocess = workspace, nên `ls` ra files
        # trong demo_repo, không phải project root.
        # capture_output=True → stdout/stderr không in ra terminal, lưu vào result.
        # text=True → stdout/stderr là string thay vì bytes.
        # timeout=600 → giết command sau 10 phút nếu chưa xong (chống hang vĩnh viễn,
        # nhưng vẫn đủ thoáng cho pytest/install). Model có thể override qua args.
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
# Phase 2 tools — surgical edits, search, sub-agent, exec
# ---------------------------------------------------------------------------

def apply_patch(path: str, old_text: str, new_text: str) -> str:
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

    ERROR CONTRACT:
      Mọi lỗi trả về string bắt đầu "ERROR:" để model đọc + retry.
      File KHÔNG bị sửa nếu có bất kỳ lỗi nào (atomic by virtue of count check
      đứng trước write_text).
    """
    # Sandbox check — raise ValueError nếu path escape WORKSPACE.
    # Exception sẽ bubble lên execute_tool() và convert thành string "ERROR: ...".
    p = _safe_path(path)

    # Guard: file phải tồn tại trước khi đọc. Không cho phép apply_patch tạo
    # file mới — đó là việc của write_file. Phân tách concerns rõ ràng.
    if not p.exists():
        return f"ERROR: file not found: {path}"

    # errors="replace" = nếu file có byte không decode được UTF-8 (vd file binary
    # lẫn vào), thay bằng ký tự "?" thay vì crash. Edge case hiếm nhưng có.
    content = p.read_text(encoding="utf-8", errors="replace")

    # count() = đếm số lần substring xuất hiện. O(n) scan. Đủ nhanh cho file
    # vài trăm KB; với file MB phải dùng str.find loop nhưng overkill ở đây.
    count = content.count(old_text)

    # CASE 0: không tìm thấy. Lý do thường gặp:
    #   - model nhớ sai bytes (vd thiếu indent, sai whitespace)
    #   - file đã bị sửa bởi tool call trước → model có stale view
    # Hint trong error message bảo model "Read the file" để refresh.
    if count == 0:
        return f"ERROR: old_text not found in {path}. Read the file to get exact bytes."

    # CASE >1: ambiguous match. Vd `old_text="return 0"` mà file có 3 hàm
    # cùng return 0. Yêu cầu model expand context để unique-ify (vd thêm
    # tên hàm vào old_text).
    if count > 1:
        return (f"ERROR: old_text matches {count} places in {path}. "
                "Add more context (surrounding lines) to make it unique.")

    # CASE 1 (happy path): replace với count=1 (third arg) để chỉ thay 1 lần.
    # Mặc dù đã verify count==1, vẫn pass count=1 cho str.replace để defensive
    # (nếu code bị refactor sau này mà bỏ qua check, replace vẫn an toàn).
    new_content = content.replace(old_text, new_text, 1)

    # write_text overwrite hoàn toàn — atomic ở mức Python (1 syscall write).
    # Không có half-written state vì OS guarantee atomic write cho file nhỏ.
    p.write_text(new_content, encoding="utf-8")

    # Verbose success message giúp model verify tool đã làm gì.
    # Format: "patched X.py: replaced N chars with M chars" — model có thể
    # so sánh N với M để biết delta size (vd N=20, M=200 = thay 1 line bằng
    # cả block lớn — flag nếu unexpected).
    return f"patched {path}: replaced {len(old_text)} chars with {len(new_text)} chars"


def multi_edit(path: str, edits: list) -> str:
    """Apply MULTIPLE edits to ONE file atomically (all-or-nothing).

    SIGNATURE:
      edits = [{"old_text": "...", "new_text": "..."}, {...}, ...]

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
    p = _safe_path(path)
    if not p.exists():
        return f"ERROR: file not found: {path}"

    # Defensive type check — model có thể emit edits dạng dict thay vì list,
    # hoặc list rỗng (no-op should be explicit error, not silent success).
    if not isinstance(edits, list) or not edits:
        return "ERROR: edits must be a non-empty list of {old_text, new_text}"

    # Read 1 lần. Tất cả replace ops sẽ chạy trên biến `content` (in-memory).
    content = p.read_text(encoding="utf-8", errors="replace")

    # Lưu original_len cho success message (so sánh size trước/sau).
    original_len = len(content)

    # Loop apply từng edit. enumerate(edits, 1) = đánh số từ 1 (human-friendly
    # cho error message: "edit #1" thay vì "edit #0").
    for i, edit in enumerate(edits, 1):
        # Defensive: từng edit phải là dict (model có thể emit list/string nhầm).
        if not isinstance(edit, dict):
            return f"ERROR: edit #{i} not a dict (file not modified)"

        # .get() với default "" để không raise KeyError nếu field thiếu.
        # Validation sẽ xảy ra ngay sau (empty old_text → error).
        old = edit.get("old_text", "")
        new = edit.get("new_text", "")

        # Empty old_text = invalid (không có gì để search). Note: empty new_text
        # vẫn OK — đó là delete operation hợp lệ.
        if not old:
            return f"ERROR: edit #{i} has empty old_text (file not modified)"

        # Uniqueness check — same logic apply_patch nhưng trên `content` đã
        # bị mutate bởi các edit trước. Đây là điểm "sequential" quan trọng:
        # edit #2 search trên kết quả của edit #1, không phải file gốc.
        count = content.count(old)
        if count == 0:
            return f"ERROR: edit #{i}: old_text not found (file not modified)"
        if count > 1:
            return f"ERROR: edit #{i}: old_text matches {count} places (file not modified)"

        # Mutate `content` in-place (well, immutable string reassignment).
        # Lưu ý: NẾU loop break sau dòng này do edit sau fail, `content` đã
        # chứa partial edits, NHƯNG ta CHƯA write ra đĩa — atomicity preserved.
        content = content.replace(old, new, 1)

    # Reach here = tất cả edits passed uniqueness check. Commit 1 lần ra đĩa.
    p.write_text(content, encoding="utf-8")

    # Success: report số edits + size delta. Size delta giúp model sanity-check
    # (vd 10 edits xóa code mà file lớn hơn → suspicious).
    return f"applied {len(edits)} edits to {path} ({original_len} → {len(content)} chars)"


def grep_files(pattern: str, path: str = ".", file_glob: str = "") -> str:
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
    # Sandbox: path phải nằm trong WORKSPACE.
    p = _safe_path(path)
    if not p.exists():
        return f"ERROR: path not found: {path}"

    # Build grep command với flags:
    #   -r = recursive (walk subdirs)
    #   -n = include line numbers in output
    #   -E = extended regex (default trong nhiều grep version, nhưng explicit
    #        cho cross-version consistency)
    cmd = ["grep", "-rnE"]

    # --include filter chỉ scan file matching glob. Truyền RIÊNG (không gộp
    # vào pattern) vì grep `--include=*.py` vs `--include *.py` cùng work.
    # Nếu file_glob rỗng, BỎ flag — không pass --include "" (sẽ match nothing).
    if file_glob:
        cmd.extend(["--include", file_glob])

    # Search target = path RELATIVE to WORKSPACE, và chạy grep với cwd=WORKSPACE.
    # Lý do: nếu pass absolute str(p), grep in ra absolute path trong mỗi dòng
    # match (vd `/home/.../ws/a.py:1:...`) — vừa noisy vừa SAI so với docstring
    # (hứa relative path) vừa khó cho model tái sử dụng path. Dùng relative
    # target → output là `a.py:1:...` / `sub/b.py:1:...` đúng như tài liệu.
    rel = p.relative_to(WORKSPACE)
    target = str(rel) if str(rel) != "." else "."

    # `--` separator — đảm bảo pattern không bị parse là option flag nếu
    # pattern bắt đầu bằng `-` (vd `-foo`). subprocess thì pass arg list nên
    # ít vấn đề, nhưng vẫn để defensive cho mọi grep variant.
    cmd.extend(["--", pattern, target])

    # Subprocess execution với timeout = 30s. Grep với regex evil có thể
    # ReDoS (catastrophic backtracking) nhưng 30s đủ để fail-safe.
    # cwd=WORKSPACE để grep emit path relative to workspace (xem comment trên).
    try:
        result = subprocess.run(cmd, cwd=WORKSPACE, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        return "ERROR: grep timed out after 30s"

    # Grep exit codes:
    #   0 = matches found
    #   1 = no matches (NOT an error from our perspective)
    #   2 = real error (invalid regex, permission denied, etc.)
    if result.returncode == 1:
        return f"no matches for pattern: {pattern}"
    if result.returncode != 0:
        # stderr.strip() để loại bỏ trailing newline, dễ đọc hơn.
        return f"ERROR: grep failed (exit {result.returncode}): {result.stderr.strip()}"

    # splitlines() split theo \n, \r\n, \r — robust cross-platform.
    lines = result.stdout.splitlines()

    # Truncation: 50 lines là sweet spot — đủ context cho model nhưng không
    # blow up token budget (50 lines × ~80 chars ≈ 4K tokens worst case).
    # Nếu model cần hơn, có thể narrow pattern hoặc giới hạn file_glob.
    if len(lines) > 50:
        return "\n".join(lines[:50]) + f"\n... [truncated, {len(lines) - 50} more matches]"

    # Empty stdout với exit 0 cực kỳ rare (grep -r với 0 lines stdout thường
    # = no match = exit 1), nhưng handle defensive.
    return "\n".join(lines) if lines else "no matches"


def glob_files(pattern: str, path: str = ".") -> str:
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
      Lưu ý: glob KHÔNG match file ẩn (bắt đầu bằng `.`) trừ khi pattern
      explicit có `.` đầu.

    OUTPUT: relative path đến WORKSPACE, 1/line, truncated tại 50.
    """
    # Sandbox check — `path` là điểm bắt đầu glob, không phải pattern.
    p = _safe_path(path)
    if not p.exists():
        return f"ERROR: path not found: {path}"

    # pathlib.Path.glob() trả generator của Path objects. sorted() ép realize
    # toàn bộ thành list + sort alphabetical (giúp output deterministic, dễ
    # diff giữa các lần chạy).
    # Bao catch-all Exception vì glob pattern xấu (vd unclosed `[`) raise
    # các loại exception khác nhau (ValueError, OSError) tùy Python version.
    try:
        matches = sorted(p.glob(pattern))
    except Exception as e:
        return f"ERROR: invalid glob pattern: {e}"

    # Edge case: pattern hợp lệ nhưng không match gì. Message rõ ràng giúp
    # model biết phải đổi pattern (vd thử '**/*.py' thay vì '*.py' nếu file
    # nằm dưới subdirectory).
    if not matches:
        return f"no files match {pattern} in {path}"

    # Convert sang relative-to-WORKSPACE path — gọn hơn absolute path
    # (vd "src/agent.py" thay vì "/home/tle/.../coding-agent/src/agent.py").
    # Nếu vì lý do nào đó match nằm ngoài WORKSPACE (không nên xảy ra vì
    # _safe_path đã check), fallback dùng str(m) absolute.
    rel = []
    for m in matches:
        try:
            rel.append(str(m.relative_to(WORKSPACE)))
        except ValueError:
            # relative_to raises ValueError nếu m không phải descendant của
            # WORKSPACE. Defensive — không nên trigger trong practice.
            rel.append(str(m))

    # Same truncation policy as grep_files: 50 là sweet spot cho token budget.
    if len(rel) > 50:
        return "\n".join(rel[:50]) + f"\n... [truncated, {len(rel) - 50} more]"
    return "\n".join(rel)


def list_dir(path: str = ".") -> str:
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
    p = _safe_path(path)
    if not p.exists():
        return f"ERROR: path not found: {path}"

    # is_dir() check tách biệt với exists() vì user có thể truyền path đến
    # 1 file (vd "calculator.py") — đó không phải là use case của list_dir.
    if not p.is_dir():
        return f"ERROR: {path} is not a directory"

    # Tách 2 list để sort dirs-first trong output, vẫn alphabetical trong từng nhóm.
    dirs = []
    files = []

    # iterdir() trả generator các Path child. sorted() ép realize + sort theo
    # name (default sort key cho Path là str(path)). Deterministic output.
    for child in sorted(p.iterdir()):
        # Skip hidden files (dot-prefix). Model có thể list_dir(".git") explicit
        # nếu cần inspect — đây chỉ là default behavior cho clutter reduction.
        if child.name.startswith("."):
            continue

        if child.is_dir():
            # Trailing "/" giúp model phân biệt visually directory với file.
            dirs.append(f"  dir   {child.name}/")
        else:
            # File: include size để model có sense về kích thước trước khi
            # read_file (vd file 50KB có thể overflow context, model nên grep
            # thay vì read full).
            try:
                size = child.stat().st_size
                file_entry = f"  file  {child.name}  ({size} bytes)"
            except OSError:
                # Permission denied hoặc symlink broken — vẫn list được tên
                # nhưng không lấy được size. Defensive fallback.
                file_entry = f"  file  {child.name}"
            files.append(file_entry)

    # Merge: dirs trước, files sau (visual hierarchy).
    items = dirs + files

    # Edge case: thư mục rỗng. Explicit message tốt hơn empty string.
    if not items:
        return f"{path}/ is empty"

    # Header line "path/" + indent body cho readable formatting.
    return f"{path}/\n" + "\n".join(items)


def run_python(code: str, timeout: int = 60) -> str:
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
    # sys import local (không top-level) vì chỉ run_python và spawn_subagent
    # cần sys.executable. Giữ top-level imports tối thiểu — marginal choice,
    # import sys lần 2 gần như free vì module đã nằm trong sys.modules cache.
    import sys

    try:
        # subprocess.run với list args (không shell=True) = SAFE từ injection.
        # `code` được pass thẳng vào Python interpreter as `-c` argument,
        # không qua shell parsing → no command injection risk.
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=WORKSPACE,           # CWD = sandbox dir, không phải project root
            capture_output=True,     # stdout/stderr → result object (không in ra terminal)
            text=True,               # decode bytes → str (utf-8 default)
            timeout=timeout,         # giết process sau N giây nếu chưa xong
        )
    except subprocess.TimeoutExpired:
        # Timeout = code có infinite loop hoặc network hang. Trả error rõ ràng.
        return f"ERROR: python timed out after {timeout}s"

    # Format output: 3 sections (exit_code, stdout, stderr) — same shape as
    # run_bash để model học 1 format dùng cho cả 2 tool.
    parts = [f"exit_code: {result.returncode}"]
    if result.stdout:
        # Conditional include: nếu rỗng thì bỏ section để output gọn.
        parts.append(f"stdout:\n{result.stdout}")
    if result.stderr:
        # stderr có thể chứa tracebacks (Python crash) → quan trọng cho debug.
        parts.append(f"stderr:\n{result.stderr}")
    return "\n".join(parts)


def spawn_subagent(goal: str, max_iters: int = 8) -> str:
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
      Last 2000 chars of stdout+stderr. Tail (not head) vì assistant final
      message + "Agent finished" line nằm ở cuối.
    """
    import sys

    # ─────────────────────────────────────────────────────────────────
    # STEP 1: Locate project root.
    # Subagent invoked as `python -m src.agent <goal>` — cần cwd có
    # thư mục `src/` chứa `agent.py`. WORKSPACE thường là `demo_repo/`
    # (descendant của project root), nên phải walk lên tới khi tìm.
    # ─────────────────────────────────────────────────────────────────
    project_root = None
    cur = WORKSPACE

    # Safeguard: max 10 levels up. Tránh infinite loop nếu filesystem bị
    # corrupt hoặc symlink loop. Realistic depth ≤ 5.
    for _ in range(10):
        # Marker: src/agent.py phải tồn tại = đây là project root.
        if (cur / "src" / "agent.py").exists():
            project_root = cur
            break

        # Reached filesystem root: cur.parent == cur (/, hoặc Windows C:\).
        # Không lên được nữa.
        if cur == cur.parent:
            break

        cur = cur.parent

    if project_root is None:
        # Không nên xảy ra trong production setup, nhưng defensive.
        return "ERROR: cannot find src/agent.py (project root not located)"

    # ─────────────────────────────────────────────────────────────────
    # STEP 2: Run subprocess.
    # `python -m src.agent <goal>` → invoke agent.py __main__ block.
    # __main__ sẽ tự set_workspace(demo_repo) — child agent KHÔNG inherit
    # parent's WORKSPACE (hardcoded behavior trong agent.py).
    # Note: nếu cần subagent work trong workspace khác, cần modify agent.py
    # hoặc thêm --workspace flag.
    # ─────────────────────────────────────────────────────────────────
    try:
        result = subprocess.run(
            [sys.executable, "-m", "src.agent", goal],
            cwd=project_root,        # cwd phải là project root để Python tìm thấy package `src`
            capture_output=True,     # bắt stdout+stderr (subagent verbose log)
            text=True,
            timeout=300,             # 5 phút hard limit
        )
    except subprocess.TimeoutExpired:
        # Subagent stuck. Trả error rõ ràng. Process đã bị SIGKILL bởi subprocess.run.
        return "ERROR: subagent timed out after 300s"

    # ─────────────────────────────────────────────────────────────────
    # STEP 3: Truncate output.
    # Subagent có thể verbose (mỗi turn log đầy đủ tool call + result).
    # 2000 chars tail = đủ thấy:
    #   - Last 1-2 tool calls + results
    #   - Assistant final message ("All tests pass" hoặc tương tự)
    #   - "Agent finished." marker
    # ─────────────────────────────────────────────────────────────────
    # Concatenate stdout + stderr — agent.py dùng logging.info nên có thể
    # vào stderr tùy logging config. Concat safer than picking 1.
    output = (result.stdout or "") + (result.stderr or "")

    if len(output) > 2000:
        # Prefix "... [truncated]" để model biết có nội dung trước đó bị bỏ.
        output = "... [truncated, showing last 2000 chars]\n" + output[-2000:]

    # Final format: exit code + output. Exit code 0 = subagent finished
    # normally; non-zero = crash/timeout/abort.
    return f"subagent exit_code: {result.returncode}\n{output}"


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
    # Phase 2 additions:
    "apply_patch": apply_patch,
    "multi_edit": multi_edit,
    "grep_files": grep_files,
    "glob_files": glob_files,
    "list_dir": list_dir,
    "run_python": run_python,
    "spawn_subagent": spawn_subagent,
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

    # 4. Trả về kết quả. Contract: mọi tool function PHẢI return str (model chỉ
    # đọc được string). Tất cả tool hiện tại đều khai báo `-> str` và thoả
    # contract, nên bỏ wrap `str(result)` cho gọn. Nếu sau này thêm tool return
    # non-str, coerce ở chính tool đó — không phải ở dispatcher.
    return result
