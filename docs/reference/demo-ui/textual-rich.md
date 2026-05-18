# Textual + Rich (TUI) for AI coding agent demo (cache)

Sources: https://textual.textualize.io/ ; https://textual.textualize.io/widgets/log/ ; https://rich.readthedocs.io/en/stable/syntax.html ; https://willmcgugan.github.io/announcing-toad/ ; arxiv 2603.05344 (OpenDev)

## Rich

- `rich.syntax.Syntax(code, "python", line_numbers=True, theme="monokai")` — pygments-backed code rendering for the terminal.
- Tables, markdown, progress bars, panels — same API works in plain terminal output and embedded in Textual widgets.

## Textual

- Modern TUI framework from the Rich team. Widgets: `Log`, `RichLog`, `DataTable`, `Tree`, `Input`, `TextArea`, `Tabs`, `Collapsible`.
- `Log` widget: streaming text, auto-scroll, append via `log.write_line(...)`. Pairs naturally with worker threads tailing a model stream.
- `RichLog`: like `Log` but accepts any Rich renderable (so you can append a `Syntax` block for code, a `Table` for tool output, a `Panel` for "thinking…").
- Apps run in terminal AND via `textual serve` in a web browser (WebSocket bridge) — same code, two surfaces.

## In-the-wild AI coding agent TUIs (2026)

- **Toad** — Will McGugan's universal TUI front-end for Claude Code / OpenHands / Gemini CLI / etc. Built on Textual. Explicit pitch: "superior UX for AI coding tools."
- **OpenDev** (arxiv 2603.05344 v3, 2026) — uses Textual TUI for the primary front-end; also exposes a FastAPI/WebSocket web UI. Implements thinking-mode + tool-call display, blocking modal approval prompts.

## Replay

- `textual run --headless --press ...` for scripted replays in tests.
- For live-demo replay: **asciinema** records the terminal session as a tiny `.cast` JSON file; replay at 0.1×-2× speed in any terminal, or embed via the asciinema-player JS on a webpage. Pairs cleanly with Textual since Textual output is just terminal text.

## LOC for a coding-agent TUI

- Bare REPL with streaming model output + tool-call panels: ~150-300 LOC across `app.py` + a couple of widget files. Higher than Chainlit/Gradio.
- Polish out-of-box is strong (proper layout, colors, scrolling) but takes longer per LOC than chat-only frameworks.

## Demo-room tradeoffs

Pro: zero browser surprises (the curl-vs-browser pain point is moot — it's the same terminal everyone watches), `textual serve` available if you must project a browser, asciinema replay is trivial.

Con: projector legibility — small font tough for back-row classmates. Some terminals on shared laptops lack 24-bit color → degraded palette. Need to font-size up and verify on actual demo display.
