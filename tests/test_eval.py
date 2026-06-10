"""
test_eval.py — Unit test thuần cho các helper đọc metadata trong eval/run.py.

KHÔNG cần vLLM / network: chỉ test read_section / read_task_meta (parse task.md),
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
    read_section,
    read_task_meta,
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


def test_read_task_meta_parses_category_and_difficulty(tmp_path):
    """read_task_meta trả category/difficulty lowercase từ task.md (đọc file 1 lần)."""
    _write_task(tmp_path, "## Category\nStrings\n## Difficulty\nHard\n")
    meta = read_task_meta(tmp_path)
    assert meta["category"] == "strings"
    assert meta["difficulty"] == "hard"


def test_read_task_meta_defaults_when_absent(tmp_path):
    """Thiếu Category/Difficulty → default 'uncategorized' / 'unknown'."""
    _write_task(tmp_path, "## Goal\njust a goal\n")
    meta = read_task_meta(tmp_path)
    assert meta["category"] == "uncategorized"
    assert meta["difficulty"] == "unknown"


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
# Crash recovery — git-based heal restores tests AND contaminated code (audit #2/#3,
# Codex review: tests are unlinked in-place — never left on disk — so git is the backup)
# ---------------------------------------------------------------------------

def test_heal_corrupted_tasks_restores_from_git(tmp_path, monkeypatch):
    """After a hard-kill leaves a deleted test and an agent-modified file, the next startup's
    `git checkout -- eval/tasks` restores BOTH to HEAD (no on-disk backup = no leak)."""
    import subprocess as sp
    repo = tmp_path / "repo"
    tdir = repo / "eval" / "tasks" / "bench" / "he_001"
    tdir.mkdir(parents=True)
    test_f = tdir / "test_x.py"
    test_f.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    sol = tdir / "sol.py"
    sol.write_text("def f():\n    return 1\n", encoding="utf-8")
    g = ["git", "-c", "user.email=t@t", "-c", "user.name=t"]
    sp.run(["git", "init", "-q"], cwd=repo, check=True)
    sp.run(g + ["add", "-A"], cwd=repo, check=True)
    sp.run(g + ["commit", "-qm", "init"], cwd=repo, check=True)
    # simulate hard-kill contamination: hidden test left deleted, sol left agent-modified
    test_f.unlink()
    sol.write_text("def f():\n    return 999  # agent edit left by hard-kill\n", encoding="utf-8")
    monkeypatch.setattr(R, "ROOT", repo)
    monkeypatch.setattr(R, "TASKS_DIR", repo / "eval" / "tasks")
    n = R.heal_corrupted_tasks()
    # SAFE policy (Codex re-review #1): restore ONLY the DELETED test (can't lose legit content);
    # a MODIFIED file is only warned about, NOT auto-reverted (don't clobber legitimate edits).
    assert n == 1
    assert test_f.read_text(encoding="utf-8") == "def test_ok():\n    assert True\n"   # deleted test restored
    assert "999" in sol.read_text(encoding="utf-8")                                    # modified file left intact


def test_heal_corrupted_tasks_noop_when_clean(tmp_path, monkeypatch):
    """No uncommitted changes under eval/tasks → heal is a no-op (returns 0)."""
    import subprocess as sp
    repo = tmp_path / "repo"
    (repo / "eval" / "tasks" / "bench" / "he_001").mkdir(parents=True)
    (repo / "eval" / "tasks" / "bench" / "he_001" / "test_x.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    g = ["git", "-c", "user.email=t@t", "-c", "user.name=t"]
    sp.run(["git", "init", "-q"], cwd=repo, check=True)
    sp.run(g + ["add", "-A"], cwd=repo, check=True)
    sp.run(g + ["commit", "-qm", "init"], cwd=repo, check=True)
    monkeypatch.setattr(R, "ROOT", repo)
    monkeypatch.setattr(R, "TASKS_DIR", repo / "eval" / "tasks")
    assert R.heal_corrupted_tasks() == 0
