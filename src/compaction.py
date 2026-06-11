"""
compaction.py — context compaction: ước lượng token + summarize history cũ.

VÌ SAO TÁCH RA src/ (trước đây nằm trong cli/chat.py):
  - Đây là module "sâu" thật sự: interface nhỏ (messages, client, model) →
    (new_messages, status), nhưng giấu các bất biến dễ vỡ nhất của message
    list (xem CRITICAL bên dưới). Nó nằm trong cli/ thì KHÔNG test được
    (cli/ không phải package) — logic nhiều bất biến nhất repo lại 0 test.
  - README bán compaction như headline feature → nó xứng đáng có nhà thật
    + unit test thật (tests/test_compaction.py).
  - cli/chat.py giữ phần CHÍNH SÁCH (ngưỡng auto-trigger từ models.json);
    file này giữ phần CƠ CHẾ (ước lượng + cắt + summarize) — tách bạch
    policy/mechanism.

Hai hàm public:
  estimate_tokens(messages)            -> int  (heuristic chars/4, KHÔNG exact)
  compact_messages(messages, client, model, keep_recent=10)
                                       -> (new_messages, status_str)
"""

from __future__ import annotations

from openai import OpenAI

# Số messages cuối giữ nguyên không summarize. 10 = đủ cho model nhớ context
# 5-6 turn gần nhất (user + assistant + tool, mix 2-3 messages/turn).
# Tăng → ít lợi ích compaction nhưng tốn tokens; giảm → mất context dễ.
KEEP_RECENT_MESSAGES = 10


def estimate_tokens(messages: list) -> int:
    """Ước lượng số token của messages list. KHÔNG cần exact.

    HEURISTIC: tổng chars / 4. Tại sao 4?
      - Qwen3 tokenizer (BPE) trung bình ~3.5-4.5 chars/token cho English
      - Vietnamese hơi tốn hơn (~3 chars/token) vì có diacritics
      - Code (Python) thường ~3.5 chars/token
      - Lấy 4 làm middle ground, sai số ~20-30% nhưng OK cho trigger decision
        (chỉ cần biết "có gần limit chưa?", không cần exact count)

    Tại sao không dùng tiktoken/transformers tokenizer thật?
      - tiktoken là OpenAI tokenizer, không khớp Qwen3
      - HuggingFace tokenizer cần load weights (~50MB), startup cost
      - Khác biệt 20% không impact correctness — threshold có buffer rồi

    COUNTED: content + tool_call_id (role=tool) + tool_calls name/arguments
    (role=assistant — write_file content vài KB thường là phần nặng nhất).
    """
    total = 0
    for m in messages:
        # content có thể None khi assistant message chỉ chứa tool_calls —
        # `or ""` để len() không crash.
        total += len(m.get("content") or "")
        # role=tool có tool_call_id (~10 chars) — nhỏ nhưng cộng dồn 30 turn.
        if m.get("tool_call_id"):
            total += len(m["tool_call_id"])
        # role=assistant với tool_calls: đếm name + arguments JSON.
        for tc in m.get("tool_calls") or []:
            fn = tc.get("function", {})
            total += len(fn.get("name", "")) + len(fn.get("arguments", ""))
    # `//` chia nguyên: 4 chars ≈ 1 token → tổng_chars // 4 ≈ số_token.
    return total // 4


def compact_messages(
    messages: list,
    client: OpenAI,
    model: str,
    keep_recent: int = KEEP_RECENT_MESSAGES,
) -> tuple[list, str]:
    """Summarize old messages thành 1 system msg, giữ recent N verbatim.

    INPUT: messages list (KHÔNG bị sửa in-place — trả về list MỚI).
    RETURN: (new_messages, status_message_for_user).

    STRATEGY:
      Before:  [system, m1, m2, m3, ..., m25]   (vd 26 messages)
      After:   [system, summary_system, m16, ..., m25]  (12 messages)
                ↑       ↑               ↑
                kept    new (LLM-gen)   last N verbatim

    CRITICAL — SPLIT POINT PHẢI là 'user' role:
      OpenAI API yêu cầu MỌI role=tool message phải có assistant.tool_calls
      ở phía trước với matching tool_call_id. Nếu compact cắt giữa pair
      (assistant.tool_calls -> tool_result), tool message thành orphan
      → API reject 400.

      Solution: walk FORWARD từ split point ban đầu đến khi gặp user message.
      User messages luôn là turn boundary sạch (không tool dependency) →
      tool message đầu tiên trong `recent` (nếu có) chắc chắn có
      assistant.tool_calls đi trước nó BÊN TRONG `recent` → không orphan.

      Vì sao walk FORWARD (giảm số message giữ lại) chứ không BACKWARD?
      Forward chỉ làm `recent` ngắn hơn → an toàn với context budget.
      Backward kéo thêm message vào `recent`, history phình to — đi ngược
      mục tiêu compact. Worst case forward không thấy user → bail (không compact).

    LLM CALL FOR SUMMARY:
      - thinking=OFF cho speed (summary là deterministic, không cần reason)
      - max_tokens=600 đủ cho ~400 words summary
      - Prompt yêu cầu preserve: tool calls, file paths, decisions, errors
        (info quan trọng nhất để model resume task)
    """
    # GUARD: history quá ngắn → không có gì để compact (+1 cho system ở index 0).
    if len(messages) <= keep_recent + 1:
        return messages, "no compaction needed (too few messages)"

    # STEP 1: tìm split point — từ -keep_recent walk forward đến user message.
    split = len(messages) - keep_recent
    while split < len(messages) and messages[split].get("role") != "user":
        split += 1
    # Walk hết list mà không thấy user (edge hiếm: toàn tool messages cuối)
    # → bail. Không compact còn hơn compact sai.
    if split >= len(messages):
        return messages, "compaction skipped (no clean user boundary in recent window)"

    # STEP 2: tách 3 phần — system giữ nguyên / phần bị tóm tắt / recent verbatim.
    system_msg = messages[0]
    to_summarize = messages[1:split]
    recent = messages[split:]
    if not to_summarize:
        return messages, "no compaction needed (nothing between system and recent)"

    # STEP 3: render to_summarize thành plain text cho LLM đọc. Tool result
    # cap 500 chars (pytest output 5KB → summary chỉ cần "tool X returned ~Y");
    # tool_calls chỉ cần name + 200 chars args đầu.
    rendered = []
    for m in to_summarize:
        role = m.get("role", "?")
        if role == "tool":
            rendered.append(f"[tool result] {(m.get('content') or '')[:500]}")
        elif role == "assistant":
            line = f"[assistant] {m.get('content') or ''}"
            for tc in m.get("tool_calls") or []:
                fn = tc.get("function", {})
                line += f"\n  → {fn.get('name', '?')}({(fn.get('arguments', '') or '')[:200]})"
            rendered.append(line)
        else:
            rendered.append(f"[{role}] {(m.get('content') or '')[:500]}")
    history_text = "\n".join(rendered)

    # STEP 4: gọi LLM summarize — SEPARATE message list (fresh "summarization
    # session", không phải `messages` đang tóm tắt). extra_body tắt thinking
    # của Qwen3 cho lần gọi này (vLLM forward thẳng vào chat template).
    summary_resp = client.chat.completions.create(  # type: ignore[arg-type,call-overload]
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You summarize agent conversation history concisely. "
                    "Be terse (<400 words). PRESERVE: tool calls made (with names "
                    "and file paths), files touched, key decisions, errors encountered, "
                    "current state of the work. DROP: chit-chat, redundant restating."
                ),
            },
            {
                "role": "user",
                "content": f"Summarize this agent trajectory:\n\n{history_text}",
            },
        ],
        max_tokens=600,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    summary = (summary_resp.choices[0].message.content or "").strip()

    # STEP 5: build list mới — prefix "[Earlier conversation summary]" giúp
    # model phân biệt summary với original system prompt.
    new_messages = [
        system_msg,
        {"role": "system", "content": f"[Earlier conversation summary]\n{summary}"},
        *recent,
    ]

    # STEP 6: status cho user/log — show savings.
    before_tok = estimate_tokens(messages)
    after_tok = estimate_tokens(new_messages)
    status = (f"compacted {len(messages)}→{len(new_messages)} messages, "
              f"~{before_tok}→~{after_tok} tokens "
              f"({100 * (1 - after_tok / max(before_tok, 1)):.0f}% reduction)")
    return new_messages, status
