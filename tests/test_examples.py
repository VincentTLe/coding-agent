"""
test_examples.py — mọi file examples/*.py phải import sạch (guard chống zombie).

Bài học thật: examples/06_chat.py từng chết-khi-import suốt nhiều tuần (import
`set_workspace` đã bị xóa trong refactor workspace-tường-minh, gọi execute_tool
2-arg theo API cũ) mà không test nào bắt — một file DẠY HỌC mà crash là đang
dạy API chết. File đó đã bị xóa; test này load từng examples/*.py bằng
importlib để zombie tương lai fail CI ngay. File mới thêm vào tự được cover.

Lưu ý: exec_module đặt __name__ = tên file (không phải "__main__") nên khối
`if __name__ == "__main__":` của example KHÔNG chạy — chỉ import, không cần vLLM.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

EXAMPLES = sorted((Path(__file__).resolve().parent.parent / "examples").glob("*.py"))


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_example_imports_cleanly(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
