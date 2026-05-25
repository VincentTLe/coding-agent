"""
test_tools.py — Unit test thuần cho src/tools.py.

KHÔNG cần vLLM / network: tất cả tool chạy trên filesystem trong tmp_path
(pytest builtin fixture cho thư mục tạm, tự dọn sau mỗi test). Mỗi test dùng
`tmp_path` như workspace (sandbox dir) để cô lập, không đụng repo thật.

src.tools là module trong package `src` → import trực tiếp được khi chạy
`pytest tests/` từ repo root (repo root nằm trên sys.path).
"""

from __future__ import annotations

import json

import pytest

from src.tools import (
    TOOL_SCHEMAS,
    TOOLS,
    _safe_path,
    apply_patch,
    execute_tool,
    multi_edit,
)


# ---------------------------------------------------------------------------
# _safe_path — sandbox enforcement
# ---------------------------------------------------------------------------

def test_safe_path_inside_workspace_ok(tmp_path):
    """Path nằm TRONG workspace → resolve OK, trả về path tuyệt đối đúng chỗ."""
    p = _safe_path("sub/file.txt", tmp_path)
    # Kết quả phải là con cháu của workspace (tmp_path).
    assert p == (tmp_path / "sub" / "file.txt").resolve()
    assert tmp_path in p.parents


def test_safe_path_root_dot_allowed(tmp_path):
    """'.' = chính workspace root → được phép (không raise)."""
    p = _safe_path(".", tmp_path)
    assert p == tmp_path.resolve()


def test_safe_path_dotdot_etc_rejected(tmp_path):
    """'../etc' leo ra ngoài sandbox → ValueError."""
    with pytest.raises(ValueError):
        _safe_path("../etc", tmp_path)


def test_safe_path_absolute_passwd_rejected(tmp_path):
    """Đường dẫn tuyệt đối '/etc/passwd' → escape workspace → ValueError.

    (workspace / '/etc/passwd') trong pathlib = '/etc/passwd', nằm ngoài tmp_path.
    """
    with pytest.raises(ValueError):
        _safe_path("/etc/passwd", tmp_path)


def test_safe_path_deep_dotdot_rejected(tmp_path):
    """'../../x' leo lên nhiều cấp → vẫn bị chặn."""
    with pytest.raises(ValueError):
        _safe_path("../../x", tmp_path)


# ---------------------------------------------------------------------------
# apply_patch — search-and-replace, uniqueness constraint
# ---------------------------------------------------------------------------

def test_apply_patch_exactly_one_match(tmp_path):
    """Đúng 1 match → patch thành công, nội dung file đổi đúng."""
    f = tmp_path / "code.py"
    f.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")

    out = apply_patch("code.py", "beta", "BETA", workspace=tmp_path)

    assert not out.startswith("ERROR")
    assert f.read_text(encoding="utf-8") == "alpha\nBETA\ngamma\n"


def test_apply_patch_zero_matches_errors_and_no_change(tmp_path):
    """old_text xuất hiện 0 lần → trả 'ERROR:' và KHÔNG sửa file."""
    f = tmp_path / "code.py"
    original = "alpha\nbeta\n"
    f.write_text(original, encoding="utf-8")

    out = apply_patch("code.py", "does_not_exist", "X", workspace=tmp_path)

    assert out.startswith("ERROR")
    # File phải giữ nguyên.
    assert f.read_text(encoding="utf-8") == original


def test_apply_patch_multiple_matches_errors_and_no_change(tmp_path):
    """old_text xuất hiện >1 lần → ambiguous → 'ERROR:' và KHÔNG sửa file."""
    f = tmp_path / "code.py"
    original = "dup\ndup\n"  # 'dup' xuất hiện 2 lần
    f.write_text(original, encoding="utf-8")

    out = apply_patch("code.py", "dup", "X", workspace=tmp_path)

    assert out.startswith("ERROR")
    assert f.read_text(encoding="utf-8") == original


# ---------------------------------------------------------------------------
# multi_edit — nhiều edit atomic, rollback nếu 1 edit hỏng
# ---------------------------------------------------------------------------

def test_multi_edit_applies_all_atomically(tmp_path):
    """Nhiều edit hợp lệ → apply tuần tự, tất cả thành công."""
    f = tmp_path / "code.py"
    f.write_text("one\ntwo\nthree\n", encoding="utf-8")

    edits = [
        {"old_text": "one", "new_text": "1"},
        {"old_text": "three", "new_text": "3"},
    ]
    out = multi_edit("code.py", edits, workspace=tmp_path)

    assert not out.startswith("ERROR")
    assert f.read_text(encoding="utf-8") == "1\ntwo\n3\n"


def test_multi_edit_rolls_back_on_invalid_edit(tmp_path):
    """1 edit hỏng (old_text không tồn tại) → file giữ NGUYÊN (rollback) + 'ERROR:'.

    Edit #1 hợp lệ nhưng edit #2 hỏng → vì atomic, edit #1 cũng KHÔNG được ghi
    ra đĩa. Đây là điểm mấu chốt: kiểm tra không có partial write.
    """
    f = tmp_path / "code.py"
    original = "one\ntwo\nthree\n"
    f.write_text(original, encoding="utf-8")

    edits = [
        {"old_text": "one", "new_text": "1"},      # hợp lệ
        {"old_text": "MISSING", "new_text": "X"},  # hỏng → phải rollback toàn bộ
    ]
    out = multi_edit("code.py", edits, workspace=tmp_path)

    assert out.startswith("ERROR")
    # Quan trọng: edit #1 KHÔNG được commit → file y nguyên bản gốc.
    assert f.read_text(encoding="utf-8") == original


# ---------------------------------------------------------------------------
# execute_tool — error contract: LUÔN trả string, không bao giờ raise
# ---------------------------------------------------------------------------

def test_execute_tool_unknown_name_returns_error(tmp_path):
    """Tên tool không tồn tại → 'ERROR:' string (không raise)."""
    out = execute_tool("no_such_tool", "{}", tmp_path)
    assert isinstance(out, str)
    assert out.startswith("ERROR")


def test_execute_tool_malformed_json_returns_error(tmp_path):
    """Arguments JSON hỏng → 'ERROR:' string (không raise)."""
    out = execute_tool("read_file", "{not valid json", tmp_path)
    assert isinstance(out, str)
    assert out.startswith("ERROR")


def test_execute_tool_missing_file_returns_error(tmp_path):
    """Tool raise/fail (read_file file thiếu) → 'ERROR:' string, KHÔNG exception."""
    args = json.dumps({"path": "nope.txt"})
    out = execute_tool("read_file", args, tmp_path)
    assert isinstance(out, str)
    assert out.startswith("ERROR")


def test_execute_tool_path_escape_returns_error(tmp_path):
    """Path escape workspace (ValueError trong tool) → convert thành 'ERROR:' string.

    read_file trên '/etc/passwd' khiến _safe_path raise ValueError; execute_tool
    phải bắt và trả string, không cho exception bubble lên crash agent.
    """
    args = json.dumps({"path": "/etc/passwd"})
    out = execute_tool("read_file", args, tmp_path)
    assert isinstance(out, str)
    assert out.startswith("ERROR")


# ---------------------------------------------------------------------------
# Registry / schema sync + round-trip
# ---------------------------------------------------------------------------

def test_registry_schema_in_sync():
    """Tên trong TOOLS phải khớp CHÍNH XÁC tên trong TOOL_SCHEMAS, và có đúng 10 tool."""
    schema_names = {s["function"]["name"] for s in TOOL_SCHEMAS}
    assert set(TOOLS) == schema_names
    assert len(TOOLS) == 10
    assert len(TOOL_SCHEMAS) == 10


def test_write_then_read_roundtrip(tmp_path):
    """write_file rồi read_file trong workspace → lấy lại đúng nội dung đã ghi."""
    content = "hello roundtrip\nline2\n"
    write_out = execute_tool(
        "write_file",
        json.dumps({"path": "out.txt", "content": content}),
        tmp_path,
    )
    assert not write_out.startswith("ERROR")

    read_out = execute_tool("read_file", json.dumps({"path": "out.txt"}), tmp_path)
    assert read_out == content
