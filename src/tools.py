"""
tools.py — The three tools the agent can call: read_file, write_file, run_bash.

Each tool is a Python function. The OpenAI-compatible API needs them described
as JSON schemas (TOOL_SCHEMAS below) so the model knows their shape. When the
model decides to call a tool, the SDK gives us back the name and a JSON string
of arguments — we route that through `execute_tool()`.

This file has three concerns kept side by side on purpose:
  1. The actual Python functions (what runs).
  2. The OpenAI schema for each (what the model sees).
  3. A single dispatch function `execute_tool()` (the glue).

Design note for the future: Phase 2+ will add more tools. Just append to TOOLS
and TOOL_SCHEMAS — agent.py needs no changes.
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

# Sandbox: confine file ops to this directory. Set to the demo_repo at startup
# (see agent.py main). Default to cwd so import-time use doesn't crash.
WORKSPACE = Path.cwd()


def set_workspace(path: str | Path) -> None:
    """Pin file operations to a directory. Call this once before run_agent()."""
    global WORKSPACE
    WORKSPACE = Path(path).resolve()
    log.info(f"[tools] workspace = {WORKSPACE}")


def _safe_path(path: str) -> Path:
    """Resolve path relative to WORKSPACE and refuse to escape it.

    Prevents the model from poking around /etc, ~/.ssh, etc."""
    p = (WORKSPACE / path).resolve()
    if WORKSPACE not in p.parents and p != WORKSPACE:
        raise ValueError(f"path {p} escapes workspace {WORKSPACE}")
    return p


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def read_file(path: str) -> str:
    """Return the full contents of a text file inside the workspace."""
    p = _safe_path(path)
    if not p.exists():
        return f"ERROR: file not found: {path}"
    text = p.read_text(encoding="utf-8", errors="replace")
    return text


def write_file(path: str, content: str) -> str:
    """Overwrite (or create) a text file inside the workspace.

    The agent MUST send the full new content — there is no patch/diff format
    in this version. Keep files small for the demo.
    """
    p = _safe_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"wrote {len(content)} chars to {path}"


def run_bash(command: str, timeout: int = 30) -> str:
    """Run a shell command inside the workspace, capturing stdout+stderr."""
    log.info(f"[tools] bash> {command}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"ERROR: command timed out after {timeout}s"

    parts = [f"exit_code: {result.returncode}"]
    if result.stdout:
        parts.append(f"stdout:\n{result.stdout}")
    if result.stderr:
        parts.append(f"stderr:\n{result.stderr}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Registry + JSON schemas
# ---------------------------------------------------------------------------

# Plain dict from name -> Python function. Used by execute_tool().
TOOLS = {
    "read_file": read_file,
    "write_file": write_file,
    "run_bash": run_bash,
}

# OpenAI-format JSON schemas. Each describes the tool the model is allowed to
# call. The model sees the `name`, `description`, and required arg shape.
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the full contents of a text file (path relative to workspace).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to the file."},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Overwrite (or create) a text file with the given content. Send the FULL new file body, not a diff.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to the file."},
                    "content": {"type": "string", "description": "Full new file content."},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_bash",
            "description": "Run a shell command in the workspace. Use for running tests (pytest), listing files (ls), etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute."},
                    "timeout": {"type": "integer", "description": "Seconds before kill (default 30)."},
                },
                "required": ["command"],
            },
        },
    },
]


def execute_tool(name: str, arguments_json: str) -> str:
    """Dispatch a tool call by name with a JSON string of arguments.

    The model gives us `arguments` as a string of JSON (never a dict). We parse,
    look up the function, call it, and stringify the result for the model.
    """
    if name not in TOOLS:
        return f"ERROR: unknown tool {name}. Available: {list(TOOLS)}"
    try:
        args = json.loads(arguments_json) if arguments_json else {}
    except json.JSONDecodeError as e:
        return f"ERROR: bad JSON arguments: {e}"
    try:
        result = TOOLS[name](**args)
    except TypeError as e:
        return f"ERROR: bad args for {name}: {e}"
    except Exception as e:
        return f"ERROR: {name} crashed: {e}"
    return str(result)
