"""
test_compaction.py — unit tests cho src/compaction.py (headline feature,
trước đây 0 test vì bị nhốt trong cli/chat.py không-import-được).

Quan trọng nhất: bất biến SPLIT-TẠI-USER — compaction không bao giờ được để
một role="tool" message mồ côi (mất assistant.tool_calls đứng trước nó) trong
recent window, vì history như vậy bị vLLM/OpenAI reject 400 ngay turn sau.
Lớp lỗi này chỉ lộ ra live, giữa demo, ở mốc ~24K token — đúng loại bug mà
unit test rẻ tiền bắt được còn smoke test thì không.
"""

from __future__ import annotations

from src.compaction import KEEP_RECENT_MESSAGES, compact_messages, estimate_tokens


# --- stub client: chỉ cần .chat.completions.create(...) trả content cố định ---

class _SummaryClient:
    def __init__(self, summary: str = "SUMMARY-TEXT"):
        self.calls = 0
        outer = self

        class _Completions:
            def create(self, **kwargs):
                outer.calls += 1
                outer.last_kwargs = kwargs

                class _Msg:
                    content = summary

                class _Choice:
                    message = _Msg()

                class _Resp:
                    choices = [_Choice()]

                return _Resp()

        class _Chat:
            completions = _Completions()

        self.chat = _Chat()


def _user(i):
    return {"role": "user", "content": f"user message {i}"}


def _asst(i, tool_call=False):
    m = {"role": "assistant", "content": f"assistant {i}"}
    if tool_call:
        m["content"] = None
        m["tool_calls"] = [{
            "id": f"call_{i}", "type": "function",
            "function": {"name": "write_file",
                         "arguments": '{"path": "a.txt", "content": "x"}'},
        }]
    return m


def _tool(i):
    return {"role": "tool", "tool_call_id": f"call_{i}", "content": f"result {i}"}


# --- estimate_tokens ---

def test_estimate_tokens_counts_content_and_tool_calls():
    base = [{"role": "user", "content": "x" * 400}]
    assert estimate_tokens(base) == 100  # 400 chars // 4
    with_tc = base + [_asst(1, tool_call=True), _tool(1)]
    # thêm assistant.tool_calls (name+arguments) và tool result phải TĂNG estimate
    assert estimate_tokens(with_tc) > estimate_tokens(base)
    assert isinstance(estimate_tokens(with_tc), int)


# --- compact_messages: guards ---

def test_compact_too_few_messages_is_noop():
    msgs = [{"role": "system", "content": "S"}] + [_user(i) for i in range(KEEP_RECENT_MESSAGES)]
    client = _SummaryClient()
    out, status = compact_messages(msgs, client, "m")
    assert out is msgs and "no compaction needed" in status
    assert client.calls == 0, "không được tốn LLM call khi không compact"


def test_compact_bails_without_user_boundary():
    # Recent window toàn assistant/tool (không có user nào từ split point trở đi)
    # → walk forward hết list → bail, KHÔNG compact sai.
    msgs = [{"role": "system", "content": "S"}, _user(0)]
    for i in range(1, 9):
        msgs += [_asst(i, tool_call=True), _tool(i)]
    client = _SummaryClient()
    out, status = compact_messages(msgs, client, "m", keep_recent=10)
    assert out is msgs and "skipped" in status
    assert client.calls == 0


# --- compact_messages: happy path + invariant ---

def test_compact_keeps_system_inserts_summary_preserves_recent():
    msgs = [{"role": "system", "content": "PERSONA"}]
    for i in range(12):
        msgs += [_user(i), {"role": "assistant", "content": f"reply {i}"}]
    client = _SummaryClient("đã làm X, file Y")
    out, status = compact_messages(msgs, client, "m", keep_recent=6)
    assert client.calls == 1
    assert out[0] == {"role": "system", "content": "PERSONA"}
    assert out[1]["role"] == "system"
    assert out[1]["content"].startswith("[Earlier conversation summary]")
    assert "đã làm X, file Y" in out[1]["content"]
    # recent window giữ VERBATIM (chính các dict cuối của input)
    n_recent = len(out) - 2
    assert out[2:] == msgs[-n_recent:]
    assert "compacted" in status and "%" in status


def test_compact_split_walks_forward_past_orphan_tool_boundary():
    """REGRESSION đáng giá nhất: split point ban đầu rơi TRÚNG một role=tool
    message → phải walk forward đến user message; message đầu tiên sau summary
    phải là role=user và không có tool message mồ côi trong output."""
    msgs = [{"role": "system", "content": "S"}]
    for i in range(6):
        msgs += [_user(i), _asst(i, tool_call=True), _tool(i)]
    # chọn keep_recent sao cho messages[-keep_recent] là role=tool
    keep = 5  # đếm ngược: tool5, asst5, user5, tool4, asst4 → [-5] = asst4... chỉnh để chắc chắn
    while msgs[len(msgs) - keep].get("role") != "tool":
        keep += 1
    client = _SummaryClient()
    out, _ = compact_messages(msgs, client, "m", keep_recent=keep)
    assert out[2]["role"] == "user", "message đầu sau summary PHẢI là user (turn boundary sạch)"
    # bất biến ghép cặp: mọi role=tool trong out phải có assistant.tool_calls
    # với id khớp đứng TRƯỚC nó
    seen_call_ids = set()
    for m in out:
        for tc in m.get("tool_calls") or []:
            seen_call_ids.add(tc["id"])
        if m.get("role") == "tool":
            assert m["tool_call_id"] in seen_call_ids, \
                f"orphan tool message: {m['tool_call_id']}"


def test_compact_summary_call_disables_thinking():
    """Summary call phải tắt thinking (deterministic + nhanh) — pin extra_body."""
    msgs = [{"role": "system", "content": "S"}]
    for i in range(12):
        msgs += [_user(i), {"role": "assistant", "content": f"r{i}"}]
    client = _SummaryClient()
    compact_messages(msgs, client, "m", keep_recent=4)
    eb = client.last_kwargs["extra_body"]
    assert eb == {"chat_template_kwargs": {"enable_thinking": False}}
