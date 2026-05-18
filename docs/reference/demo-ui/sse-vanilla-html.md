# Vanilla HTML + Server-Sent Events (cache)

Sources: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events ; https://procedure.tech/blogs/the-streaming-backbone-of-llms-why-server-sent-events-(sse)-still-wins-in-2025

## Protocol

- Server response: `Content-Type: text/event-stream`, lines `data: ...\n\n`.
- Client: `const es = new EventSource("/stream"); es.onmessage = e => render(e.data);`
- Auto-reconnect built into browser; same protocol that OpenAI / Anthropic / most LLM APIs use natively.

## Minimal demo shape

- `app.py` (FastAPI): one `/stream` endpoint yielding agent events as SSE — ~40 LOC.
- `index.html`: one `<EventSource>` listener + minimal DOM updates — ~60-100 LOC including a code/diff renderer (highlight.js + diff2html or similar via CDN).
- Total: ~100-150 LOC, before any actual polish.

## Why for an agent demo

- Maximum control: every pixel is yours.
- Easy to record a session as JSONL on the server, replay it from disk by re-emitting the events — true replay.
- Trivial to embed in any slide deck (`<iframe>` or screen capture).

## Why probably not for this demo

- LOC and time cost are highest of the six options.
- The owner's prior pain point ("OK in curl, broken in browser") happens *exactly* here: the HTML/CSS/JS layer is hand-rolled, so the surface area for browser-vs-curl divergence is largest.
- No batteries — code-block syntax highlight, diff rendering, scroll behavior, auto-collapse of steps must all be hand-built or stitched from JS libraries.

## When it does pay off

- Long-running production UI where you'll keep iterating beyond the demo.
- Embedding into an existing web app.
- Need pixel-perfect branding, or specific accessibility requirements no framework supports.
