# F5 — Python logging for a verbose agent runtime (2026)

## TL;DR

For a from-scratch coding agent whose owner debugs by watching the screen,
the cleanest setup in 2026 is **stdlib `logging` + `rich.logging.RichHandler`**,
configured via `dictConfig`, with per-module levels and an optional second
JSON sink for later analysis. `print()` is too lossy, `loguru` is great but
adds a dependency and a non-standard global logger that fights stdlib-based
ecosystem tools (Langfuse, OTel, `uvicorn`), and `structlog` is the right
choice only once tooling for shipping logs to OpenTelemetry or Langfuse is
in place. The agent already has stdlib; bolting on Rich gives readable
multi-color output and click-to-file tracebacks with one dependency. Add
`structlog` only when log shipping arrives.

## Why this matters

Rule C in `AGENTS.md` requires verbose runtime: every tool invocation,
every tool result, every model reasoning step must be visible. The owner
learns by watching, so the live console output is the **primary** UI; log
files are secondary. That inverts the usual production picture (machines
read first, humans read fallback). The library choice therefore optimises
for: (1) legibility on a terminal, (2) per-tool-call context without
ceremony, (3) per-module level control so chatty `httpx`/`openai` doesn't
drown the agent's own logs, (4) a clean upgrade path to JSON + Langfuse
when observability work begins in F-week.

## State of the art (May 2026)

The 2026 Python logging landscape has three serious choices and one
non-choice ([Dash0 2026][dash0]; [BSWEN 2026][bswen]):

- **stdlib `logging`** — universal, integrates with every framework
  (FastAPI, uvicorn, Langfuse, OTel). Verbose to configure, but
  `dictConfig` makes per-module levels easy. Pair with Rich for pretty
  output or `python-json-logger` for JSON. [UNVERIFIED]: fastest overall
  when handlers do little work, per the Dash0 comparison.
- **loguru** — single-import global logger, zero-config defaults, built-in
  rotation/compression/JSON via `serialize=True`, `logger.catch` decorator
  for exceptions, `logger.contextualize()` for per-block context that is
  async-safe ([loguru overview][loguru]). Tradeoff: not a stdlib `Logger`;
  external libraries that target stdlib (Langfuse's `"langfuse"` logger,
  `uvicorn.access`) need an `InterceptHandler` bridge.
- **structlog** — processor pipeline emits an event dict that each
  processor (timestamp, level, context merge, JSON render) transforms in
  turn. Native `contextvars` integration is async- and thread-safe with no
  glue ([structlog contextvars][structlog]). 2026 benchmarks put it ~2x
  faster than stdlib/loguru for simple records and ~25% faster than loguru
  for JSON ([Dash0 2026][dash0]). Best path for OpenTelemetry: write JSON
  to stdout and let the OTel Collector convert to OTLP ([johal 2026][johal]).
- **`print()`** — fine for throwaway scripts; in a multi-tool agent it has
  no levels, no timestamps, no context, no JSON path, and can't be silenced
  per module. Rejected.

`print()` aside, the consensus across recent surveys is: start with loguru
for prototypes; pick stdlib for libraries; move to structlog when scaling
or when OpenTelemetry/Langfuse log export is required.

## Most used right now

- **Langfuse Python SDK** uses stdlib `logging` (logger name `"langfuse"`,
  default WARNING) and is built on OpenTelemetry's tracer/span model
  ([Langfuse advanced usage][lf]). This means anything routed through
  stdlib gets correlated with Langfuse spans for free.
- **OpenAI SDK, httpx, uvicorn, FastAPI, asyncio**: stdlib loggers.
- **Rich** has effectively become the default "pretty console" for Python
  CLI tools and is the same library used by `pip`, `pytest --rich`,
  `textual`, and most modern CLIs. RichHandler is a stdlib `Handler`
  subclass so it slots into `dictConfig` cleanly ([Rich logging][rich]).
- In agent codebases specifically, the public LangChain/LangGraph examples
  and Anthropic's own cookbook samples use stdlib `logging` + a pretty
  handler; structlog appears in production microservice posts but is rare
  in single-host research code.

## Comparison

| Criterion                                  | stdlib + Rich         | loguru               | structlog                | `print()` |
|--------------------------------------------|-----------------------|----------------------|--------------------------|-----------|
| Ease of first setup                        | medium (dictConfig)   | one-liner            | medium (configure call)  | trivial   |
| Pretty console for "watch the screen"      | **excellent** (Rich)  | very good            | good (ConsoleRenderer)   | poor      |
| Structured JSON output                     | add second handler    | `serialize=True`     | swap renderer            | no        |
| Per-module log levels                      | **native, easy**      | `enable/disable` only| via stdlib bridge        | none      |
| Per-tool-call context                      | `extra=` + Filter     | `bind`/`contextualize`| **`bind_contextvars`** | none      |
| Async safety                               | manual contextvars    | `contextualize` ok   | **native contextvars**   | n/a       |
| Langfuse integration                       | **direct**            | needs InterceptHandler| stdlib bridge           | no        |
| OpenTelemetry integration                  | direct via OTel handler| InterceptHandler    | best path (JSON→Collector)| no       |
| Performance (simple record) [UNVERIFIED]   | baseline              | ~= stdlib            | ~2x stdlib               | fastest   |
| Performance (JSON serialization) [UNVERIFIED]| n/a (handler-dep)   | baseline             | ~25% faster than loguru  | n/a       |
| Verbose tracebacks with locals             | yes (RichHandler)     | yes (`diagnose=True`)| yes (StackInfoRenderer)  | no        |
| New dependency vs stdlib                   | `rich`                | `loguru`             | `structlog`              | none      |
| Mental model load on owner                 | low (stdlib + theme)  | low                  | medium (processors)      | trivial   |

[UNVERIFIED] in the perf rows because the 2026 benchmarks cited by Dash0
and BSWEN are reported aggregates; the project hasn't run its own.

## Recommendation

**Use stdlib `logging` configured by `dictConfig`, with `RichHandler` as
the console sink.** No `print()` past the first hour of the project. Defer
loguru and structlog until the project has a concrete need they uniquely
solve.

Rationale tied to this project:
1. The owner must be able to explain every line (Rule C, plus the broader
   "explainable code" mandate). `logging` is in the standard library —
   `python -m pydoc logging` is the source of truth, no extra reading.
2. Rich gives the "watch the screen" upgrade with one dep and zero
   conceptual cost on top of stdlib.
3. Langfuse and OpenTelemetry both expect stdlib `logging`. When F-week
   (observability) lands, no rewrite is needed — only adding handlers.
4. `dictConfig` makes per-module levels (`httpx=WARNING`, `agent.tools=DEBUG`)
   declarative and editable from one place.

### Concrete starter config

Drop this in `agent/logging_config.py`:

```python
# agent/logging_config.py
import logging
import logging.config
from contextvars import ContextVar

# context that follows tool calls across async boundaries
_tool_call_id: ContextVar[str | None] = ContextVar("tool_call_id", default=None)
_task_id:      ContextVar[str | None] = ContextVar("task_id",      default=None)


class ContextFilter(logging.Filter):
    """Inject contextvars into every LogRecord so RichHandler can show them."""
    def filter(self, record: logging.LogRecord) -> bool:
        record.tool_call_id = _tool_call_id.get() or "-"
        record.task_id      = _task_id.get()      or "-"
        return True


LOGGING_CONFIG: dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"context": {"()": ContextFilter}},
    "formatters": {
        # Rich draws time + level + path; we add task/tool context to message.
        "rich":  {"format": "[%(task_id)s/%(tool_call_id)s] %(name)s: %(message)s"},
        "jsonl": {"format": "%(asctime)s %(levelname)s %(name)s "
                            "task=%(task_id)s tool=%(tool_call_id)s %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "rich.logging.RichHandler",
            "level": "DEBUG",
            "formatter": "rich",
            "filters": ["context"],
            "rich_tracebacks": True,
            "tracebacks_show_locals": False,
            "show_path": True,
            "markup": False,
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/agent.log",
            "maxBytes": 5_000_000,
            "backupCount": 3,
            "level": "DEBUG",
            "formatter": "jsonl",
            "filters": ["context"],
        },
    },
    "loggers": {
        # Project loggers — verbose by default (Rule C).
        "agent":       {"level": "DEBUG", "propagate": True},
        "agent.tools": {"level": "DEBUG", "propagate": True},
        "agent.model": {"level": "DEBUG", "propagate": True},
        # Noisy third-party — keep quiet.
        "httpx":    {"level": "WARNING", "propagate": True},
        "openai":   {"level": "INFO",    "propagate": True},
        "urllib3":  {"level": "WARNING", "propagate": True},
        "langfuse": {"level": "INFO",    "propagate": True},
    },
    "root": {"level": "INFO", "handlers": ["console", "file"]},
}


def configure() -> None:
    import os
    os.makedirs("logs", exist_ok=True)
    logging.config.dictConfig(LOGGING_CONFIG)


# Helpers callers use around each tool invocation.
def set_task(task_id: str)        -> None: _task_id.set(task_id)
def set_tool_call(call_id: str)   -> None: _tool_call_id.set(call_id)
def clear_tool_call()             -> None: _tool_call_id.set(None)
```

Usage from the agent loop:

```python
import logging
from agent.logging_config import configure, set_task, set_tool_call, clear_tool_call

configure()
log = logging.getLogger("agent.tools.bash")

set_task("task-007")
try:
    set_tool_call("call-3")
    log.info("invoking bash: %s", argv)
    result = run_bash(argv)
    log.debug("bash stdout (%d bytes):\n%s", len(result.stdout), result.stdout)
finally:
    clear_tool_call()
```

The owner sees, on screen, color-coded lines like:

```
[12:04:11] DEBUG    [task-007/call-3] agent.tools.bash: invoking bash: ['pytest', '-x']
```

Exceptions render with Rich's syntax-highlighted traceback automatically.
The JSON-ish file sink keeps an audit log for replay / Langfuse import.

### What to add later (not now)

- **JSONL export to Langfuse**: when F-week (observability) starts, add a
  third handler that posts to Langfuse via `@observe` decorators on tool
  functions — no changes to the rest of the logging code.
- **structlog migration**: only if/when log shipping to OpenTelemetry is on
  the roadmap and the processor pipeline starts paying for itself
  (redaction, sampling, trace-id injection). Until then, the extra mental
  model is not worth it for this project's scale.

## Next steps

1. Create `agent/logging_config.py` with the config above. (~50 LOC.)
2. Add `rich` to dependencies (`uv add rich`). Confirm the owner is OK with
   one dep — it is widely used (pip, pytest plugins, textual).
3. Sprinkle `set_task` / `set_tool_call` calls in the agent loop's tool
   dispatcher so every record carries task and call IDs.
4. Smoke test: run a multi-tool task; visually inspect that lines are
   readable, tracebacks render with locals off, and `httpx` is quiet.
5. Add an integration test that captures stdout via `pytest`'s `capsys`
   and asserts the agent emits at least one log line per tool call
   (enforces Rule C in CI).

## Open questions

- Does the owner want a `--quiet` flag for demo day (May 29) that swaps
  the console handler to `INFO`/`WARNING`? Rule C says verbose by default,
  but a demo audience may want less noise.
- File rotation policy: 5 MB × 3 backups is a guess; should align with
  whatever disk policy F-week settles on.
- When Langfuse arrives, decide whether tool inputs/outputs go in the log
  message (current plan) or only in Langfuse spans (cleaner, but the
  on-screen verbosity drops).

## Sources

- [Choosing a Python Logging Library in 2026 — Dash0][dash0]
- [Which Python Logging Library Should I Use in 2026 — BSWEN][bswen]
- [Loguru — Overview (readthedocs)][loguru]
- [structlog — Context Variables][structlog]
- [Rich — Logging Handler][rich]
- [Langfuse Python SDK — Advanced Usage][lf]
- [Structlog JSON Logs + OpenTelemetry middleware 2026 — johal.in][johal]
- [The Python Logging Setup I Actually Use in 2026 — Vibe Eval Blog][vibe]

[dash0]: https://www.dash0.com/guides/python-logging-libraries
[bswen]: https://docs.bswen.com/blog/2026-04-29-python-logging-library-choice/
[loguru]: https://loguru.readthedocs.io/en/stable/overview.html
[structlog]: https://www.structlog.org/en/stable/contextvars.html
[rich]: https://rich.readthedocs.io/en/stable/logging.html
[lf]: https://langfuse.com/docs/observability/sdk/python/advanced-usage
[johal]: https://johal.in/structlog-json-logs-middleware-opentelemetry-python-2026/
[vibe]: https://blog.vibe-eval.com/content/posts/python-logging-config-actually-works/
