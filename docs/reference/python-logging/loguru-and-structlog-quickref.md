# Loguru and structlog — cached quick reference

Sources:
- <https://loguru.readthedocs.io/en/stable/overview.html>
- <https://www.structlog.org/en/stable/contextvars.html>
- <https://www.dash0.com/guides/python-logging-libraries> (2026 comparison)

Downloaded 2026-05-18.

## Loguru in 30 lines

```python
from loguru import logger
import sys

logger.remove()                      # drop default handler
logger.add(sys.stderr, level="INFO", colorize=True,
           format="<green>{time:HH:mm:ss}</green> | "
                  "<level>{level: <8}</level> | "
                  "<cyan>{name}</cyan>:<cyan>{line}</cyan> - {message}")
logger.add("logs/agent.jsonl", level="DEBUG", serialize=True)  # JSON sink

# per-call context
logger.bind(tool="bash", call_id="t-42").info("running")

# scoped context (async-safe via contextvars)
with logger.contextualize(task_id="task-7"):
    logger.info("step 1")           # automatically tagged with task_id
```

Key facts:
- One global `logger`; no `getLogger("foo")` hierarchy. Per-module gating
  uses `logger.disable("pkg.mod")` / `logger.enable("pkg.mod")` instead
  of named levels.
- `add(sink, serialize=True)` writes JSON dicts.
- `enqueue=True` makes a sink multiprocess-safe (puts on a queue, worker
  thread drains).
- Tracebacks: `logger.catch` decorator or `backtrace=True, diagnose=True`
  on a sink gives variable-aware tracebacks (similar quality to Rich).
- OpenTelemetry: no native bridge — route via `InterceptHandler` so OTel's
  `LoggingHandler` can pick records up from stdlib.

## structlog in 30 lines

```python
import logging, structlog

logging.basicConfig(format="%(message)s", level=logging.INFO)

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,   # pull context from contextvars
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer(),           # pretty for humans
        # swap to JSONRenderer() in prod
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

log = structlog.get_logger("agent")

# bind context (async- and thread-safe via contextvars)
structlog.contextvars.bind_contextvars(task_id="task-7")
log.info("tool_invoked", tool="bash", argv=["ls", "-la"])
```

Key facts:
- **Processor pipeline**: each log event flows through an ordered list of
  callables. Easy to insert redaction, sampling, trace-id injection.
- `contextvars.bind_contextvars()` propagates context across `asyncio`
  tasks and threads automatically.
- Two renderers ship in-box: `ConsoleRenderer` (pretty, for the screen)
  and `JSONRenderer` (for log shipping). Toggle by env var.
- OpenTelemetry: structlog inherits OTel support "for free" when routed
  through stdlib's `LoggingHandler`. Alternatively, write JSON to stdout
  and let the OTel Collector convert.
- Roughly 2x faster than stdlib/loguru for simple messages; ~25% faster
  than loguru for JSON serialization per 2026 benchmarks.

## When to pick which

| Need                                          | Pick           |
|-----------------------------------------------|----------------|
| Smallest setup, single dev, prototype         | loguru         |
| Pretty human output + low-effort JSON         | loguru         |
| Hard requirement: OTel-native logs            | structlog      |
| Production microservices, redaction, sampling | structlog      |
| Zero new deps, library code                   | stdlib only    |
| "Owner debugs by watching the screen"         | stdlib + Rich  |
