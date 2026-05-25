"""
agent.py — ReAct-style coding agent that uses tools to complete a task.

WHAT THIS FILE DOES
  Takes a natural-language goal (e.g. "Fix the failing tests in demo_repo/"),
  calls an LLM that may invoke any of the 10 tools defined in src/tools.py
  (read_file, write_file, apply_patch, multi_edit, grep_files, glob_files,
  list_dir, run_bash, run_python, spawn_subagent), keeps looping until the
  model is satisfied (returns content with no more tool_calls), or we hit
  `max_iters` and give up.

KEY DIFFERENCE FROM 01_chat.py
  01_chat.py only had `messages` + `content`. Here we ALSO have:
    - `tools=TOOL_SCHEMAS` in the API call (tell model what it can call)
    - `msg.tool_calls` to read (what the model wants to call)
    - role="tool" messages we append back (results of calls)

THE REACT LOOP (the heart of every modern coding agent — Claude/Codex use this)
   1. Send messages + tool schemas to the LLM.
   2. LLM responds either with plain content (it's done) OR with one or
      more tool_calls (it wants to do something).
   3. If content-only -> return. If tool_calls -> execute each, append the
      tool result to messages, loop.
   4. Stop if we exceed max_iters as a safety net.

WHEN DONE
  cd ~/code/coding-agent && source .venv/bin/activate
  python -m src.agent "Fix the failing tests in demo_repo/"
  (Or use examples/05_agent_loop.py for the prettier demo CLI.)
"""

from __future__ import annotations

# `logging` thay cho `print()` — sau này có thể redirect log vào file để
# thu thập trace cho fine-tuning ở Phase 3. Đây là Rule C trong AGENTS.md.
import logging
import os
import time
from pathlib import Path

# Đọc biến môi trường từ .env (BASE_URL, MODEL_NAME, API_KEY) — y hệt 01_chat.py.
from dotenv import load_dotenv

# OpenAI SDK — bao bọc HTTP/JSON, cho phép swap backend bằng cách đổi base_url.
# `OpenAIError` là base class của MỌI lỗi SDK (timeout, 5xx, kết nối rớt, 400 do
# context tràn). Bắt nó ở vòng lặp để 1 lỗi transient không kill cả run_agent —
# xem BƯỚC 1 bên dưới để hiểu vì sao việc này quan trọng cho tính đúng đắn.
from openai import OpenAI, OpenAIError

# TypedDict cho 1 message — chỉ dùng type hint giúp Pylance không kêu
# "list[dict] không phải Iterable[ChatCompletionMessageParam]" khi truyền vào create().
from openai.types.chat import ChatCompletionMessageParam

# Lấy 2 thứ từ tools.py:
#   - TOOL_SCHEMAS: danh sách JSON schema mô tả tools (model nhìn vào để biết gọi sao)
#   - execute_tool: dispatcher chạy tool theo name + args + workspace (sandbox dir)
# Lưu ý: KHÔNG còn `set_workspace` — workspace nay là tham số tường minh truyền
# thẳng vào execute_tool() ở mỗi lời gọi (xem run_agent), không phải global.
from src.tools import TOOL_SCHEMAS, execute_tool

# System prompt — tách ra file riêng để sau này dễ versioning cho training data.
from src.prompts import SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# ANSI color codes — tô màu output để prof nhìn dễ phân biệt từng phần.
# Không cần thư viện ngoài, chỉ là escape codes terminal hiểu sẵn.
# ---------------------------------------------------------------------------

# Mỗi mã ANSI là chuỗi đặc biệt báo terminal "đổi màu chữ kể từ đây".
# `\033[XXm` = bắt đầu màu. `\033[0m` = reset về mặc định.
class Color:
    HEADER = "\033[1;34m"   # bold blue — cho dòng "=== Turn N ==="
    TOOL = "\033[1;32m"     # bold green — cho dòng "[tool] tool_name(...)"
    RESULT = "\033[33m"     # yellow — cho dòng "[tool result]"
    ASSISTANT = "\033[1;35m"  # bold magenta — cho "[assistant] ..."
    FINISH = "\033[1;36m"   # bold cyan — cho "Agent finished."
    WARN = "\033[1;31m"     # bold red — cho cảnh báo
    RESET = "\033[0m"       # tắt mọi màu


def cprint(color: str, text: str) -> None:
    """In ra text có màu. Dùng `log.info` thay vì `print` để consistent.

    Tại sao tách hàm này? — Tránh lặp `{Color.X}...{Color.RESET}` ở 5 chỗ.
    """
    log.info(f"{color}{text}{Color.RESET}")


# ---------------------------------------------------------------------------
# Setup (LAZY — KHÔNG side-effect ở import)
#
# Trước đây file này đọc .env, dựng OpenAI client và gọi logging.basicConfig
# NGAY ở top level → chỉ cần `import src.agent` là đã require .env + cấu hình
# logging toàn cục cho cả tiến trình. Điều đó làm import có tác dụng phụ: eval
# harness / examples / test import module này sẽ crash nếu thiếu .env, và việc
# basicConfig chạy lúc import giẫm lên cấu hình logging của caller.
#
# Cách sửa: ĐẨY mọi thứ vào hàm lazy, chỉ chạy khi run_agent thực sự cần:
#   - get_client(): singleton — lần đầu mới load_dotenv + đọc env + dựng client.
#   - logging: cấu hình 1 lần bên trong run_agent qua _setup_logging() (có guard).
# => `import src.agent` giờ KHÔNG dựng client, KHÔNG cần env, KHÔNG đụng logging.
# ---------------------------------------------------------------------------

# `log` chỉ là một logger object — lấy logger KHÔNG có side-effect (không cấu
# hình gì), nên để ở module level vẫn an toàn. Việc CẤU HÌNH (basicConfig) mới
# là thứ phải hoãn lại tới run_agent.
log = logging.getLogger("agent")

# Singleton client — None cho tới lần get_client() đầu tiên. `global` cho phép
# gán lại biến module-level từ trong hàm.
_client: OpenAI | None = None

# Đã cấu hình logging chưa — guard để _setup_logging() chỉ basicConfig 1 lần,
# tránh giẫm lên cấu hình của caller ở những lần run_agent sau.
_logging_ready = False


def get_client() -> OpenAI:
    """Trả về OpenAI client (singleton), dựng lười ở lần gọi đầu tiên.

    Tại sao lười? — Để `import src.agent` không có tác dụng phụ: không đọc .env,
    không cần biến môi trường, không tạo kết nối. Chỉ khi run_agent (hoặc caller)
    THỰC SỰ cần gọi model thì mới load_dotenv + đọc env + dựng client.

    Đọc 3 biến cấu hình ở đây (không phải lúc import). Thiếu BASE_URL hay MODEL
    → crash ngay (fail fast). API_KEY có default vì vLLM không enforce auth.
    """
    global _client
    if _client is None:
        # Đọc file .env vào os.environ. Có file ./.env thì auto detect.
        load_dotenv()
        base_url = os.environ["VLLM_BASE_URL"]
        api_key = os.environ.get("VLLM_API_KEY", "not-needed")
        # Tạo OpenAI client trỏ vào vLLM. Đây chính là pattern "portability" — chỉ
        # cần đổi base_url trong .env là chạy được với GPT-4 cloud, Ollama, ...
        _client = OpenAI(base_url=base_url, api_key=api_key)
    return _client


def get_model() -> str:
    """Đọc MODEL lười từ env (gọi sau khi get_client đã load_dotenv, hoặc tự đọc).

    Tách riêng khỏi get_client để chỗ gọi API đọc tên model rõ ràng. load_dotenv
    là idempotent nên gọi ở đây cũng an toàn nếu vì lý do gì client chưa dựng.
    """
    load_dotenv()
    return os.environ["VLLM_MODEL_NAME"]


def _setup_logging() -> None:
    """Cấu hình logging 1 lần duy nhất (có guard), gọi từ run_agent.

    `format="%(message)s"` = chỉ in nội dung message, không in timestamp/level —
    gọn cho demo. Level INFO = thấy mọi log.info(). Guard `_logging_ready` để
    không basicConfig lại ở các lần run_agent sau (tránh giẫm cấu hình caller).
    """
    global _logging_ready
    if not _logging_ready:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
        _logging_ready = True


# ---------------------------------------------------------------------------
# THE AGENT LOOP — trái tim của hệ thống
# ---------------------------------------------------------------------------

def run_agent(goal: str, workspace: Path, max_iters: int = 15,
              time_budget_s: float | None = None,
              temperature: float | None = None) -> dict:
    """Run the ReAct loop until the model stops calling tools, or max_iters.

    ReAct = Reasoning + Acting interleaved. Each iteration:
      - reason:  model thinks, may produce visible content.
      - act:     model emits tool_calls (or nothing -> we're done).
      - observe: we execute each tool and append result as role=tool.
    Termination: model returns NO tool_calls (it has decided it's done).

    workspace: thư mục sandbox agent được phép đọc/ghi — nay là THAM SỐ tường
    minh (positional thứ 2, BẮT BUỘC), không còn là global trong tools.py. Mỗi
    lời gọi execute_tool() bên dưới truyền thẳng workspace này xuống tool.

    Returns {"finish_reason": str, "iters_used": int} so the eval harness can
    record the outcome. finish_reason ∈ {finished, max_iters, api_error, timeout, no_action}.
    `iters_used` = số turn ĐÃ thực hiện (1-based `i` tại điểm thoát) — nhất quán ở
    MỌI nhánh return (finished / max_iters / api_error / timeout / no_action).
    Callers that ignore the return value (the REPL, the CLI) are unaffected.

    time_budget_s: optional wall-clock cap, checked BETWEEN turns (None = no cap).
    """
    # Cấu hình logging 1 lần (lười — không chạy lúc import). Phải gọi TRƯỚC mọi
    # cprint/log.info bên dưới để output hiện ra.
    _setup_logging()
    # Dựng client lười + đọc tên model lười (không có gì xảy ra lúc import module).
    client = get_client()
    model = get_model()
    # Khởi tạo "cuốn sổ ký ức" (messages list) — y hệt 01_chat.py, nhưng nay
    # chứa cả system prompt VÀ goal của user (2 message ban đầu).
    # Dùng OpenAI TypedDict để Pylance pass-through; dict literal vẫn assign được
    # vì TypedDict là structural typing (chỉ check keys + value types).
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": goal},
    ]

    # Vòng lặp giới hạn `max_iters` turn — safety net để agent không loop vô tận.
    # Mỗi turn = 1 round-trip với model + thực thi tool nếu có.
    start = time.monotonic()
    # Guardrail "nói mà không làm": ~30% lần model trả prose (mô tả/viết code dạng
    # text) ngay turn đầu mà KHÔNG gọi tool nào → loop tưởng "xong" → task fail oan.
    #   made_tool_call: đã gọi tool lần nào chưa (chốt phân biệt "xong thật" vs "bail").
    #   nudges_used:    đã nhắc bao nhiêu lần; chặn ở MAX_NUDGES để không loop vô tận.
    made_tool_call = False
    nudges_used = 0
    MAX_NUDGES = 2
    NUDGE = ("You replied with text but called no tool, so nothing has actually changed "
             "on disk and the task is NOT done. If the task needs a file created or edited, "
             "call write_file / apply_patch / multi_edit now — do not just describe the code. "
             "Only stop without a tool call once the work is truly complete.")
    for i in range(1, max_iters + 1):
        # Hết ngân sách thời gian (nếu eval truyền vào) → dừng gọn. Chỉ check GIỮA
        # các turn: không ngắt được 1 tool đang chạy dở, nhưng mỗi tool đã có timeout
        # riêng (run_bash 600s, run_python/pytest 60s) nên thời gian bị chặn trên.
        if time_budget_s is not None and time.monotonic() - start > time_budget_s:
            cprint(Color.WARN, f"\nAgent hit time budget {time_budget_s:.0f}s on turn {i}.")
            # `iters_used: i` (KHÔNG phải i-1) cho NHẤT QUÁN với mọi nhánh return
            # khác — tất cả đều báo `i` (1-based số turn đã bước vào). Bug cũ trả
            # i-1 khiến eval đếm lệch 1 ở case timeout.
            return {"finish_reason": "timeout", "iters_used": i}
        # Header phân tách từng turn — dễ nhìn khi demo.
        cprint(Color.HEADER, f"\n=== Turn {i} (history: {len(messages)} messages) ===")

        # -----------------------------------------------------------------------
        # BƯỚC 1: GỌI API (REASON)
        # Khác 01_chat.py ở 2 tham số mới:
        #   - tools=TOOL_SCHEMAS: gửi danh sách tool cho model biết
        #   - tool_choice="auto": cho model TỰ QUYẾT có gọi tool không
        # ("required" sẽ ép gọi tool mỗi turn — không phù hợp vì cần model có
        # khả năng "kết thúc" bằng cách trả về content trần)
        # -----------------------------------------------------------------------
        # type:ignore: TOOL_SCHEMAS là list[dict] (xem tools.py), không exact
        # match OpenAI TypedDict ChatCompletionToolUnionParam. Runtime hợp lệ vì
        # dict shape khớp schema OpenAI mong đợi.
        #
        # Bọc try/except quanh CHỈ lời gọi API: nếu vLLM rớt mạng, trả 5xx, hay
        # context vượt quá window (400), exception sẽ bubble ra ngoài và giết
        # cả run_agent — eval/run.py sẽ tính nguyên task là crash. Bắt ở đây để
        # log lỗi (Rule C: verbose) rồi return GỌN GÀNG.
        # An toàn về tính đúng đắn: tại điểm này messages list đang Ở TRẠNG THÁI
        # HỢP LỆ (mọi assistant-tool_calls trước đó đã có đủ tool message ghép
        # cặp). Vì ta return TRƯỚC khi append assistant message mới, list không
        # bao giờ bị bỏ lại với 1 assistant.tool_calls "mồ côi" không có kết quả.
        # temperature=None → dùng default của model (REPL). Eval truyền 0.0 để
        # decode tham lam (greedy): tool-call ổn định + kết quả TÁI LẬP được (pass@1
        # chuẩn). Ở temp mặc định (~0.6), thỉnh thoảng turn-1 model trả prose thay
        # vì gọi write_file → task fail oan; greedy gần như loại bỏ hành vi đó.
        create_kwargs = dict(
            model=model,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            max_tokens=2048,
        )
        if temperature is not None:
            create_kwargs["temperature"] = temperature
        try:
            resp = client.chat.completions.create(**create_kwargs)  # type: ignore[arg-type]
        except OpenAIError as e:
            cprint(Color.WARN, f"\nAPI error on turn {i}: {e}. Stopping.")
            return {"finish_reason": "api_error", "iters_used": i}

        # -----------------------------------------------------------------------
        # BƯỚC 2: BÓC LẤY MESSAGE (giống 01_chat.py)
        # resp.choices là list — nếu n=1 (default), index 0 là câu trả lời duy nhất.
        # msg là Pydantic object có .content, .role, .tool_calls, .reasoning, ...
        # -----------------------------------------------------------------------
        msg = resp.choices[0].message

        # -----------------------------------------------------------------------
        # BƯỚC 3: APPEND ASSISTANT MESSAGE VÀO SỔ KÝ ỨC
        # KHÁC 01_chat.py: ở đây mình KHÔNG append `{"role":"assistant","content":...}`,
        # vì làm vậy sẽ MẤT field `tool_calls`. Đây là BẤT BIẾN sống còn của
        # ReAct loop: mỗi assistant message có tool_calls PHẢI được theo sau bởi
        # đúng 1 tool message cho MỖI tool_call_id. Nếu append thủ công chỉ
        # content, các tool-result message ở BƯỚC 6 sẽ tham chiếu tool_call_id
        # không tồn tại trong assistant trước → API trả 400 và cả run hỏng.
        # `model_dump(exclude_none=True)` = convert Pydantic object → dict, bỏ field
        # null (vd: `content: None` khi model chỉ gọi tool, `audio: None`). Đã
        # verify: exclude_none GIỮ NGUYÊN mảng tool_calls + id + function, nên
        # bất biến ghép cặp vẫn toàn vẹn — chỉ rụng các field thừa làm API khó chịu.
        # -----------------------------------------------------------------------
        # model_dump trả về dict[str, Any], không exact-match TypedDict
        # ChatCompletionMessageParam → type:ignore. Runtime hoàn toàn ổn vì
        # dict shape khớp schema OpenAI; chỉ type checker khó tính.
        messages.append(msg.model_dump(exclude_none=True))  # type: ignore[arg-type]

        # -----------------------------------------------------------------------
        # BƯỚC 4: NẾU MODEL CÓ CONTENT (= nói chuyện), IN RA
        # Content có thể None khi model chỉ gọi tool không nói gì.
        # Khi có content, đây là lúc model "narrate" (giải thích nó đang làm gì).
        # -----------------------------------------------------------------------
        if msg.content:
            cprint(Color.ASSISTANT, f"[assistant] {msg.content}")

        # -----------------------------------------------------------------------
        # BƯỚC 5: NẾU KHÔNG CÓ TOOL_CALLS, AGENT KẾT THÚC
        # Quy ước ReAct: model dừng gọi tool = model nghĩ task xong → mình tin nó.
        # `not msg.tool_calls` true khi tool_calls là None HOẶC list rỗng.
        # -----------------------------------------------------------------------
        if not msg.tool_calls:
            # Đã hành động ít nhất 1 lần → tin agent đã xong thật (giữ nguyên hành vi
            # ReAct cũ, bảo toàn quyền kết thúc hợp lệ của agent đã làm việc xong).
            if made_tool_call:
                cprint(Color.FINISH, "\nAgent finished.")
                return {"finish_reason": "finished", "iters_used": i}
            # Chưa đụng tool lần nào mà đã "xong" → gần như chắc là trả prose suông.
            # Còn quota nhắc VÀ còn turn để model phản hồi nudge thì nhắc rồi loop lại.
            # An toàn pairing: assistant vừa append KHÔNG có tool_calls nên messages
            # đang hợp lệ; thêm 1 user nudge sau nó OK.
            #
            # `and i < max_iters`: CHỈ nhắc khi VẪN CÒN turn phía sau để model đáp lại
            # nudge. Nếu đây là turn cuối (i == max_iters), nudge cũng vô nghĩa (loop
            # sẽ dừng ngay, model không kịp đọc) → rơi thẳng xuống no_action bên dưới.
            # Đây là fix cho ca biên max_iters <= MAX_NUDGES: trước đây cứ còn quota là
            # nudge + continue, nên turn cuối append nudge rồi vòng lặp kết thúc và HÀM
            # RƠI XUỐNG nhánh max_iters ở cuối → báo nhầm "max_iters" thay vì "no_action".
            if nudges_used < MAX_NUDGES and i < max_iters:
                nudges_used += 1
                cprint(Color.WARN,
                       f"\nModel answered without calling a tool; nudging ({nudges_used}/{MAX_NUDGES}).")
                messages.append({"role": "user", "content": NUDGE})
                continue
            # Hết quota (hoặc đây là turn cuối) mà vẫn không act → dừng, đánh dấu
            # no_action để harness phân biệt với "finished" thật (fail kiểu "nói mà
            # không làm"). Return TẠI ĐÂY (iters_used=i) thay vì để rơi xuống nhánh
            # max_iters ở cuối hàm — phân loại finish_reason chính xác hơn.
            cprint(Color.WARN, "\nAgent stopped without ever calling a tool (no_action).")
            return {"finish_reason": "no_action", "iters_used": i}

        # -----------------------------------------------------------------------
        # BƯỚC 5.5: NẾU ĐÂY LÀ TURN CUỐI (i == max_iters) MÀ MODEL VẪN GỌI TOOL,
        # KHÔNG chạy tool nữa. Lý do: kết quả tool ở turn cuối sẽ KHÔNG bao giờ
        # được gửi lại cho model (vòng lặp kết thúc ngay sau), nên chạy chúng chỉ
        # phí công — tệ hơn, có thể là write_file/apply_patch làm thay đổi đĩa mà
        # model không kịp verify. Dừng tại đây và rơi xuống cảnh báo max_iters.
        # -----------------------------------------------------------------------
        if i == max_iters:
            break

        # -----------------------------------------------------------------------
        # BƯỚC 6: NẾU CÓ TOOL_CALLS, CHẠY TỪNG CÁI VÀ TRẢ KẾT QUẢ VỀ
        # Có thể có >1 tool_call trong 1 turn (model parallel calls).
        # -----------------------------------------------------------------------
        # Tới đây chắc chắn sẽ chạy tool (đã qua BƯỚC 5.5 break) → đánh dấu agent
        # đã THỰC SỰ hành động (tắt guardrail "nói mà không làm" cho các turn sau).
        made_tool_call = True
        for tc in msg.tool_calls:
            # type:ignore: msg.tool_calls có thể chứa ChatCompletionMessageCustomToolCall
            # (không có .function). Hiện model chỉ emit function calls (Hermes parser)
            # nên runtime ổn — Pylance khó tính.
            # Log tên tool + arguments TRƯỚC khi chạy → debug được tool nào hang.
            cprint(Color.TOOL, f"[tool] {tc.function.name}({tc.function.arguments})")  # type: ignore[union-attr]

            # execute_tool tự parse JSON args + dispatch theo name. Nó luôn trả
            # về string (kể cả khi có lỗi — string bắt đầu bằng "ERROR:").
            # `workspace` truyền tường minh xuống dispatcher (không còn global).
            result = execute_tool(tc.function.name, tc.function.arguments, workspace)  # type: ignore[union-attr]

            # Cắt bớt khi log để khỏi spam terminal. Model vẫn nhận FULL kết quả
            # qua append messages bên dưới.
            preview = result if len(result) < 500 else result[:500] + "...[truncated]"
            cprint(Color.RESULT, f"[tool result]\n{preview}")

            # Append tool result theo format chuẩn OpenAI:
            #   role: "tool"
            #   tool_call_id: phải khớp với tc.id để API biết kết quả này thuộc call nào
            #   content: chuỗi kết quả (model đọc chuỗi này ở turn sau)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })
        # Hết for — loop sang turn tiếp theo, model sẽ "thấy" tool results vừa append.

    # Rơi xuống đây = đã dùng hết max_iters turn mà model vẫn còn muốn gọi tool
    # (chưa chịu trả content trần để báo "xong"). Đây là safety net chống loop
    # vô tận — không hẳn là bug, nhưng dấu hiệu task quá khó hoặc model bị kẹt.
    cprint(Color.WARN, f"\nAgent hit max_iters={max_iters} without finishing.")
    return {"finish_reason": "max_iters", "iters_used": max_iters}


# ---------------------------------------------------------------------------
# ENTRY POINT — `python -m src.agent "goal"`
# (Để gọn, examples/05_agent_loop.py là CLI wrapper "đẹp hơn" cho demo)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    # argparse thay cho việc bóc sys.argv thủ công — cho phép --workspace (chốt
    # sandbox file ops) + --max-iters tùy chọn, và tự sinh usage/-h.
    parser = argparse.ArgumentParser(
        description="ReAct coding agent. Example: "
                    "python -m src.agent 'Fix the failing tests in demo_repo/'")
    # positional `goal` với nargs="+" → gom MỌI từ user gõ thành 1 list, rồi
    # join lại thành câu hoàn chỉnh (giữ hành vi cũ: gõ không cần đóng ngoặc kép).
    parser.add_argument("goal", nargs="+", help="natural-language task description")
    # --workspace: thư mục sandbox agent được phép đọc/ghi. Default demo_repo/ —
    # agent không "đi lạc" sang sửa src/agent.py của chính mình (self-modification
    # là Phase 4, chưa phải bây giờ).
    parser.add_argument("--workspace", default="demo_repo",
                        help="sandbox directory the agent may read/write (default: demo_repo)")
    # --max-iters tùy chọn: bỏ trống thì dùng default của run_agent (15).
    parser.add_argument("--max-iters", type=int, default=None,
                        help="max ReAct turns (default: run_agent's 15)")
    args = parser.parse_args()

    # Join các từ goal thành 1 câu. Path(...).resolve() biến --workspace thành
    # đường dẫn tuyệt đối trước khi đưa vào run_agent (tool ops chốt vào đây).
    task = " ".join(args.goal)
    workspace = Path(args.workspace).resolve()

    cprint(Color.HEADER, f"GOAL: {task}\n")
    # Chỉ truyền max_iters khi user có chỉ định → nếu không, dùng default của hàm.
    if args.max_iters is not None:
        run_agent(task, workspace=workspace, max_iters=args.max_iters)
    else:
        run_agent(task, workspace=workspace)
