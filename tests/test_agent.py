"""
test_agent.py — unit tests for model config AND the ReAct loop (no vLLM needed).

Config: load_model_config() reads models.json by id, with $AGENT_MODEL override
and a .env fallback. Loop: run_agent(client=...) nhận client GIẢ với response
soạn sẵn — nhờ seam này mọi bất biến đã document của vòng lặp (5 finish_reason,
ghép cặp tool_calls ↔ role:"tool", nudge cap, iters_used) đều test được offline.
"""

from __future__ import annotations

import json

from openai import OpenAIError

from src.agent import ModelConfig, load_model_config, run_agent
from src.prompts import SYSTEM_PROMPT, build_system_prompt


def test_load_model_config_reads_models_json():
    """models.json at the repo root resolves to a ModelConfig with sane fields."""
    load_model_config.cache_clear()
    cfg = load_model_config()
    assert isinstance(cfg, ModelConfig)
    assert cfg.model and cfg.base_url.startswith("http")
    assert cfg.max_tokens > 0 and cfg.context_window > 0


def test_agent_model_env_override(monkeypatch):
    """$AGENT_MODEL selects a different entry from models.json (model swap = config)."""
    monkeypatch.setenv("AGENT_MODEL", "qwen3-8b")
    load_model_config.cache_clear()
    try:
        assert load_model_config().model == "Qwen/Qwen3-8B"
    finally:
        # Don't leak the cached override into other tests.
        load_model_config.cache_clear()


def test_build_system_prompt_none_is_byte_identical():
    """No/empty/whitespace skill → byte-identical SYSTEM_PROMPT (default unchanged)."""
    assert build_system_prompt(None) == SYSTEM_PROMPT
    assert build_system_prompt("") == SYSTEM_PROMPT
    assert build_system_prompt("   \n  \t ") == SYSTEM_PROMPT


def test_build_system_prompt_appends_skill():
    """With skill text → starts with the full base prompt AND contains the skill."""
    out = build_system_prompt("RULE: write a failing test first.")
    assert out.startswith(SYSTEM_PROMPT)
    assert "RULE: write a failing test first." in out
    assert "Learned skills" in out


def test_agent_logging_follows_current_stderr():
    """Regression (audit HIGH — AUDITABILITY): the agent's logging handler must write to
    sys.stderr AT EMIT TIME, not stay bound to whatever stderr existed when logging was
    configured. eval calls run_agent inside redirect_stderr(per-task file); on a reused
    spawn-pool worker, a once-bound handler kept writing to the first task's closed stream
    → 590/627 per-task logs were 0 bytes. Configure once, then log under two different
    redirects: BOTH must receive their line."""
    import io
    from contextlib import redirect_stderr
    from src import agent as A

    A._logging_ready = False
    A.log.handlers.clear()
    A._setup_logging()                       # configure once (like the first run_agent call)
    b1, b2 = io.StringIO(), io.StringIO()
    with redirect_stderr(b1):
        A.log.info("alpha-trace")
    with redirect_stderr(b2):
        A.log.info("beta-trace")
    assert "alpha-trace" in b1.getvalue(), "log did not follow redirect #1"
    assert "beta-trace" in b2.getvalue(), "log did not follow redirect #2 (0-byte-logs bug)"


# ---------------------------------------------------------------------------
# ReAct-loop tests — FakeClient bơm qua run_agent(client=...), không cần vLLM.
# ---------------------------------------------------------------------------

class _Fn:
    def __init__(self, name: str, arguments: str = "{}"):
        self.name = name
        self.arguments = arguments


class _ToolCall:
    def __init__(self, name: str, arguments: str = "{}", id: str = "call_1"):
        self.id = id
        self.function = _Fn(name, arguments)


class _Msg:
    """Đóng giả ChatCompletionMessage: .content / .tool_calls / .model_dump()."""

    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or None

    def model_dump(self, exclude_none: bool = True) -> dict:
        d: dict = {"role": "assistant"}
        if self.content is not None:
            d["content"] = self.content
        if self.tool_calls:
            d["tool_calls"] = [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name,
                              "arguments": tc.function.arguments}}
                for tc in self.tool_calls
            ]
        return d


class _Choice:
    def __init__(self, msg):
        self.message = msg


class _Resp:
    def __init__(self, msg, empty: bool = False):
        self.choices = [] if empty else [_Choice(msg)]


class FakeClient:
    """Client soạn kịch bản: mỗi create() trả turn kế tiếp (msg / Exception / "empty").

    Giữ tham chiếu `seen_messages` tới CHÍNH list messages của run_agent — sau khi
    chạy, test soi được trạng thái cuối của message list (bất biến ghép cặp).
    """

    def __init__(self, turns):
        self._turns = list(turns)
        self.calls = 0
        self.seen_messages = None
        fake = self

        class _Completions:
            def create(self, **kwargs):
                fake.calls += 1
                fake.seen_messages = kwargs["messages"]
                turn = fake._turns.pop(0)
                if isinstance(turn, Exception):
                    raise turn
                if turn == "empty":
                    return _Resp(None, empty=True)
                return _Resp(turn)

        class _Chat:
            completions = _Completions()

        self.chat = _Chat()


def _assert_pairing(messages):
    """Bất biến: mỗi assistant.tool_calls có ĐÚNG len(tool_calls) role:"tool" theo sau, khớp id."""
    for idx, m in enumerate(messages):
        if isinstance(m, dict) and m.get("role") == "assistant" and m.get("tool_calls"):
            ids = [tc["id"] for tc in m["tool_calls"]]
            follow = messages[idx + 1: idx + 1 + len(ids)]
            assert [f.get("tool_call_id") for f in follow] == ids, \
                f"orphan tool_calls at index {idx}: {ids}"
            assert all(f.get("role") == "tool" for f in follow)


def _write_call(path: str = "a.txt", content: str = "hi", id: str = "call_w") -> _ToolCall:
    return _ToolCall("write_file", json.dumps({"path": path, "content": content}), id=id)


def test_loop_tool_then_content_is_finished(tmp_path):
    """Hành động rồi trả content trần → finished; tool có chạy thật; pairing giữ."""
    fc = FakeClient([
        _Msg(tool_calls=[_write_call()]),
        _Msg(content="all done"),
    ])
    out = run_agent("t", tmp_path, client=fc)
    assert out == {"finish_reason": "finished", "iters_used": 2}
    assert (tmp_path / "a.txt").read_text() == "hi"
    _assert_pairing(fc.seen_messages)


def test_loop_prose_only_two_nudges_then_no_action(tmp_path):
    """Nói mà không làm: đúng 2 NUDGE rồi phân loại no_action (không phải finished)."""
    fc = FakeClient([_Msg(content="I would write a file...")] * 3)
    out = run_agent("t", tmp_path, client=fc)
    assert out == {"finish_reason": "no_action", "iters_used": 3}
    nudges = [m for m in fc.seen_messages
              if isinstance(m, dict) and m.get("role") == "user"
              and "called no tool" in str(m.get("content", ""))]
    assert len(nudges) == 2, "nudge cap phải là ĐÚNG 2 lần"


def test_loop_nudge_recovery(tmp_path):
    """Prose → nudge → model tỉnh ra gọi tool → content → finished (nudge có tác dụng)."""
    fc = FakeClient([
        _Msg(content="let me think out loud"),
        _Msg(tool_calls=[_write_call()]),
        _Msg(content="done"),
    ])
    out = run_agent("t", tmp_path, client=fc)
    assert out == {"finish_reason": "finished", "iters_used": 3}
    assert (tmp_path / "a.txt").exists()


def test_loop_parallel_tools_with_finish(tmp_path):
    """[write_file, finish] cùng turn: CẢ HAI chạy, đủ 2 role:tool, rồi finished."""
    fc = FakeClient([
        _Msg(tool_calls=[
            _write_call(id="call_a"),
            _ToolCall("finish", json.dumps({"summary": "done"}), id="call_b"),
        ]),
    ])
    out = run_agent("t", tmp_path, client=fc)
    assert out == {"finish_reason": "finished", "iters_used": 1}
    assert (tmp_path / "a.txt").exists(), "tool đứng trước finish vẫn phải chạy"
    _assert_pairing(fc.seen_messages)
    tool_results = [m for m in fc.seen_messages
                    if isinstance(m, dict) and m.get("role") == "tool"]
    assert len(tool_results) == 2


def test_loop_max_iters_non_finish_tools_not_executed(tmp_path):
    """Turn cuối gọi tool thường → KHÔNG chạy tool, max_iters, và KHÔNG orphan tool_calls."""
    fc = FakeClient([_Msg(tool_calls=[_write_call()])])
    out = run_agent("t", tmp_path, max_iters=1, client=fc)
    assert out == {"finish_reason": "max_iters", "iters_used": 1}
    assert not (tmp_path / "a.txt").exists(), "tool result không ai đọc → không được chạy"
    _assert_pairing(fc.seen_messages)
    assert fc.seen_messages[-1].get("role") == "user", \
        "assistant msg chưa-chạy-tool phải được pop để giữ bất biến ghép cặp"


def test_loop_final_turn_finish_is_finished(tmp_path):
    """finish() trên turn cuối = finished (model ĐÃ tuyên bố xong), không phải max_iters."""
    fc = FakeClient([_Msg(tool_calls=[_ToolCall("finish",
                                                json.dumps({"summary": "ok"}))])])
    out = run_agent("t", tmp_path, max_iters=1, client=fc)
    assert out == {"finish_reason": "finished", "iters_used": 1}
    _assert_pairing(fc.seen_messages)


def test_loop_timeout_checked_before_first_call(tmp_path):
    """time_budget_s=0 → timeout NGAY, không có API call nào (pin semantics hiện tại:
    iters_used=1 = turn đã BƯỚC VÀO, nhất quán mọi nhánh — đã document trong docstring)."""
    fc = FakeClient([])
    out = run_agent("t", tmp_path, time_budget_s=0, client=fc)
    assert out == {"finish_reason": "timeout", "iters_used": 1}
    assert fc.calls == 0


def test_loop_api_error_is_classified(tmp_path):
    """OpenAIError từ SDK → api_error, không crash, không orphan message."""
    fc = FakeClient([OpenAIError("vllm down")])
    out = run_agent("t", tmp_path, client=fc)
    assert out == {"finish_reason": "api_error", "iters_used": 1}
    assert fc.seen_messages[-1].get("role") == "user", "không được append assistant dở dang"


def test_loop_empty_choices_is_api_error(tmp_path):
    """Response 200 nhưng choices=[] (vLLM lỗi lạ) → api_error, không IndexError."""
    fc = FakeClient(["empty"])
    out = run_agent("t", tmp_path, client=fc)
    assert out == {"finish_reason": "api_error", "iters_used": 1}


def test_loop_bad_json_args_repaired_in_history(tmp_path):
    """JSON-repair (trước đây chỉ REPL có) giờ tới được run_agent qua
    execute_turn: args hỏng → tool KHÔNG chạy, bản args trong history được
    thay "{}" (turn sau không 400), model nhận ERROR hướng dẫn retry."""
    bad_args = '{"path": "a.txt", "content": """boom"""}'  # triple-quote = JSON hỏng
    fc = FakeClient([
        _Msg(tool_calls=[_ToolCall("write_file", bad_args, id="call_bad")]),
        _Msg(content="done"),
    ])
    out = run_agent("t", tmp_path, client=fc)
    assert out == {"finish_reason": "finished", "iters_used": 2}
    assert not (tmp_path / "a.txt").exists(), "args hỏng thì tool không được chạy"
    asst = [m for m in fc.seen_messages
            if isinstance(m, dict) and m.get("role") == "assistant" and m.get("tool_calls")]
    assert asst[0]["tool_calls"][0]["function"]["arguments"] == "{}", \
        "history phải được sanitize để turn sau không 400"
    tool_msgs = [m for m in fc.seen_messages
                 if isinstance(m, dict) and m.get("role") == "tool"]
    assert tool_msgs[0]["content"].startswith("ERROR: invalid JSON")
    _assert_pairing(fc.seen_messages)


def test_execute_turn_keyboard_interrupt_keeps_pairing(tmp_path, monkeypatch):
    """Ctrl+C giữa tool dài: execute_turn điền placeholder cho MỌI call còn lại
    (pairing nguyên vẹn) RỒI MỚI re-raise — REPL break turn, eval thoát sạch."""
    import pytest

    from src import agent as A

    def _boom(name, arguments, workspace):
        raise KeyboardInterrupt

    monkeypatch.setattr(A, "execute_tool", _boom)
    calls = [
        {"id": "call_1", "name": "write_file", "arguments": '{"path": "a", "content": "x"}'},
        {"id": "call_2", "name": "write_file", "arguments": '{"path": "b", "content": "y"}'},
    ]
    messages = [{"role": "assistant", "content": None, "tool_calls": [
        {"id": c["id"], "type": "function",
         "function": {"name": c["name"], "arguments": c["arguments"]}}
        for c in calls
    ]}]
    with pytest.raises(KeyboardInterrupt):
        A.execute_turn(calls, messages, tmp_path)
    tool_msgs = [m for m in messages if m.get("role") == "tool"]
    assert [m["tool_call_id"] for m in tool_msgs] == ["call_1", "call_2"], \
        "cả 2 call phải có result (call bị ngắt + call bị skip)"
    assert "interrupted" in tool_msgs[0]["content"]
    assert "skipped" in tool_msgs[1]["content"]
