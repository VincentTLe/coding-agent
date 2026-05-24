"""
05_agent_loop.py — CLI wrapper around the ReAct agent in src/agent.py.

WHAT THIS FILE DOES
  Thin entry point for the demo: parses args, points the tool sandbox at a
  workspace directory, and calls `run_agent(task, max_iters)`. All real
  agent logic lives in `src/agent.py` — this file is just plumbing.

WHY SPLIT IT FROM src/agent.py
  Putting the CLI here lets `src/agent.py` be importable from elsewhere
  (e.g. `tests/test_agent_loop.py` mocking the LLM) without invoking
  argparse / sys.exit. Same separation-of-concerns as Click apps that
  put their CLI in __main__ and the logic in a library module.

DEMO COMMAND (the exact line to run during the prof checkpoint)
  cd ~/code/coding-agent && source .venv/bin/activate
  python examples/05_agent_loop.py "Fix the failing test in demo_repo/"

OPTIONAL FLAGS
  --max-iters N      cap on agent turns (default 15)
  --workspace PATH   directory the tools may read/write (default demo_repo)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# When run as a script (`python examples/05_agent_loop.py`), Python only puts
# `examples/` on sys.path. Add the project root so `from src...` works.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

# Import the agent module. We re-use ITS client, logger, run_agent — no
# duplication of API/env setup here.
from src.agent import run_agent
from src.tools import set_workspace


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Run the from-scratch coding agent on a single task.",
    )
    parser.add_argument(
        "task",
        nargs="+",
        help="Goal for the agent, e.g. 'Fix the failing test in demo_repo/'.",
    )
    parser.add_argument(
        "--max-iters", type=int, default=15,
        help="Maximum agent turns before giving up (default: 15).",
    )
    parser.add_argument(
        "--workspace",
        default=str(Path(__file__).resolve().parent.parent / "demo_repo"),
        help="Directory the tools (read/write/bash) are confined to.",
    )
    args = parser.parse_args()

    # Validate input TRƯỚC khi pin sandbox — không chốt workspace cho 1 lần
    # gọi sai (vd task rỗng). parser.error() in usage rồi exit(2).
    task_text = " ".join(args.task).strip()
    if not task_text:
        parser.error("task must not be empty")

    # Chốt sandbox (file ops + bash CWD) vào workspace TRƯỚC khi run_agent.
    # set_workspace() gọi .resolve() bên trong → mọi tool đọc/ghi đều bị
    # _safe_path() kẹp trong thư mục này, agent không thể leo ra sửa src/
    # hay /etc. Đây là ranh giới an toàn DUY NHẤT, nên phải set trước tiên.
    set_workspace(args.workspace)

    log = logging.getLogger("agent")
    log.info("=" * 60)
    log.info(f"  model    : {os.environ.get('VLLM_MODEL_NAME', '?')}")
    log.info(f"  endpoint : {os.environ.get('VLLM_BASE_URL', '?')}")
    log.info(f"  workspace: {args.workspace}")
    log.info(f"  max_iters: {args.max_iters}")
    log.info(f"  goal     : {task_text}")
    log.info("=" * 60)

    try:
        run_agent(task_text, max_iters=args.max_iters)
    except (KeyboardInterrupt, EOFError):
        log.info("\nInterrupted.")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
