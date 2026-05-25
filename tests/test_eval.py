"""
test_eval.py — Unit test thuần cho các helper đọc metadata trong eval/run.py.

KHÔNG cần vLLM / network: chỉ test read_section / read_meta (parse task.md),
không gọi run_agent. task.md được viết ra tmp_path nên hoàn toàn cô lập.

Giống đầu eval/run.py, ta phải thêm REPO ROOT vào sys.path TRƯỚC khi import,
vì `from eval.run import ...` cần thấy package `eval` ở repo root (và eval/run.py
lại import `from src.agent import run_agent` — chỉ resolve được khi root trên path).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Repo root = cha của thư mục tests/ (file này nằm ở <root>/tests/test_eval.py).
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from eval.run import read_meta, read_section  # noqa: E402


def _write_task(dir_path: Path, body: str) -> None:
    """Helper nhỏ: ghi task.md vào dir_path."""
    (dir_path / "task.md").write_text(body, encoding="utf-8")


# ---------------------------------------------------------------------------
# read_section — EXACT heading match (không prefix-match nhầm)
# ---------------------------------------------------------------------------

def test_read_section_exact_heading_match(tmp_path):
    """'## Goal' phải khớp CHÍNH XÁC, KHÔNG dính sang '## Goalkeeper'.

    Đây là bẫy: nếu code match bằng startswith/prefix thì 'Goal' sẽ ăn nhầm
    section 'Goalkeeper'. Kết quả đúng phải là 'X' (dưới ## Goal), không phải 'Y'.
    """
    _write_task(tmp_path, "## Goal\nX\n## Goalkeeper\nY\n")
    assert read_section(tmp_path, "Goal") == "X"


def test_read_section_missing_heading_returns_default(tmp_path):
    """Heading không tồn tại → trả về default đã truyền."""
    _write_task(tmp_path, "## Goal\nX\n")
    assert read_section(tmp_path, "Nonexistent", "fallback") == "fallback"


def test_read_section_no_task_md_returns_default(tmp_path):
    """Không có task.md → trả default (mặc định '')."""
    # tmp_path rỗng, chưa ghi task.md nào.
    assert read_section(tmp_path, "Goal", "def") == "def"
    assert read_section(tmp_path, "Goal") == ""


def test_read_meta_parses_category_and_difficulty(tmp_path):
    """read_meta trả (category, difficulty) lowercase từ task.md."""
    _write_task(tmp_path, "## Category\nStrings\n## Difficulty\nHard\n")
    cat, dif = read_meta(tmp_path)
    assert cat == "strings"
    assert dif == "hard"


def test_read_meta_defaults_when_absent(tmp_path):
    """Thiếu Category/Difficulty → default 'uncategorized' / 'unknown'."""
    _write_task(tmp_path, "## Goal\njust a goal\n")
    cat, dif = read_meta(tmp_path)
    assert cat == "uncategorized"
    assert dif == "unknown"
