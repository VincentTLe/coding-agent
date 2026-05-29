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

import eval.run as R  # noqa: E402
from eval.run import (  # noqa: E402
    read_meta,
    read_section,
    remove_extras,
    restore_files,
    run_pytest,
    snapshot_files,
)


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


# ---------------------------------------------------------------------------
# Scoring critical path — snapshot / restore / remove_extras (audit #5: was untested)
# ---------------------------------------------------------------------------

def test_snapshot_restore_roundtrip(tmp_path):
    """snapshot → agent mutates + leaks files/dirs → restore returns dir to the snapshot.

    This is the highest-blast-radius logic in the harness (a bug here corrupts EVERY
    score) and previously had zero coverage."""
    d = tmp_path / "task"
    d.mkdir()
    (d / "sol.py").write_text("original", encoding="utf-8")
    (d / "test_sol.py").write_text("def test(): assert True", encoding="utf-8")
    snap = snapshot_files(d)
    # Agent makes a mess: edits a tracked file, leaks a stray file and a stray dir.
    (d / "sol.py").write_text("AGENT EDIT", encoding="utf-8")
    (d / "stray.txt").write_text("junk", encoding="utf-8")
    (d / "junkdir").mkdir()
    (d / "junkdir" / "x.py").write_text("x", encoding="utf-8")
    restore_files(d, snap)
    assert (d / "sol.py").read_text(encoding="utf-8") == "original"   # reverted
    assert (d / "test_sol.py").exists()                               # kept
    assert not (d / "stray.txt").exists()                             # extra removed
    assert not (d / "junkdir").exists()                               # extra dir removed (recursive)
    assert {p.name for p in d.iterdir()} == {"sol.py", "test_sol.py"}


def test_remove_extras_keeps_snapshot_only(tmp_path):
    """remove_extras deletes exactly the paths not in the snapshot."""
    d = tmp_path / "t"
    d.mkdir()
    (d / "keep.py").write_text("k", encoding="utf-8")
    snap = snapshot_files(d)
    (d / "drop.py").write_text("d", encoding="utf-8")
    remove_extras(d, snap)
    assert (d / "keep.py").exists() and not (d / "drop.py").exists()


def test_run_pytest_requires_a_real_passing_test(tmp_path):
    """Exit code 0 alone is NOT a pass (audit): an all-skipped or no-test directory must
    score FAIL, otherwise a missing/hidden-test corruption silently scores as PASS."""
    # (a) genuine pass → True
    (tmp_path / "test_a.py").write_text("def test_ok():\n    assert 1 == 1\n", encoding="utf-8")
    assert run_pytest(tmp_path)[0] is True
    # (b) all skipped → exit 0 but 0 passed → must be FALSE
    (tmp_path / "test_a.py").write_text(
        "import pytest\n@pytest.mark.skip(reason='x')\ndef test_s():\n    assert True\n", encoding="utf-8")
    assert run_pytest(tmp_path)[0] is False
    # (c) no test files at all → exit 5 → FALSE
    (tmp_path / "test_a.py").unlink()
    assert run_pytest(tmp_path)[0] is False
    # (d) a failing test → FALSE
    (tmp_path / "test_b.py").write_text("def test_bad():\n    assert 1 == 2\n", encoding="utf-8")
    assert run_pytest(tmp_path)[0] is False


# ---------------------------------------------------------------------------
# Crash-safe hidden tests — startup sweep recovers a hard-killed run (audit #2)
# ---------------------------------------------------------------------------

def test_restore_orphaned_hidden_tests_recovers_after_hard_kill(tmp_path, monkeypatch):
    """A test file left in the backup dir (run hard-killed before restore) is moved back
    to its task on the next startup — prevents the silent self-propagating false-fail."""
    tasks = tmp_path / "tasks"
    backup = tmp_path / "backup"
    (tasks / "bench" / "he_001").mkdir(parents=True)
    monkeypatch.setattr(R, "TASKS_DIR", tasks)
    monkeypatch.setattr(R, "HIDDEN_BACKUP_DIR", backup)
    bak = backup / "bench" / "he_001" / "test_x.py"
    bak.parent.mkdir(parents=True)
    bak.write_text("def test_ok(): assert True", encoding="utf-8")
    orig = tasks / "bench" / "he_001" / "test_x.py"
    assert not orig.exists()
    n = R.restore_orphaned_hidden_tests()
    assert n == 1
    assert orig.read_text(encoding="utf-8") == "def test_ok(): assert True"
    assert not backup.exists()                       # backup dir cleaned


def test_sweep_drops_stale_backup_when_original_present(tmp_path, monkeypatch):
    """If the original test is already present, a leftover backup is dropped (not restored
    over the real file) and counted as 0 restored."""
    tasks = tmp_path / "tasks"
    backup = tmp_path / "backup"
    (tasks / "bench" / "he_002").mkdir(parents=True)
    monkeypatch.setattr(R, "TASKS_DIR", tasks)
    monkeypatch.setattr(R, "HIDDEN_BACKUP_DIR", backup)
    orig = tasks / "bench" / "he_002" / "test_y.py"
    orig.write_text("real", encoding="utf-8")
    bak = backup / "bench" / "he_002" / "test_y.py"
    bak.parent.mkdir(parents=True)
    bak.write_text("stale", encoding="utf-8")
    n = R.restore_orphaned_hidden_tests()
    assert n == 0
    assert orig.read_text(encoding="utf-8") == "real"   # original untouched
    assert not backup.exists()
