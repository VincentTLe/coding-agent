"""
agent.py — ReAct-style coding agent that uses tools to complete a task.

WHAT THIS FILE DOES
  Takes a natural-language goal, calls an LLM that may invoke tools
  (read_file / write_file / run_bash), keeps looping until the model
  is satisfied (returns content with no more tool_calls), or we hit
  `max_iters` and give up.

KEY DIFFERENCE FROM 01_chat.py
  01 only had `messages` + `content`. Here we ALSO have:
    - `tools=TOOL_SCHEMAS` in the API call (tell model what it can call)
    - `msg.tool_calls` to read (what the model wants to call)
    - role="tool" messages we append back (results of calls)

THE REACT LOOP (the heart of every modern coding agent)
   1. Send messages + tool schemas to the LLM.
   2. LLM responds either with plain content (it's done) OR with one or
      more tool_calls (it wants to do something).
   3. If content-only -> return. If tool_calls -> execute each, append the
      tool result to messages, loop.
   4. Stop if we exceed max_iters as a safety net.

WHEN DONE
  cd ~/code/coding-agent && source .venv/bin/activate
  python -m src.agent "Fix the failing test in demo_repo/"
  (Or use examples/05_agent_loop.py for the prettier demo CLI.)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

from src.tools import TOOL_SCHEMAS, execute_tool, set_workspace
from src.prompts import SYSTEM_PROMPT

# ---------------------------------------------------------------------------
# Setup (same shape as 01_chat.py)
# ---------------------------------------------------------------------------

load_dotenv()
BASE_URL = os.environ["VLLM_BASE_URL"]
MODEL = os.environ["VLLM_MODEL_NAME"]
API_KEY = os.environ.get("VLLM_API_KEY", "not-needed")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

# Rule C says verbose by default. Using `logging` (not print) so we can
# redirect to a file later for fine-tuning data collection in Phase 3.
logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("agent")


# ---------------------------------------------------------------------------
# The agent loop
# ---------------------------------------------------------------------------

def run_agent(goal: str, max_iters: int = 15) -> None:
    """Run the ReAct loop until the model stops calling tools, or max_iters.

    ReAct = Reasoning + Acting interleaved. Each iteration:
      - reason: model thinks, may produce visible content.
      - act:    model emits tool_calls (or nothing -> we're done).
      - observe: we execute each tool and append result as role=tool.
    Termination: model returns NO tool_calls (it has decided it's done).
    """
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": goal},
    ]

    for i in range(1, max_iters + 1):
        log.info(f"\n=== Turn {i} (history: {len(messages)} messages) ===")

        # ------------------------------------------------------------------
        # TODO 1: Call the chat-completion API.
        #
        # Compared to 01_chat.py, you must ALSO pass:
        #     tools=TOOL_SCHEMAS,
        #     tool_choice="auto",
        # so the model is allowed to decide whether to call a tool.
        # ------------------------------------------------------------------
        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOL_SCHEMAS,
            # why? "auto" lets the model itself decide: call a tool, OR just talk.
            # "required" would force a tool call every turn (we don't want that —
            # the model needs to be able to say "done" with plain content).
            tool_choice="auto",
            max_tokens=2048,
        )

        # ------------------------------------------------------------------
        # TODO 2: Pull out the model's message (same as 01_chat.py).
        # ------------------------------------------------------------------
        msg = resp.choices[0].message

        # ------------------------------------------------------------------
        # TODO 3: Append the assistant message to `messages`.
        #
        # Unlike 01_chat.py, we cannot just append {"role": "assistant",
        # "content": content} — we need to preserve `tool_calls` too,
        # otherwise the next API call rejects the conversation as malformed
        # (the tool result messages that follow would reference tool_call_ids
        # that no longer exist in the assistant turn before them).
        # ------------------------------------------------------------------
        # why? model_dump(exclude_none=True) turns the Pydantic message
        # object into a plain dict suitable for the messages list,
        # dropping null fields so the API doesn't choke on `"audio": null`
        # and similar provider-specific extras.
        messages.append(msg.model_dump(exclude_none=True))  # type: ignore[arg-type]

        # ------------------------------------------------------------------
        # TODO 4: If the model returned any visible content, log it.
        # ------------------------------------------------------------------
        if msg.content:
            log.info(f"[assistant] {msg.content}")

        # ------------------------------------------------------------------
        # TODO 5: If the model did NOT call any tools, it's done. Exit.
        # ------------------------------------------------------------------
        if not msg.tool_calls:
            # why? The model decides termination, not us. When it stops asking
            # for tools, we trust it; if it's wrong, we'll see in evaluation.
            log.info("\nAgent finished.")
            return

        # ------------------------------------------------------------------
        # TODO 6: For each tool_call, execute and append the result.
        # ------------------------------------------------------------------
        for tc in msg.tool_calls:
            # why? log the call BEFORE running it so a hanging tool is debuggable.
            log.info(f"[tool] {tc.function.name}({tc.function.arguments})")

            result = execute_tool(tc.function.name, tc.function.arguments)

            # why? truncate long results in the log only; the model still sees
            # the FULL result via the appended tool message below.
            preview = result if len(result) < 500 else result[:500] + "...[truncated]"
            log.info(f"[tool result]\n{preview}")

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,    # why? must match the id from msg.tool_calls
                                          # so the API knows which call this answers.
                "content": result,
            })
        # End of for — fall through to next iteration.

    log.warning(f"\nAgent hit max_iters={max_iters} without finishing.")


# ---------------------------------------------------------------------------
# Entry point — `python -m src.agent "goal"`
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.agent 'task description'")
        print("Example: python -m src.agent 'Fix the failing test in demo_repo/'")
        sys.exit(1)

    # Pin the tool sandbox to demo_repo/. Without this, file ops default to
    # the project root and the agent could happily edit its own source.
    set_workspace(Path(__file__).parent.parent / "demo_repo")

    task = " ".join(sys.argv[1:])
    log.info(f"GOAL: {task}\n")
    run_agent(task)
