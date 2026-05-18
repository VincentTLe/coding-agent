# F4 — Demo UI Options for an AI Coding Agent (May 2026)

## TL;DR

For the 2026-05-29 live demo, use **Chainlit**. It is the only option that renders tool calls and reasoning as collapsible cards *without writing UI code* — `@cl.step` auto-captures each tool's input, output, and duration. ~20-50 LOC of glue. Pin a recent version (community-maintained since 2025-05; two high-severity CVEs in late 2025) and verify in a real browser per Rule C, not curl.

## Why this matters

The advisor + classmates must *see each step* in 10-15 minutes: tool calls, outputs, reasoning, diffs. Prior pain point: a feature looked OK over curl but broke in browser. So we need (a) batteries-included step rendering, (b) low LOC, (c) good code-block + diff rendering, (d) browser verification.

## State of the art, May 2026

- **Chainlit** — `@cl.step` auto-renders nested tool-call cards; `config.ui.cot` toggles full / hidden / tool-calls-only; markdown + streaming + LangChain hooks built-in.
- **Gradio** — `ChatMessage(metadata={"title","id","parent_id","duration","status"})` for collapsible accordions; supports nesting.
- **Streamlit** — `st.status` + `st.code` + community `streamlit-code-diff`. Streaming requires manual callbacks.
- **Reflex** — pure-Python full-stack, 60+ components, no out-of-box agent step card.
- **Textual + Rich** — `RichLog` + `rich.syntax.Syntax`. Real coding-agent TUIs use it (Toad, OpenDev). `textual serve` for browser.
- **Vanilla HTML + SSE** — `text/event-stream`; de-facto LLM streaming protocol. Maximum control, maximum surface area.

## Most-used in 2026

Across six 2026 surveys: **Chainlit/Gradio dominate agent-chat-with-step-visibility**, **Streamlit dominates agent+dashboard**, **Textual is niche but fast-growing for terminal coding agents (Toad, Claude Code, Gemini CLI front-ends)**, **vanilla SSE is the post-framework production choice**. [UNVERIFIED — synthesized from 2026 articles, no single ranked survey.]

## Comparison

| Option | LOC | Auto step card | Code block | Diff | Replay | Pain risk |
|---|---|---|---|---|---|---|
| **Chainlit** | 20-50 | yes (`@cl.step`) | md | md ```diff``` | data layer | medium (CVEs) |
| **Gradio** | 25-35 | yes (`ChatMessage` meta) | md | md ```diff``` | save_history | low (HF) |
| **Streamlit** | 80-120 | manual (`st.status`) | `st.code` | community pkg | session_state | medium (rerun flicker) |
| **Reflex** | 200-400 | build it | `rx.code_block` | none | none | high (JS surface) |
| **Textual+Rich** | 150-300 | build it | `Syntax` | `Syntax` | asciinema | very low (no browser) |
| **Vanilla SSE** | 100-150+ | hand-built | highlight.js | diff2html | JSONL re-emit | highest |

LOC = honest minimum for "chat + streaming + nested tool-call cards + syntax-highlighted code," not hello-world.

## Recommendation

**Primary: Chainlit.** Wrap agent loop with `@cl.step(type="tool")` per tool + one `@cl.on_message` + `cl.Message().send()` for final. Smallest investment that satisfies "audience SEES each step." **Fallback: Gradio** if Chainlit CVE history blocks — same accordion pattern, HF-backed. **Reject:** Reflex (overkill), Streamlit (manual + rerun fights streaming), Textual (projector legibility), vanilla SSE (exact pain point).

## Next steps

1. `uv add chainlit`, pin to a 2026 release post-CVE.
2. `app.py`: `@cl.on_message` wrapping agent loop; one `@cl.step` per tool.
3. `.chainlit/config.toml` → `[UI] cot = "full"`.
4. Verify in **real browser** (Chrome + Firefox): multi-tool task, accordion nesting, streaming, code blocks. Log per Rule C.
5. Record `asciinema rec demo.cast` or OBS as Plan B.
6. Practice at projector resolution; bump browser zoom for back row.

## Open questions

- Specific Chainlit CVE IDs and patched versions. [UNVERIFIED]
- Does `@cl.step` cleanly wrap a Pi-style minimal loop where tools aren't OpenAI-function-typed?
- Asciinema vs OBS as the better Plan B?

## Sources

- Chainlit [Step](https://docs.chainlit.io/concepts/step), [GitHub](https://github.com/Chainlit/chainlit), [DeepWiki](https://deepwiki.com/Chainlit/chainlit/4-step-and-message-system)
- Gradio [Agents and Tool Usage](https://www.gradio.app/guides/agents-and-tool-usage), [ChatInterface](https://www.gradio.app/docs/gradio/chatinterface)
- Streamlit [st.status](https://docs.streamlit.io/develop/api-reference/status/st.status), [st.code](https://docs.streamlit.io/develop/api-reference/text/st.code), [streamlit-code-diff](https://github.com/evertoncolling/streamlit-code-diff)
- Reflex [reflex.dev](https://reflex.dev/), [2026 frameworks](https://reflex.dev/blog/2026-01-09-top-python-web-frameworks-2026/)
- Textual [textualize.io](https://textual.textualize.io/), [Log](https://textual.textualize.io/widgets/log/), [rich.syntax](https://rich.readthedocs.io/en/stable/syntax.html), [Toad](https://willmcgugan.github.io/announcing-toad/), [OpenDev arxiv 2603.05344](https://arxiv.org/html/2603.05344v3)
- 2026 comparisons [fast.io](https://fast.io/resources/best-ui-frameworks-ai-agents/), [Medium ATNO](https://medium.com/@atnoforgenai/streamlit-vs-gradio-vs-chainlit-building-quick-uis-for-your-ai-applications-138e3baa5317), [getstream.io](https://getstream.io/blog/ai-chat-ui-tools/), [ai-hive](https://www.ai-hive.net/post/mesop-streamlit-chainlit-and-gradio-a-comprehensive-comparison-of-ai-application-frameworks)
- SSE [MDN](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events), [procedure.tech 2026](https://procedure.tech/blogs/the-streaming-backbone-of-llms-why-server-sent-events-(sse)-still-wins-in-2025)
- Asciinema [docs](https://docs.asciinema.org/how-it-works/)
