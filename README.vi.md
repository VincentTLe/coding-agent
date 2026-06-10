> 🇬🇧 English version: [README.md](README.md)

# Coding Agent from Scratch

Built-from-scratch AI coding agent dùng Qwen3-14B local qua vLLM. Không framework (no LangChain / LangGraph / CrewAI).

- **Course**: Math/Stat 361 Research (Knox College)
- **Advisor**: Prof. Andrew Leahy
- **Demo**: checkpoint 2026-05-20 → final 2026-05-29

---

## 1. HOW IT WORKS — toàn cảnh

```
┌─────────────────────────────────────────────────────────────────┐
│  YOU (terminal)  ── gõ task → đọc output                         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  PYTHON PROCESS — cli/chat.py  (REPL chat)                       │
│  ──────────────────────────────────────                          │
│    while True:                                                    │
│      user = input("you> ")                                        │
│      if slash command: handle                        # ↓ §4      │
│        (/help /clear /think /nothink /compact /tokens /exit)     │
│      messages.append({"role": "user", "content": user})           │
│      if estimate_tokens(messages) > 24000:           # compaction │
│        messages = compact_messages(messages)         # ← auto     │
│                                                                   │
│      for turn in range(15):                          # inner loop │
│        stream = client.chat.completions.create(                   │
│          model, messages, tools=TOOL_SCHEMAS,        # ← tools.py │
│          stream=True,                                             │
│          extra_body={"chat_template_kwargs":                      │
│                      {"enable_thinking": thinking_enabled}})      │
│                                                                   │
│        for chunk in stream:                          # streaming  │
│          delta.reasoning_content → in màu trắng      # thinking   │
│          delta.content           → in màu tím        # answer     │
│          delta.tool_calls        → tích luỹ          # actions    │
│                                                                   │
│        validate JSON args (anti triple-quote crash)               │
│        messages.append(assistant msg with tool_calls)             │
│                                                                   │
│        if no tool_calls: break       ← agent xong                 │
│                                                                   │
│        for tc in tool_calls:                                      │
│          result = execute_tool(...)  ← tools.py dispatcher        │
│          messages.append({"role": "tool", "content": result})     │
│        # loop tiếp → model thấy tool results                      │
└──────────────────────┬──────────────────────────────────────────┘
                       │ HTTP POST /v1/chat/completions
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  VLLM SERVER — chạy trong tmux session "vllm"                    │
│  ────────────────────────────────                                │
│    Launched by: bash scripts/start_vllm.sh                       │
│    Listening:   http://localhost:8765                            │
│    Model:       Qwen3-14B trên GPU1 (~28GB BF16, A6000 48GB)     │
│    Context:     --max-model-len 32768 (32K)                      │
│    GPU mem:     --gpu-memory-utilization 0.75                    │
│    Parsers:     --reasoning-parser qwen3  (tách <think> block)   │
│                 --tool-call-parser hermes (tách <tool_call> XML) │
│                 --enable-auto-tool-choice                        │
└─────────────────────────────────────────────────────────────────┘
```

**3 câu tóm tắt:**
1. `cli/chat.py` chạy REPL, giữ `messages` list, mỗi user input gửi qua **OpenAI SDK** đến **vLLM** HTTP.
2. **vLLM** chạy **Qwen3-14B** trên GPU, stream về từng token (thinking + content + tool_calls).
3. Khi model gọi tool, `cli/chat.py` chạy tool qua `src/tools.py` (truyền `workspace` xuống), append result vào `messages`, loop lại.

### Tools — 11 tools, 5 nhóm

Tất cả định nghĩa trong `src/tools.py` (hàm + JSON schema + dispatcher). Model chọn tool đúng theo nhóm.

| Nhóm | Tool | Làm gì |
|---|---|---|
| **FILE I/O** | `read_file` | đọc toàn bộ nội dung file |
| | `write_file` | ghi đè / tạo file mới (full content) |
| | `apply_patch` | sửa surgical, 1 match duy nhất (`old_text` phải unique) |
| | `multi_edit` | nhiều edit cho 1 file, atomic (all-or-nothing) |
| **DISCOVERY** | `list_dir` | liệt kê thư mục (sạch hơn `ls`) |
| | `glob_files` | match file theo pattern (vd `**/*.py`) |
| | `grep_files` | regex search across files |
| **EXECUTION** | `run_bash` | chạy shell command (pytest, git, pip…), timeout 600s |
| | `run_python` | chạy snippet Python nhanh, timeout 60s |
| **DELEGATION** | `spawn_subagent` | chạy 1 agent con trong subprocess (timeout 300s, max_iters 8) |
| **COMPLETION** | `finish` | tín hiệu kết thúc tường minh — run_agent bắt theo tên để dừng vòng lặp |

> **Sandbox (trust model trung thực)**: 7 tool nhận đường dẫn bị giới hạn trong workspace dir (default CLI là `demo_repo/`) — `_safe_path(path, workspace)` trong `tools.py` chặn path-traversal (`../`). Workspace là **tham số tường minh** truyền qua `run_agent(goal, workspace, ...)` và `execute_tool(name, args, workspace)` — KHÔNG còn global `WORKSPACE` / `set_workspace`. **Nhưng** 3 tool thực thi (`run_bash`, `run_python`, `spawn_subagent`) chạy với toàn quyền user, chỉ giới hạn cwd + timeout — sandbox chống *tai nạn đường dẫn*, không chống lệnh ác ý. Cô lập thật cần container/bwrap (chưa làm).

### Context compaction

Conversation dài làm tràn 32K context. `cli/chat.py` tự xử lý:

- `estimate_tokens(messages)` ước lượng token mỗi turn.
- Khi vượt `COMPACT_THRESHOLD_TOKENS = 24000` (~75% context), `compact_messages()` tóm tắt history cũ thành 1 summary, **giữ nguyên `KEEP_RECENT_MESSAGES = 10` message gần nhất verbatim**.
- `/compact` để nén thủ công ngay; `/tokens` (hoặc `/tok`) để xem ước lượng token hiện tại.

---

## 2. FILE LAYOUT — ai import ai

```
coding-agent/
│
├── cli/                       🟢 CÁCH CHẠY agent thật
│   ├── chat.py                🟢 ENTRY POINT (REPL chat, streaming + compaction)
│   │   Imports: src.tools, src.prompts, openai, dotenv
│   │   Imported by: nothing (entry point)
│   └── solve.py               🟢 ENTRY POINT (one-shot task runner)
│       Imports: src.agent
│       Imported by: nothing (entry point)
│
├── src/                       THƯ VIỆN agent (import được, không side-effect)
│   ├── __init__.py            (marker — đánh dấu src/ là Python package)
│   ├── agent.py               ReAct loop — run_agent(goal, workspace, ...) (KHÔNG streaming)
│   │   │                      Cũng là entry one-shot: python -m src.agent "task" --workspace dir
│   │   Imports: src.tools, src.prompts, openai, dotenv (client lazy qua get_client())
│   │   Imported by: cli/solve.py, eval/run.py
│   ├── tools.py               11 tools + JSON schemas + dispatcher + sandbox
│   │   Imports: stdlib only
│   │   Imported by: src.agent, cli/chat.py
│   └── prompts.py             SYSTEM_PROMPT (1 string)
│       Imports: nothing
│       Imported by: src.agent, cli/chat.py
│
├── examples/                  THANG DẠY HỌC (đọc để hiểu, KHÔNG phải runtime)
│   └── 01_chat.py → 04_sandbox_safety.py   ladder: chat → 1 tool → ReAct loop → sandbox
│
├── tests/                     pytest unit tests (sandbox, tools, dispatcher)
│
├── eval/                      BENCHMARK HARNESS (627 tasks)
│   ├── run.py                 🟢 ENTRY POINT (chạy song song, chấm bằng pytest)
│   │   Imports: src.agent, src.tools
│   ├── validate_tasks.py      quality gate (reference pass, stub fail → else quarantine)
│   ├── convert_benchmark.py   regen task HumanEval+/MBPP (deps: huggingface_hub + requests)
│   └── tasks/                 bench/ (HE+ & MBPP) · curated/ (37 hard) · 3 demo cũ
│
├── scripts/start_vllm.sh      🟢 ENTRY POINT (launch vLLM server)
│   Standalone bash script — không relate Python imports.
│
├── demo_repo/                 SANDBOX cho agent (workspace mặc định của CLI)
│   ├── algorithms.py          is_prime + factorial + fibonacci
│   ├── test_algorithms.py     pytest cases cho ở trên (8 tests, import từ algorithms)
│   ├── calculator.py          add + multiply
│   ├── test_calculator.py     pytest cases cho ở trên (3 tests)
│   └── fibonacci.py           script fibonacci đệ quy độc lập (có __main__) — artifact agent
│                              tự sinh ra (bằng chứng write_file); KHÔNG phải file mà test import
│
├── .env                       Biến môi trường runtime (gitignored)
├── .env.example               Template
├── pyproject.toml             Deps + ruff/pytest config
├── uv.lock                    Lockfile (uv tự tạo)
├── AGENTS.md                  Rule A/B/C (verify, cache docs, verbose)
└── README.md                  File này
```

**Đường dẫn chính khi gõ `python cli/chat.py`:**

```
cli/chat.py
   │
   ├──── from dotenv import load_dotenv         # đọc .env
   ├──── from openai import OpenAI              # HTTP client
   │
   ├──── from src.tools import (...)            ← LOAD src/tools.py
   │        TOOL_SCHEMAS, execute_tool          # workspace truyền vào execute_tool()
   │
   └──── from src.prompts import SYSTEM_PROMPT  ← LOAD src/prompts.py
```

---

## 3. RUN — 3 cách bật agent lên

### 3A. Local trên lab server (lambdavector2) — cách nhanh nhất

```bash
# 1. Kiểm tra vLLM còn chạy không (đã có tmux session "vllm")
curl -sf http://localhost:8765/v1/models >/dev/null && echo OK || echo "vLLM DOWN"

# Nếu DOWN:
tmux attach -t vllm           # vào pane vLLM coi log
# hoặc khởi động lại:
tmux new -d -s vllm 'bash ~/code/coding-agent/scripts/start_vllm.sh'
# đợi ~1-2 phút thấy "Application startup complete"

# 2. Mở REPL
cd ~/code/coding-agent && source .venv/bin/activate
python cli/chat.py
```

### 3B. SSH từ máy khác (vd máy của thầy) vào lab server

```bash
# Trên máy của thầy / máy bất kì có SSH:
ssh tle@<địa-chỉ-lambdavector2>     # cần access lab network (VPN nếu off-campus)

# Trong session SSH (làm tiếp như 3A):
cd ~/code/coding-agent && source .venv/bin/activate
python cli/chat.py
```

> **Lưu ý:** nếu mạng lab không cho phép SSH từ ngoài, dùng laptop của anh (đã có access) + screen share / chiếu màn hình cho thầy xem.

### 3C. Chạy hoàn toàn cục bộ trên máy có GPU (khả thi nhưng phức tạp)

Cần:
- Python 3.12
- GPU NVIDIA ≥ 30GB VRAM (A6000 / A100 / 4090 24GB không đủ cho BF16, cần FP8 hoặc INT4 quant)
- Tải `Qwen/Qwen3-14B` (~28GB) từ Hugging Face
- Install vLLM + deps

```bash
git clone <repo-url> coding-agent && cd coding-agent
uv venv && source .venv/bin/activate && uv sync
pip install vllm                              # ~5-10 phút download
hf download Qwen/Qwen3-14B --local-dir ~/models/Qwen3-14B
cp .env.example .env

# Tab 1 — vLLM server
bash scripts/start_vllm.sh

# Tab 2 — REPL
python cli/chat.py
```

---

## 4. DEMO — 10 phút cho thầy

### Pre-demo (~30 giây)

```bash
# 1. Verify vLLM
curl -sf http://localhost:8765/v1/models >/dev/null && echo "vLLM OK"

# 2. cd + venv
cd ~/code/coding-agent && source .venv/bin/activate

# 3. Reset demo_repo về buggy state (sạch hint comments)
cat > demo_repo/algorithms.py <<'PYEOF'
"""Common math algorithms."""


def is_prime(n: int) -> bool:
    """Return True if n is a prime number (n >= 2)."""
    if n < 2:
        return False
    for i in range(1, n):
        if n % i == 0:
            return False
    return True


def factorial(n: int) -> int:
    """Return n! (n factorial). factorial(0) = 1, factorial(5) = 120."""
    if n < 0:
        raise ValueError("n must be non-negative")
    result = 1
    for i in range(1, n):
        result *= i
    return result


def fibonacci(n: int) -> int:
    """Return the nth Fibonacci number. fib(0)=0, fib(1)=1."""
    if n < 0:
        raise ValueError("n must be non-negative")
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a
PYEOF

cat > demo_repo/calculator.py <<'PYEOF'
"""A tiny calculator module."""


def add(a: int, b: int) -> int:
    return a - b


def multiply(a: int, b: int) -> int:
    return a * b
PYEOF

# 4. Verify pre-state: một số test FAIL (tổng 11 tests)
python -m pytest demo_repo --tb=no -q
```

> Mục tiêu demo: agent chạy pytest, thấy fail, **sửa SOURCE (không sửa test)**, re-run đến khi **11/11 pass**.

### Demo flow (REPL)

```bash
python cli/chat.py
```

```
═══════════════════════════════════════════════════════════
PHẦN 1 — FAST MODE (mặc định, không thinking)
═══════════════════════════════════════════════════════════

you> Hello, what can you do?
   → trả lời ngay, KHÔNG thinking block

you> Add a function power(base, exp) to calculator.py with tests in test_calculator.py
   → đọc file → viết func + test → chạy pytest → done

═══════════════════════════════════════════════════════════
PHẦN 2 — DEEP MODE (bật thinking)
═══════════════════════════════════════════════════════════

you> /think
   → "Thinking mode: ON (deep)"

you> Fix all failing tests in this repo
   → [thinking] → ls → pytest → [thinking] → read → [thinking] → write → pytest → done

═══════════════════════════════════════════════════════════
PHẦN 3 — TRADE-OFF
═══════════════════════════════════════════════════════════

you> /nothink
you> What does multiply do?
   → trả lời ngay, không thinking

you> /tokens
   → in token estimate hiện tại + threshold (auto-compact ở 24000)

you> /exit
```

> Full slash commands: `/help  /clear  /think  /nothink  /compact  /tokens  /exit`

### Cách DỪNG agent

| Khi nào | Phím |
|---|---|
| Agent thinking/streaming lâu | **Ctrl+C** → `[interrupted]` → quay về `you>` |
| Ở cursor `you>` | **Ctrl+C** hoặc `/exit` → thoát REPL |

---

## 5. TROUBLESHOOTING

| Vấn đề | Cách fix |
|---|---|
| `vLLM DOWN` (curl fail) | `tmux attach -t vllm` xem log, hoặc relaunch `bash scripts/start_vllm.sh` |
| REPL báo `API error: Connection refused` | vLLM chưa start xong → đợi ~1-2 phút |
| Agent loop vô tận | Ctrl+C → /clear → gõ lại task ngắn hơn |
| Pytest report `collected 0 items / 1 error` | File anh sửa có SYNTAX error — agent đã được dạy nhận và fix |
| Demo_repo không còn bug | Chạy lại đoạn `cat > demo_repo/*.py` ở Pre-demo trên |
| Tool call crash vì JSON | Đã có sanitization — agent retry tự động (không crash REPL) |

---

## 6. CODE GUIDE — đọc từng file theo thứ tự

> 📊 **Muốn nắm toàn bộ hệ thống bằng hình ảnh trước khi vào code?** Mở [`SYSTEM_DEEP_DIVE.html`](docs/explainers/SYSTEM_DEEP_DIVE.html) — trang giải thích trực quan từ nguyên lý gốc (LLM dự đoán token → ReAct + tool calling → vLLM → hệ thống của mình → eval → cái gì là của riêng mình). Tiếng Việt, có sidebar mục lục + diagram tự dựng. Đọc cái này trước rồi vào code sẽ dễ hơn nhiều.

Anh muốn hiểu sâu thì đọc theo order này:

1. **`examples/01_chat.py` → `04_sandbox_safety.py`** — thang dạy học: chat (không tool) → 1 tool → ReAct loop → sandbox. Đọc theo số thứ tự.
2. **`src/prompts.py`** — 1 string SYSTEM_PROMPT.
3. **`src/tools.py`** — 11 tools (5 nhóm) + JSON schemas + dispatcher + sandbox (`_safe_path(path, workspace)`). Đọc comments Việt theo từng phần.
4. **`src/agent.py`** — ReAct loop bản KHÔNG streaming, `run_agent(goal, workspace, ...)`. Hiểu xong examples + tools + agent là biết hết core.
5. **`cli/chat.py`** — REPL streaming, thêm: stream chunks, thinking display, JSON sanitization, thinking toggle, context compaction (`estimate_tokens` / `compact_messages`).
6. **`eval/run.py`** — benchmark harness: chấm 627 task song song, hidden-test scoring, guardrail `no_action`.
7. **`scripts/start_vllm.sh`** — biết vLLM bật bằng flag gì.

Mỗi file đã có **inline Vietnamese comments** giải thích từng section.

---

## 7. ROADMAP

- **Phase 1** (now → May 29) — basic agent ✅ + 11 tools ✅ + context compaction ✅ + checkpoint 2026-05-20 + final 2026-05-29
- **Phase 2** (Jun) — Reflexion loop + persistent `MEMORY.md`
- **Phase 3** (Jul-Aug) — LoRA fine-tuning Qwen3-14B trên agent traces (Unsloth + DPO)
- **Phase 4** (Aug+) — agent generate new tools cho chính mình, edit own prompts (self-improvement)

Plan đầy đủ: `~/.claude/plans/push-i-k-c-gleaming-crystal.md`. Pre-research SOTA: `docs/research/_SUMMARY.md` (30 reports).

---

## 8. AGENTS.md rules (cho session AI mới)

- **Rule A**: web-search official sources trước khi đưa ra technical claim.
- **Rule B**: cache official docs vào `docs/reference/<tech>/`, append `docs/reference/INDEX.md`.
- **Rule C**: verbose agent runtime (logs đầy đủ thay vì print thưa).
