"""
06_chat.py — Interactive REPL chat với coding agent (giống Claude Code / Codex).

KHÁC `05_agent_loop.py` Ở ĐÂU
  05 là ONE-SHOT: gõ task qua argv → chạy đến hết → thoát.
  06 là REPL nhiều turn: bạn gõ → agent stream từng token + thinking + tool calls
  → kết thúc 1 lượt → bạn gõ tiếp → ...
  History tích lũy trong cùng 1 session (giống chat với Claude Code).

3 TÍNH NĂNG MỚI SO VỚI 05
  1. STREAMING: `stream=True` → nhận từng delta thay vì chờ cả response.
  2. THINKING HIỆN REAL-TIME: vLLM khởi động với `--reasoning-parser qwen3`
     nên Qwen3-14B emit `<think>...</think>` được tách thành field `reasoning_content`
     riêng. Mình in màu xám ngay khi nó chảy về.
  3. TOOL CALL STEP-BY-STEP: hiện ngay tool name + args (green) và result (yellow)
     trước khi model viết câu trả lời tiếp.

LỆNH SLASH
  /exit, /quit, /q     thoát
  /clear, /reset       xoá history (giữ system prompt)
  /think               bật chế độ deep thinking (model thinks before each turn)
  /nothink             tắt thinking (fast mode — mặc định)
  /mode                xem mode hiện tại
  /help                hiện help

CÁCH CHẠY
  cd ~/code/coding-agent && source .venv/bin/activate
  python examples/06_chat.py                              # workspace = demo_repo
  python examples/06_chat.py --workspace /tmp/playground  # workspace khác
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Khi chạy `python examples/06_chat.py`, Python chỉ đặt examples/ vào sys.path.
# Thêm project root để `from src...` import được.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from openai import OpenAI

# Tái dùng tools + prompt y nguyên — không duplicate.
from src.tools import TOOL_SCHEMAS, execute_tool, set_workspace
from src.prompts import SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# ANSI colors — em tô màu để phân biệt: bạn / thinking / assistant / tool / result.
# ---------------------------------------------------------------------------
WHITE = "\033[97m"       # thinking (trắng sáng, dễ nhìn trên nền tối)
BLUE = "\033[1;34m"      # banner + turn header
GREEN = "\033[1;32m"     # tool call (đang gọi tool)
YELLOW = "\033[33m"      # tool result
MAGENTA = "\033[1;35m"   # assistant content (visible reply)
CYAN = "\033[1;36m"      # user prompt + system info
RED = "\033[1;31m"       # error / warn
RESET = "\033[0m"        # reset


# ---------------------------------------------------------------------------
# Auto-compaction — giữ conversation history dưới context limit
# ---------------------------------------------------------------------------
#
# PROBLEM: Qwen3-14B `max_model_len=32768`. Mỗi turn append assistant + tool
# messages — qua 20-30 turns, history dễ vượt 32K → vLLM trả 400 "context
# length exceeded" và REPL crash. Claude Code giải quyết bằng auto-summarize:
# khi history quá dài, gom các turn cũ thành 1 summary và giữ recent turns
# nguyên xi. Tool ở đây implement đúng pattern đó.
#
# THRESHOLDS (tunable constants):
#   COMPACT_THRESHOLD_TOKENS = 24000 → trigger ở ~75% context (chừa headroom)
#   KEEP_RECENT_MESSAGES     = 10    → giữ 10 message gần nhất verbatim
# ---------------------------------------------------------------------------

# Trigger point: khi estimated tokens vượt threshold, auto-compact TRƯỚC
# stream call tiếp theo. 24K = ~75% của max_model_len 32K, đủ headroom cho
# next response (~2K tokens) + tool results.
COMPACT_THRESHOLD_TOKENS = 24000

# max_model_len của Qwen3-14B trong vLLM. Dùng làm mẫu số khi hiển thị %
# context đã dùng (/tokens). Để hằng số riêng thay vì hardcode 32768 rải rác.
MAX_MODEL_LEN = 32768

# Số messages cuối giữ nguyên không summarize. 10 = đủ cho model nhớ context
# 5-6 turn gần nhất (user + assistant + tool, mix 2-3 messages/turn).
# Tăng → ít compaction lợi ích nhưng tốn tokens; giảm → mất context dễ.
KEEP_RECENT_MESSAGES = 10


def estimate_tokens(messages: list) -> int:
    """Ước lượng số token của messages list. KHÔNG cần exact.

    HEURISTIC: tổng chars / 4. Tại sao 4?
      - Qwen3 tokenizer (BPE) trung bình ~3.5-4.5 chars/token cho English
      - Vietnamese hơi tốn hơn (~3 chars/token) vì có diacritics
      - Code (Python) thường ~3.5 chars/token
      - Lấy 4 làm middle ground, sai số ~20-30% nhưng OK cho trigger decision
        (chúng ta chỉ cần biết "có gần limit chưa?", không cần exact count)

    Tại sao không dùng tiktoken/transformers tokenizer thật?
      - tiktoken là OpenAI tokenizer, không khớp Qwen3
      - HuggingFace tokenizer cần load weights (~50MB), startup cost
      - Khác biệt 20% không impact correctness — threshold có buffer rồi

    COUNTED:
      - message['content'] (str hoặc None)
      - message['tool_call_id'] (cho role=tool messages)
      - tool_calls[i].function.name + arguments (cho role=assistant)
    """
    total = 0
    for m in messages:
        # content có thể None khi assistant message chỉ chứa tool_calls.
        # `or ""` để convert None → empty string (len=0).
        content = m.get("content") or ""
        total += len(content)

        # role=tool messages có tool_call_id (~10 chars/UUID-like) — nhỏ
        # nhưng cộng dồn 30 turns có thể đáng kể.
        if m.get("tool_call_id"):
            total += len(m["tool_call_id"])

        # role=assistant với tool_calls — đếm function name + arguments JSON.
        # Đây thường là phần lớn nhất của 1 turn (write_file content có thể
        # vài KB).
        for tc in m.get("tool_calls") or []:
            fn = tc.get("function", {})
            total += len(fn.get("name", "")) + len(fn.get("arguments", ""))

    # Integer divide để trả int (caller so sánh với threshold int).
    return total // 4


def compact_messages(
    messages: list,
    client: OpenAI,
    model: str,
    keep_recent: int = KEEP_RECENT_MESSAGES,
) -> tuple[list, str]:
    """Summarize old messages thành 1 system msg, giữ recent N verbatim.

    INPUT: messages list (mutable, NOT modified in-place — return new list).
    RETURN: (new_messages, status_message_for_user).

    STRATEGY:
      Before:  [system, m1, m2, m3, ..., m25]   (vd 26 messages)
      After:   [system, summary_system, m16, ..., m25]  (12 messages)
                ↑       ↑               ↑
                kept    new (LLM-gen)   last 10 verbatim

    CRITICAL — SPLIT POINT MUST BE 'user' role:
      OpenAI API yêu cầu MỌI role=tool message phải có assistant.tool_calls
      ở phía trước với matching tool_call_id. Nếu compact cắt giữa pair
      (vd assistant.tool_calls -> tool_result), tool message thành orphan
      → API reject 400.

      Solution: walk FORWARD từ initial split point đến khi gặp user message.
      User messages luôn là turn boundaries clean (không có tool dependency).
      `recent` bắt đầu tại đúng 1 user message → tool message đầu tiên trong
      `recent` (nếu có) chắc chắn có assistant.tool_calls đi trước nó BÊN TRONG
      `recent` → không bao giờ orphan.

      Vì sao walk FORWARD (giảm số message giữ lại) chứ không BACKWARD?
      Forward chỉ làm `recent` ngắn hơn → an toàn với context budget. Backward
      sẽ kéo thêm message vào `recent`, có thể làm history phình to — đi ngược
      mục tiêu compact. Worst case forward không thấy user → bail (không compact).

    LLM CALL FOR SUMMARY:
      - thinking=OFF cho speed (summary là deterministic, không cần reason)
      - max_tokens=600 đủ cho ~400 words summary
      - Prompt yêu cầu preserve: tool calls, file paths, decisions, errors
        (đây là info quan trọng nhất cho model resume task)
    """
    # GUARD: nếu history quá ngắn, không có gì để compact. +1 để account
    # cho system message ở index 0 (luôn giữ).
    if len(messages) <= keep_recent + 1:
        return messages, "no compaction needed (too few messages)"

    # STEP 1: Tìm split point — bắt đầu từ -keep_recent, walk forward đến
    # khi gặp user message (clean turn boundary).
    split = len(messages) - keep_recent
    while split < len(messages) and messages[split].get("role") != "user":
        split += 1

    # Nếu walk hết list mà không thấy user (rare edge case — vd toàn tool
    # messages cuối), bail. Tốt hơn không compact còn hơn compact sai.
    if split >= len(messages):
        return messages, "compaction skipped (no clean user boundary in recent window)"

    # STEP 2: Tách messages thành 3 phần.
    system_msg = messages[0]                # giữ nguyên — định nghĩa agent persona
    to_summarize = messages[1:split]        # phần này sẽ bị compact thành 1 summary
    recent = messages[split:]               # giữ nguyên — model cần immediate context

    # Edge: nếu nothing to summarize (split=1), bail.
    if not to_summarize:
        return messages, "no compaction needed (nothing between system and recent)"

    # STEP 3: Render to_summarize thành plain text cho LLM đọc.
    # Format thân thiện với model — không cần re-serialize full JSON, chỉ
    # cần text representation của (role, content, tool calls).
    rendered = []
    for m in to_summarize:
        role = m.get("role", "?")

        if role == "tool":
            # Tool result — cap 500 chars per (tool results có thể rất dài,
            # vd pytest output 5KB). Summary không cần full content, chỉ
            # cần biết "tool X returned roughly Y".
            content = (m.get("content") or "")[:500]
            rendered.append(f"[tool result] {content}")

        elif role == "assistant":
            # Assistant: content (visible text) + tool_calls (actions taken)
            content = m.get("content") or ""
            tcs = m.get("tool_calls") or []
            line = f"[assistant] {content}"

            # List tool calls model đã emit — chỉ name + first 200 chars args
            # (đủ để summarizer hiểu "agent đã làm gì").
            for tc in tcs:
                fn = tc.get("function", {})
                args_preview = (fn.get("arguments", "") or "")[:200]
                line += f"\n  → {fn.get('name', '?')}({args_preview})"
            rendered.append(line)

        else:
            # role=user or system — chỉ content. Cap 500 chars để safe.
            rendered.append(f"[{role}] {(m.get('content') or '')[:500]}")

    history_text = "\n".join(rendered)

    # STEP 4: Gọi LLM để summarize. Dùng SEPARATE message list (không phải
    # `messages` đang summarize) — đây là fresh "summarization session".
    # Thinking OFF cho speed; max_tokens=600 (≈400 words).
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

    # STEP 5: Build new messages list.
    # [original system, summary as system, ...recent verbatim]
    # Prefix "[Earlier conversation summary]" giúp model phân biệt với
    # original system prompt khi đọc.
    new_messages = [
        system_msg,
        {
            "role": "system",
            "content": f"[Earlier conversation summary]\n{summary}",
        },
        *recent,
    ]

    # STEP 6: Build status message — show savings cho user/log.
    before_tok = estimate_tokens(messages)
    after_tok = estimate_tokens(new_messages)
    status = (f"compacted {len(messages)}→{len(new_messages)} messages, "
              f"~{before_tok}→~{after_tok} tokens "
              f"({100 * (1 - after_tok/max(before_tok, 1)):.0f}% reduction)")

    return new_messages, status


def handle_slash(cmd: str, messages: list, system_prompt: str) -> bool:
    """Xử lý slash command. Return True nếu đã xử lý xong (skip LLM call)."""
    c = cmd.strip().lower()
    if c in ("/exit", "/quit", "/q"):
        print(f"{CYAN}Bye.{RESET}")
        sys.exit(0)
    if c in ("/clear", "/reset"):
        # Xoá history nhưng giữ lại system prompt — mỗi conversation cần system.
        messages.clear()
        messages.append({"role": "system", "content": system_prompt})
        print(f"{CYAN}Conversation cleared.{RESET}")
        return True
    if c in ("/help", "/?"):
        # Liệt kê ĐẦY ĐỦ slash commands — kể cả những lệnh xử lý inline trong chat()
        # (/think /nothink /mode /compact /tokens). User gõ /help phải thấy mọi lệnh có thể dùng.
        print(f"{CYAN}Commands: /exit  /clear  /help  /think  /nothink  /mode  /compact  /tokens{RESET}")
        return True
    if c.startswith("/"):
        print(f"{RED}Unknown command: {cmd}. Try /help.{RESET}")
        return True
    return False


def stream_one_turn(
    client: OpenAI,
    model: str,
    messages: list,
    thinking_enabled: bool = False,
) -> tuple[str, list[dict]]:
    """Stream 1 round-trip với model. Trả về (content_buf, tool_calls).

    In ra thinking (white) + content (magenta) ngay khi delta về.
    Accumulate tool_calls từ các chunk vì OpenAI stream chia tool_calls qua nhiều delta.

    thinking_enabled: bật/tắt block <think>...</think> của Qwen3 qua chat template.
    """
    # `stream=True` đổi return type: thay vì 1 ChatCompletion, ta nhận iterator
    # của các ChatCompletionChunk. Mỗi chunk có `delta` chứa MỘT MẢNH của response.
    # `extra_body.chat_template_kwargs.enable_thinking` — Qwen3 native flag để
    # bật/tắt thinking. vLLM forward thẳng sang chat template.
    # type:ignore: messages là list[dict] và TOOL_SCHEMAS cũng là list[dict].
    # Không ép sang OpenAI TypedDict cho đỡ ràng buộc cứng — runtime hợp lệ
    # vì dict shape khớp schema, Pylance chỉ kêu vì TypedDict strict.
    stream = client.chat.completions.create(  # type: ignore[arg-type,call-overload]
        model=model,
        messages=messages,
        tools=TOOL_SCHEMAS,
        tool_choice="auto",
        max_tokens=2048,
        stream=True,
        extra_body={"chat_template_kwargs": {"enable_thinking": thinking_enabled}},
    )

    content_buf = ""        # tích luỹ visible content qua các delta (cần trả về để lưu history)
    # Thinking KHÔNG cần tích luỹ: ta chỉ in nó ra để user xem, không lưu vào
    # history (reasoning_content không gửi lại model ở turn sau). `in_thinking`
    # đủ để biết đã in header chưa — không cần buffer riêng.
    # Tool calls về theo từng mảnh: id, name, arguments có thể đến ở các delta khác nhau.
    # Dict key = index (do model có thể gọi nhiều tool song song).
    tool_calls: dict[int, dict] = {}

    in_thinking = False     # đang trong block thinking?
    in_content = False      # đang trong block content?

    for chunk in stream:
        # Phòng trường hợp chunk rỗng (vLLM thi thoảng emit chunk không choices).
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta

        # --- 1. REASONING (thinking) ---
        # vLLM với `--reasoning-parser qwen3` tách `<think>...</think>` ra field
        # riêng. Field name là `reasoning_content` trong vLLM (một số version là
        # `reasoning` — getattr với fallback để tương thích cả hai).
        r = getattr(delta, "reasoning_content", None) or getattr(delta, "reasoning", None)
        if r:
            if not in_thinking:
                # Header chỉ in 1 lần khi bắt đầu thinking — không spam.
                print(f"\n{CYAN}[thinking]{RESET}", flush=True)
                in_thinking = True
                in_content = False
            # end="" + flush=True → ghi từng mẩu lên cùng dòng, không buffer.
            # Dùng WHITE thay vì GRAY+DIM cho dễ đọc.
            print(f"{WHITE}{r}{RESET}", end="", flush=True)

        # --- 2. VISIBLE CONTENT ---
        if delta.content:
            if not in_content:
                # Nếu vừa thoát thinking → xuống dòng để close block đó.
                if in_thinking:
                    print()
                print(f"\n{MAGENTA}[assistant]{RESET}", flush=True)
                in_content = True
                in_thinking = False
            print(f"{MAGENTA}{delta.content}{RESET}", end="", flush=True)
            content_buf += delta.content

        # --- 3. TOOL CALLS (delta-streamed) ---
        # tool_calls trong delta là LIST của các tool_call delta. Mỗi tool_call
        # delta có .index (vị trí trong list cuối cùng), .id (chỉ về ở chunk đầu),
        # .function.name (cũng thường ở chunk đầu), .function.arguments (chia thành
        # nhiều chunk vì JSON args có thể dài).
        if delta.tool_calls:
            for tcd in delta.tool_calls:
                idx = tcd.index
                if idx not in tool_calls:
                    tool_calls[idx] = {"id": "", "name": "", "arguments": ""}
                if tcd.id:
                    tool_calls[idx]["id"] += tcd.id
                if tcd.function:
                    if tcd.function.name:
                        tool_calls[idx]["name"] += tcd.function.name
                    if tcd.function.arguments:
                        tool_calls[idx]["arguments"] += tcd.function.arguments

    # Hết stream — xuống dòng cho đẹp.
    print()

    return content_buf, [tool_calls[i] for i in sorted(tool_calls)]


def chat(workspace: Path, max_tool_turns: int = 15) -> None:
    """Vòng lặp REPL chính."""
    load_dotenv()
    base_url = os.environ["VLLM_BASE_URL"]
    model = os.environ["VLLM_MODEL_NAME"]
    api_key = os.environ.get("VLLM_API_KEY", "not-needed")

    client = OpenAI(base_url=base_url, api_key=api_key)
    set_workspace(workspace)

    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Thinking mode (sticky). Default OFF — fast cho task đơn giản (greeting,
    # câu hỏi ngắn). User gõ /think để bật trước khi giao task phức tạp.
    thinking_enabled = False

    # Banner — giống style Claude Code / Codex.
    print(f"{BLUE}{'═' * 60}{RESET}")
    print(f"{BLUE}  coding-agent (REPL chat){RESET}")
    print(f"  model     : {model}")
    print(f"  endpoint  : {base_url}")
    print(f"  workspace : {workspace}")
    print(f"  commands  : /exit  /clear  /help  /think  /nothink  /mode  /compact  /tokens")
    print(f"  mode      : fast (thinking off) — gõ /think để bật deep thinking")
    print(f"  compact   : auto-trigger ở ~{COMPACT_THRESHOLD_TOKENS} tokens (giữ {KEEP_RECENT_MESSAGES} msg gần nhất)")
    print(f"{BLUE}{'═' * 60}{RESET}")

    while True:
        # --- Lấy input từ user ---
        try:
            user_input = input(f"\n{CYAN}you> {RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{CYAN}Bye.{RESET}")
            return

        if not user_input:
            continue

        # --- Thinking mode toggle (sticky) ---
        # Tách riêng khỏi handle_slash vì cần mutate `thinking_enabled` (closure var).
        low = user_input.lower()
        if low in ("/think", "/deep"):
            thinking_enabled = True
            print(f"{CYAN}Thinking mode: ON (deep — model thinks before each turn){RESET}")
            continue
        if low in ("/nothink", "/fast"):
            thinking_enabled = False
            print(f"{CYAN}Thinking mode: OFF (fast — model responds directly){RESET}")
            continue
        if low == "/mode":
            m = "ON (deep)" if thinking_enabled else "OFF (fast)"
            print(f"{CYAN}Thinking mode: {m}{RESET}")
            continue

        # --- Compaction commands (inline vì cần client + model từ closure) ---
        # /tokens: show estimate without doing anything. Useful trước khi
        # quyết định có /compact manually hay không.
        if low in ("/tokens", "/tok"):
            tok = estimate_tokens(messages)
            pct = 100 * tok / MAX_MODEL_LEN
            # Màu cảnh báo theo mức độ gần threshold: đỏ = đã vượt (auto-compact
            # sẽ chạy ở turn sau), vàng = đang tiến sát, xanh = còn thoải mái.
            warn_level = COMPACT_THRESHOLD_TOKENS - 4000  # ~20K, ngưỡng "đang sát"
            color = RED if tok > COMPACT_THRESHOLD_TOKENS else (YELLOW if tok > warn_level else GREEN)
            print(f"{color}Token estimate: ~{tok} / {MAX_MODEL_LEN // 1000}K ({pct:.0f}%)  "
                  f"[threshold: {COMPACT_THRESHOLD_TOKENS}]{RESET}")
            continue

        # /compact: trigger summarization NGAY, kể cả khi chưa đụng threshold.
        # Useful khi user biết tasks sắp tới sẽ tốn nhiều tokens và muốn pre-free
        # context budget.
        if low == "/compact":
            print(f"{CYAN}Compacting conversation history...{RESET}")
            try:
                # in-place replace: messages[:] = new_list. Phải dùng slice
                # assignment thay vì reassign messages = new_list, vì variable
                # `messages` là local trong chat() và sub-functions vẫn còn ref.
                new_msgs, status = compact_messages(messages, client, model)
                messages[:] = new_msgs
                print(f"{CYAN}{status}{RESET}")
            except Exception as e:
                # Compaction là best-effort — nếu LLM call fail, KHÔNG được crash
                # REPL. Báo lỗi, để user tự xử lý (e.g. /clear).
                print(f"{RED}Compaction failed: {e}{RESET}")
            continue

        if handle_slash(user_input, messages, SYSTEM_PROMPT):
            continue

        # --- Append user message vào history (memory) ---
        messages.append({"role": "user", "content": user_input})

        # --- AUTO-COMPACT CHECK (before inner loop starts) ---
        # Kiểm tra token estimate TRƯỚC mỗi inner loop. Nếu vượt threshold,
        # tự động summarize trước khi gửi request → tránh "context length
        # exceeded" 400 từ vLLM.
        #
        # Trigger ở threshold 24K (~75% của 32K) chứ không 31K — để chừa
        # buffer cho:
        #   - response tokens (~2K max_tokens)
        #   - inaccuracy của estimate_tokens (±20-30%)
        #   - tool results spike trong inner loop trước khi compact lần sau
        #
        # Compaction tốn 1 extra LLM call (~3-5s), nhưng rẻ hơn nhiều so với
        # context overflow crash buộc user gõ /clear (mất toàn bộ history).
        tok_estimate = estimate_tokens(messages)
        if tok_estimate > COMPACT_THRESHOLD_TOKENS:
            print(f"{YELLOW}[auto-compact] ~{tok_estimate} tokens > threshold "
                  f"{COMPACT_THRESHOLD_TOKENS}, summarizing history...{RESET}")
            try:
                new_msgs, status = compact_messages(messages, client, model)
                messages[:] = new_msgs
                print(f"{YELLOW}[auto-compact] {status}{RESET}")
            except Exception as e:
                # Best-effort: nếu compact fail, vẫn cứ thử gửi request original
                # (có thể vẫn dưới limit nếu estimate sai cao). Worse case
                # vLLM trả 400 và except block bên dưới handle.
                print(f"{RED}[auto-compact] failed: {e} — proceeding without compaction{RESET}")

        # --- Inner agent loop ---
        # Sau khi user nói 1 câu, model có thể cần GỌI TOOL NHIỀU LẦN trước khi
        # đưa ra câu trả lời cuối. Mỗi vòng inner = 1 round-trip stream.
        # Vòng dừng khi model không gọi tool nào nữa (= câu trả lời cuối cho user).
        # `_turn` (prefix `_`) báo linter biết biến không dùng trong body —
        # range() chỉ để giới hạn iterations, không cần index thật.
        for _turn in range(1, max_tool_turns + 1):
            try:
                content_buf, tool_calls = stream_one_turn(client, model, messages, thinking_enabled)
            except KeyboardInterrupt:
                # Ctrl+C giữa stream → cho user ngắt agent mà không thoát REPL.
                print(f"\n{RED}[interrupted]{RESET}")
                # Append assistant placeholder để conversation không lệch.
                messages.append({"role": "assistant", "content": "[interrupted by user]"})
                break
            except Exception as e:
                print(f"\n{RED}API error: {e}{RESET}")
                # Rollback TOÀN BỘ messages thuộc turn này — nếu lỗi xảy ra GIỮA inner
                # loop (sau khi đã append assistant + role=tool messages), chỉ pop user
                # msg sẽ để lại orphan tool messages → API reject ở turn sau.
                # Cách an toàn: pop từ cuối cho tới khi gặp user message gần nhất, rồi
                # pop luôn nó để user gõ lại từ đầu.
                while messages and messages[-1].get("role") != "user":
                    messages.pop()
                if messages and messages[-1].get("role") == "user":
                    messages.pop()
                break

            # --- Validate JSON args TRƯỚC KHI append vào history ---
            # Nếu model emit bad JSON (vd Python triple-quote `"""..."""`),
            # vLLM sẽ trả 400 ở turn sau vì history chứa tool_call args không
            # parse được. Mark broken để:
            #   (a) Thay arguments bằng "{}" trong history → vLLM happy.
            #   (b) Trả error message rõ cho model retry với JSON đúng.
            for tc in tool_calls:
                try:
                    if tc["arguments"]:
                        json.loads(tc["arguments"])
                except json.JSONDecodeError as e:
                    tc["_bad_json"] = True
                    tc["_bad_json_error"] = str(e)

            # --- Build assistant message để append vào history ---
            # Phải giữ NGUYÊN `tool_calls` field cho turn sau, giống agent.py
            # (xem comment dài về model_dump trong agent.py line 154-163).
            asst_msg: dict = {"role": "assistant", "content": content_buf or None}
            if tool_calls:
                asst_msg["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            # Bad JSON → "{}" để history hợp lệ. Tool result vẫn nói lỗi.
                            "arguments": "{}" if tc.get("_bad_json") else tc["arguments"],
                        },
                    }
                    for tc in tool_calls
                ]
            messages.append(asst_msg)

            # --- Nếu model không gọi tool → câu trả lời cuối, ra ngoài inner loop ---
            if not tool_calls:
                break

            # --- Thực thi từng tool call, append result vào history ---
            # INVARIANT: asst_msg vừa append có N tool_calls. API yêu cầu MỖI
            # tool_call phải có đúng 1 role=tool result với matching id ở phía
            # sau. Nếu thiếu (vd Ctrl+C giữa execute_tool của tool dài như
            # run_tests), tool_call thành orphan → vLLM 400 ở turn sau. Vì vậy
            # ta dùng `interrupted` flag: khi user ngắt, vẫn append placeholder
            # result cho MỌI tool còn lại để giữ pairing hợp lệ, rồi mới break.
            interrupted = False
            for tc in tool_calls:
                args_str = tc["arguments"]
                # Cắt args dài cho gọn khi in (model vẫn nhận full qua history).
                args_preview = args_str if len(args_str) <= 200 else args_str[:200] + "...[truncated]"
                print(f"{GREEN}▶ {tc['name']}({args_preview}){RESET}")

                if interrupted:
                    # Đã bị Ctrl+C ở tool trước — không chạy nữa, chỉ điền
                    # placeholder để tool_call này không bị orphan.
                    result = "[skipped: user interrupted tool execution]"
                elif tc.get("_bad_json"):
                    # Không gọi execute_tool — args không parse được.
                    # Error message này được gửi NGƯỢC lại model. Giữ ENGLISH-ONLY
                    # vì Qwen3 instruct tuned trên English; trộn Vietnamese giảm
                    # tỉ lệ retry thành công (em đã quan sát qua demo trước).
                    result = (
                        f"ERROR: invalid JSON in arguments: {tc['_bad_json_error']}\n"
                        "Retry with valid JSON. Escape newlines as \\n and double-quotes as \\\". "
                        "Do NOT use Python triple-quote (\"\"\") inside JSON strings."
                    )
                else:
                    try:
                        result = execute_tool(tc["name"], args_str)
                    except KeyboardInterrupt:
                        # Ctrl+C giữa 1 tool dài. Đánh dấu interrupted để các tool
                        # còn lại chỉ điền placeholder (giữ pairing), không crash REPL.
                        print(f"\n{RED}[interrupted]{RESET}")
                        interrupted = True
                        result = "[interrupted: user cancelled tool execution]"

                result_preview = result if len(result) <= 500 else result[:500] + "...[truncated]"
                print(f"{YELLOW}  ↳ {result_preview}{RESET}")

                # role=tool message — tool_call_id PHẢI khớp với tc.id để API
                # link result với call. Sai id → API reject conversation.
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })

            # Nếu user đã ngắt giữa tool execution → kết thúc turn này (history
            # vẫn hợp lệ vì mọi tool_call đã có result). Không chạy stream tiếp.
            if interrupted:
                break
            # Loop sang turn tiếp theo — model sẽ "thấy" tool results vừa append.
        else:
            # Chạy hết max_tool_turns mà model vẫn gọi tool → cảnh báo.
            print(f"{RED}Hit max_tool_turns={max_tool_turns}. Stopping this turn.{RESET}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Interactive REPL chat with the coding agent (Claude-Code-style).",
    )
    parser.add_argument(
        "--workspace",
        default=str(Path(__file__).resolve().parent.parent / "demo_repo"),
        help="Sandbox directory the tools may read/write/exec inside (default: demo_repo).",
    )
    parser.add_argument(
        "--max-tool-turns", type=int, default=15,
        help="Max tool-call iterations between each user message (default: 15).",
    )
    args = parser.parse_args()

    # Silence stdlib logging trong tools.py để không xen ngang stream output.
    # Chat REPL tự quản lý mọi print rồi.
    logging.basicConfig(level=logging.WARNING)

    chat(Path(args.workspace), args.max_tool_turns)
    return 0


if __name__ == "__main__":
    sys.exit(main())
