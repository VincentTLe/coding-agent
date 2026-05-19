"""
01_chat.py — Stateless multi-turn chat against any OpenAI-compatible LLM.

KEY CONCEPT (re-read this any time you get lost)
  The server is STATELESS. It does not remember any earlier turn.
  This client keeps a Python list called `messages` and resends the
  WHOLE list every API call. That list IS the memory.

YOUR JOB
  Replace every `# TODO ...` line with real code. The comments above
  each section explain the syntax + concepts you'll need. Try to
  reason from the hints first; only ask Claude/web when stuck.

WHEN DONE
  $ python examples/01_chat.py
  Tell the bot your name. Then ask "what is my name?".
  If it answers correctly, your messages-list-as-memory is working.

HOW TO PROGRESS
  Fill sections 1 -> 8 in order. After each section, save the file
  and run it. Sections 1-5 are setup (won't run anything visible);
  the file only "does something" once section 7 (main) is filled.

SWAPPING MODELS (no code changes needed)
  This file reads server URL + model name from `.env`. To switch backends,
  only edit `.env` and restart the server — Python code stays the same.

    # Qwen3-14B served by local vLLM (current setup, has reasoning trace):
    VLLM_BASE_URL=http://localhost:8765/v1
    VLLM_MODEL_NAME=Qwen/Qwen3-14B

    # Qwen3.6-27B (heavier, also has reasoning):
    VLLM_MODEL_NAME=Qwen/Qwen3.6-27B          # plus restart server with the bigger model

    # OpenAI cloud (no reasoning trace, just `content`):
    VLLM_BASE_URL=https://api.openai.com/v1
    VLLM_MODEL_NAME=gpt-4o-mini
    VLLM_API_KEY=sk-...                       # real key required

  The `reasoning` field appears only if the server runs with a reasoning
  parser (e.g. vLLM's `--reasoning-parser qwen3`) AND the model emits a
  thinking block. The code below handles both "present" and "absent" cases.
"""

# ===================================================================
# SECTION 1 — IMPORTS
# ===================================================================
# Python syntax for pulling code out of other modules:
#     import X            -> import the whole module. Use as `X.thing`.
#     from X import Y     -> import just Y. Use as `Y` (no prefix).
#
# You need 3 things:
#   a) the stdlib module that gives access to os.environ
#   b) `load_dotenv` from the `dotenv` library (loads .env into os.environ)
#   c) the `OpenAI` class from the `openai` library

# TODO 1.a:
import os
# TODO 1.b:
from dotenv import load_dotenv
# TODO 1.c:
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam


# ===================================================================
# SECTION 2 — LOAD THE .ENV FILE
# ===================================================================
# load_dotenv() reads ./.env and copies each KEY=VALUE line into
# os.environ. After this call, os.environ["VLLM_BASE_URL"] works.
# Call it with NO arguments — it auto-detects ./.env in the cwd.

# TODO 2.a:
load_dotenv() 


# ===================================================================
# SECTION 3 — READ CONFIG FROM ENVIRONMENT (module-level constants)
# ===================================================================
# After load_dotenv(), these vars exist (defined in .env):
#     VLLM_BASE_URL     URL of the vLLM server
#     VLLM_MODEL_NAME   model identifier the server knows
#     VLLM_API_KEY      auth token (vLLM ignores, but SDK requires non-empty)
#
# Two ways to read:
#     os.environ["KEY"]                   REQUIRED — raises KeyError if missing.
#     os.environ.get("KEY", "fallback")   OPTIONAL — returns fallback if missing.
#
# Style: module-level constants are ALL_CAPS_WITH_UNDERSCORES.

# TODO 3.a: BASE_URL = ...           (treat as required)
BASE_URL = os.environ["VLLM_BASE_URL"]
# TODO 3.b: MODEL    = ...           (treat as required)
MODEL = os.environ["VLLM_MODEL_NAME"]
# TODO 3.c: API_KEY  = ...           (optional, default to "not-needed")
API_KEY = os.environ.get("VLLM_API_KEY", "not-needed")

# ===================================================================
# SECTION 4 — CREATE THE OPENAI CLIENT
# ===================================================================
# In Python, you create an instance of a class by calling it like a function:
#     obj = ClassName(arg1=value1, arg2=value2)
#
# The OpenAI class accepts two keyword arguments you care about:
#     base_url=  the server's URL
#     api_key=   the auth token

# TODO 4.a: client = ...
client = OpenAI(
    base_url=BASE_URL,
    api_key=API_KEY
)

# ===================================================================
# SECTION 5 — INITIALIZE THE MESSAGES LIST (the "memory")
# ===================================================================
# Every message is a dict with two keys:
#     {"role": <"system" | "user" | "assistant">, "content": <str>}
#
# Start with ONE message of role "system" that sets the assi    stant's behavior.
# Example content: "You are a helpful assistant. Keep answers concise."
#
# Optional type hint (good documentation):
#     messages: list[dict] = [...]

# TODO 5.a:
messages: list[ChatCompletionMessageParam] = [
    {
        "role": "system",
        "content": "You are a helpful assistant. Keep the answer concise."
    }
]       

# ===================================================================
# SECTION 6 — chat_once: ONE ROUND-TRIP TO THE SERVER
# ===================================================================
# Goal: take a user line, call the model, print its reply, and
# update `messages` so the NEXT turn remembers this exchange.
#
# Steps (you decide the exact code):
#   (1) Append a new dict to `messages` for the user's turn.
#         {"role": "user", "content": user_text}
#   (2) Print a debug line so you can SEE the list grow:
#         "  -> sending N messages to server"   where N = len(messages)
#   (3) Call the API. The method chain is:
#         client.chat.completions.create(
#             model=MODEL,
#             messages=messages,
#             max_tokens=1024,
#         )
#       Store the return value in `resp`.
#   (4) Drill in:
#         msg = resp.choices[0].message
#       (`resp.choices` is a list; index 0 is the answer. Each choice has
#        `.message` which is a Pydantic object with .role, .content, etc.)
#   (5) Get the reasoning trace (model's hidden thinking, when available):
#         reasoning = getattr(msg, "reasoning", None)
#       WHY getattr instead of msg.reasoning?
#         Direct dot-access raises AttributeError if the attribute is
#         missing. getattr(obj, "name", default) returns default if
#         missing.
#       WHEN does `reasoning` exist?
#         Only when the SERVER is started with a reasoning parser
#         (e.g. vLLM's `--reasoning-parser qwen3`) AND the model emits
#         a <think>...</think> block. Otherwise the field is absent
#         (vanilla OpenAI/Anthropic cloud, plain Ollama, etc.).
#         Using getattr() makes this same code work in BOTH cases —
#         defensive = portable.
#   (6) Get the visible reply:
#         content = msg.content or ""
#       WHY `or ""`?  msg.content can be None (e.g. cut off at max_tokens).
#       `None or ""` evaluates to "". Safer than calling .strip() on None.
#   (7) Print:
#         - if reasoning is truthy: print "[reasoning]\n<reasoning>\n"
#         - always:                 print "[assistant]\n<content>\n"
#   (8) Append the assistant turn back to `messages`:
#         {"role": "assistant", "content": content}
#       IMPORTANT: append ONLY content, NOT reasoning. Reasoning is a
#       one-shot scratchpad; replaying it would confuse the model.

def chat_once(user_text: str) -> None:
    """One round-trip: append user turn, call model, print, append assistant turn."""
    # TODO 6: implement steps 1-8 from the comment block above.
    # Bỏ tin nhắn của user vào cuối danh sách lịch sử ( nhét câu hỏi vào hộp kí ức - memory box)  :
    messages.append({"role": "user", "content": user_text})
    
    # In ra màn hình để debug xem danh sách đang dài bao nhiêu tin nhắn:
    print(f"  -> sending {len(messages)} messages to server")
    
    # Thực hiện gọi API qua mạng nội bộ ( gửi toàn bộ hộp kí ức lên server vLLM):
    resp = client.chat.completions.create(
        model = MODEL,
        messages = messages,
        max_tokens = 1024
    )
    # Server trả về 1 hộp quà lớn -> bóc vỏ để lấy gói tin của AI 
    # `resp.choices` là một list (dù chỉ có 1 lựa chọn, vẫn là list). Lấy phần tử đầu tiên, rồi lấy `.message`:
    msg = resp. choices[0].message
    # Lấy phần "reasoning" (nếu có, nếu không có thì None):
    reasoning = getattr(msg, "reasoning", None)
    # Lấy phần "content" (câu trả lời của assistant). Nếu content là None thì thay bằng "" để tránh lỗi khi in:
    content = msg.content or ""
    
    # In kết quả ra màn hình cho người dùng xem 
    if reasoning: 
        print(f"[reasoning]\n{reasoning}\n")
    # Luôn luôn in câu trả lời của assistant, dù có reasoning hay không:
    print(f"[assistant]\n{content}\n")
    #(8) Bỏ câu trả lời của assistant vào cuối danh sách lịch sử, để lần sau model còn nhớ:
    messages.append({"role": "assistant", "content": content})
    


#chat_once("Hello world")  # test the function before implementing main()

# ===================================================================
# SECTION 7 — main(): THE INTERACTIVE INPUT LOOP
# ===================================================================
# Pseudo-code:
#     print connection info: BASE_URL, MODEL, how to quit
#     loop forever:
#         try:
#             user_text = input("[you] ").strip()
#         except (EOFError, KeyboardInterrupt):
#             # Ctrl-D / Ctrl-C -> quit gracefully
#             print "\nBye."
#             return
#         if user_text is empty:
#             continue                # skip this iteration, prompt again
#         if user_text in {"exit", "quit"}:
#             print "Bye."
#             return
#         chat_once(user_text)
#
# Python bits you may need:
#     input(prompt)           blocks, returns the typed line (no trailing "\n")
#     "  abc  ".strip()       -> "abc"
#     while True:             infinite loop, exit with break / return
#     try: ... except (A, B): catch multiple exception types at once
#     continue                jump back to the start of the loop
#     return                  exit the current function
#     "x" in {"a","b","x"}    True; sets are great for "is one of" checks

def main() -> None:
    # TODO 7: implement the loop following the pseudo-code above.
    """ Vòng lặp chính của giao diện CLI """
    print("Welcome to the QWEN3 Chat Agent !")
    print("Type your message here and press Enter to chat with the model. Press Ctrl+C or type 'exit' to quit.\n")

    # Vòng lặp vô hạn giúp chat liên tục cho đến khi người dùng muốn thoát:
    while True:

        
        # lấy input từ người dùng, xử lý Ctrl+C / Ctrl+D để thoát:
        try :
            user_input = input("[you] ").strip() 
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break
        
        if user_input.lower() in {"exit", "quit"}:
            print("Bye.")
            break
        
        if not user_input:  # nếu người dùng chỉ nhấn Enter mà không gõ gì, bỏ qua và hỏi lại
            continue
          
        # Gọi hàm chat_once để xử lý câu hỏi của người dùng:  
        chat_once(user_input)
        
        
# ===================================================================
# SECTION 8 — ENTRY POINT GUARD
# ===================================================================
# Every Python file has a magic variable `__name__`:
#   - run directly with `python file.py` -> __name__ == "__main__"
#   - imported by another file           -> __name__ == "file"
#
# The conventional guard below makes main() run only when this file
# is executed directly. If someone does `import 01_chat` later, the
# loop won't auto-fire (useful for testing/reuse).

# TODO 8: write the standard `if __name__ == "__main__":` guard
#         and call main() inside it.
if __name__ == "__main__":
    main()  