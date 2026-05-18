# stdlib `logging` + Rich RichHandler — cached reference

Source: <https://rich.readthedocs.io/en/stable/logging.html> (Rich 14.1) and
<https://blog.vibe-eval.com/content/posts/python-logging-config-actually-works/>
(2026 setup post). Downloaded 2026-05-18.

## What RichHandler does

`rich.logging.RichHandler` is a `logging.Handler` subclass. It renders log
records in colorized columns: time, level (color-coded), message (syntax
highlighted), file path (optional, click-to-open in supporting terminals).
Drop-in replacement for `StreamHandler`.

## Minimal setup

```python
import logging
from rich.logging import RichHandler

logging.basicConfig(
    level="INFO",
    format="%(message)s",     # Rich draws the rest
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)
log = logging.getLogger("agent")
log.info("hello")
```

## Useful RichHandler kwargs

- `show_time=True/False` — time column.
- `show_level=True/False` — level column.
- `show_path=True/False` — file:line of the call site. Click-to-open in many
  terminals.
- `rich_tracebacks=True` — render `exception()` calls with syntax highlighting
  and local variable values.
- `tracebacks_show_locals=False` — hide locals in tracebacks (PII safety).
- `tracebacks_suppress=[...]` — list of modules to collapse in tracebacks
  (e.g. SDK internals).
- `markup=True` — interpret `[red]...[/red]` Rich markup in messages.
  Off by default.
- `keywords=[...]` — words to highlight in messages.

## Per-module levels via dictConfig

The 2026 "actually use" config uses `logging.config.dictConfig` to silence
chatty libraries without losing the rich formatting on your own logs:

```python
import logging.config

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"rich": {"format": "%(message)s", "datefmt": "[%X]"}},
    "handlers": {
        "rich": {
            "class": "rich.logging.RichHandler",
            "level": "DEBUG",
            "formatter": "rich",
            "rich_tracebacks": True,
            "show_path": True,
            "tracebacks_show_locals": False,
        },
    },
    "loggers": {
        "": {"level": "INFO", "handlers": ["rich"], "propagate": True},
        "httpx":        {"level": "WARNING", "propagate": True},
        "openai":       {"level": "WARNING", "propagate": True},
        "urllib3":      {"level": "WARNING", "propagate": True},
        "agent":        {"level": "DEBUG",   "propagate": True},
        "agent.tools":  {"level": "DEBUG",   "propagate": True},
    },
}
logging.config.dictConfig(LOGGING_CONFIG)
```

## Per-tool-call context (stdlib idiom)

`logging.LoggerAdapter` or `extra=` kwarg attach a dict per call:

```python
log = logging.getLogger("agent.tools.bash")
log.info("invoked", extra={"tool_call_id": tcid, "argv": argv})
```

For automatic propagation across nested calls / async tasks, use
`contextvars.ContextVar` and inject via a `logging.Filter`. (Structlog
does this natively; with stdlib you write ~15 lines of Filter glue.)

## Limitations to know

- RichHandler is human-pretty; if you also need JSON for log shipping,
  add a second handler (e.g. `python-json-logger`) on the same logger.
- Rich markup is OFF by default in logs to avoid surprise from user data.
- Tracebacks suppressed frames show file:line only, no code.
