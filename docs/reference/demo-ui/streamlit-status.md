# Streamlit st.status / st.code / st.chat (cache)

Sources: https://docs.streamlit.io/develop/api-reference/status/st.status ; https://docs.streamlit.io/develop/api-reference/text/st.code ; https://github.com/evertoncolling/streamlit-code-diff

## st.status — minimal example

```python
import streamlit as st, time

with st.status("Processing agent steps...", expanded=True) as status:
    st.write("Step 1: Analyzing input...")
    time.sleep(1)
    st.write("Step 2: Executing task...")
    status.update(label="Done", state="complete")
```

- States: `running` (spinner) | `complete` (checkmark) | `error` (red icon)
- `with` block auto-transitions to `complete` on exit
- Can stack arbitrary widgets inside (text, code, dataframes)

## Code / diff rendering

- `st.code(body, language="python", line_numbers=True)` — built-in syntax-highlighted block.
- Side-by-side diffs: not built-in. The `streamlit-code-diff` community component wraps `v-code-diff` for side-by-side or unified diffs with automatic theme detection.

## Chat primitives

- `st.chat_message("assistant")`, `st.chat_input()` — built since 2023.
- 2026: `st.container(autoscroll=True)` (release notes 2026) auto-scrolls to bottom — useful for streaming step logs.

## Agent-reasoning patterns

Streamlit + LangGraph human-in-the-loop pattern (MarkTechPost, 2026-02) uses `st.status` per node + interrupts for approvals. Gives full step visibility but ~80-150 LOC for a polished agent flow.

## LOC for an agent demo with tool-call display

- Plain chat: ~30 LOC
- Chat + per-tool `st.status` cards + `st.code` for diffs: ~80-120 LOC
- Tool-call streaming requires custom callbacks (no auto-observability)

## Limitations for live demo

- Re-runs whole script on each interaction → state must live in `st.session_state`, can flicker.
- Streaming intermediate steps requires manual implementation (vs Chainlit auto). [Source: fast.io 2026 guide]
