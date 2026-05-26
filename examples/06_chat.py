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
        # (/think /nothink /mode). User gõ /help phải thấy mọi lệnh có thể dùng.
        print(f"{CYAN}Commands: /exit  /clear  /help  /think  /nothink  /mode{RESET}")
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
    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=TOOL_SCHEMAS,
        tool_choice="auto",
        max_tokens=2048,
        stream=True,
        extra_body={"chat_template_kwargs": {"enable_thinking": thinking_enabled}},
    )

    content_buf = ""        # tích luỹ visible content qua các delta
    reasoning_buf = ""      # tích luỹ thinking (chỉ dùng để biết đã in chưa)
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
            reasoning_buf += r

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
    print(f"  commands  : /exit  /clear  /help  /think  /nothink  /mode")
    print(f"  mode      : fast (thinking off) — gõ /think để bật deep thinking")
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

        if handle_slash(user_input, messages, SYSTEM_PROMPT):
            continue

        # --- Append user message vào history (memory) ---
        messages.append({"role": "user", "content": user_input})

        # --- Inner agent loop ---
        # Sau khi user nói 1 câu, model có thể cần GỌI TOOL NHIỀU LẦN trước khi
        # đưa ra câu trả lời cuối. Mỗi vòng inner = 1 round-trip stream.
        # Vòng dừng khi model không gọi tool nào nữa (= câu trả lời cuối cho user).
        for turn in range(1, max_tool_turns + 1):
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
            for tc in tool_calls:
                args_str = tc["arguments"]
                # Cắt args dài cho gọn khi in (model vẫn nhận full qua history).
                args_preview = args_str if len(args_str) <= 200 else args_str[:200] + "...[truncated]"
                print(f"{GREEN}▶ {tc['name']}({args_preview}){RESET}")

                if tc.get("_bad_json"):
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
                    result = execute_tool(tc["name"], args_str)

                result_preview = result if len(result) <= 500 else result[:500] + "...[truncated]"
                print(f"{YELLOW}  ↳ {result_preview}{RESET}")

                # role=tool message — tool_call_id PHẢI khớp với tc.id để API
                # link result với call. Sai id → API reject conversation.
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })
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
