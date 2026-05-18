# Aider — Reflections / Edit-Error Recovery (cached)

Sources:
- https://github.com/Aider-AI/aider/blob/main/aider/coders/base_coder.py
- https://github.com/Aider-AI/aider/issues/3450 ("Only 3 reflections allowed, stopping.")
- https://github.com/Aider-AI/aider/issues/3713 (Gemini 2.5 Pro failing at SEARCH/REPLACE blocks until 3 retries)
- https://aider.chat/docs/troubleshooting/edit-errors.html
- https://aider.chat/HISTORY.html

## Hard-coded recovery budget
`base_coder.py` defines:
- `num_reflections = 0`
- `max_reflections = 3`

Loop in `run_one`:
- Set `self.reflected_message = None`.
- Send a message.
- If the response produced a `reflected_message` (e.g. malformed SEARCH/REPLACE block, lint error, test failure), loop and feed that reflected message back as the next user turn.
- Increment `num_reflections`. When it exceeds `max_reflections`, print **"Only {max_reflections} reflections allowed, stopping."** and stop.

So Aider's recovery is bounded at **3 reflection cycles per user request**, not an unbounded retry.

## What triggers a reflection
- `SearchReplaceNoExactMatch` — the LLM's SEARCH section didn't byte-match the file.
- Malformed edit block (missing fences, wrong header).
- (Optionally) lint or test errors that Aider re-feeds.

## Recovery prompt content
Aider feeds back the failed edit + an explanation of the format violation, asking the LLM to regenerate the block. The 2024–25 history notes that switching from "edit block" to "search/replace block" and "improved reflection feedback to LLMs using the diff edit format" reduced malformed-edit incidents.

## "Cannot proceed" exit
Aider does not have a model-driven "give up" signal. It exits the reflection loop purely on the 3-attempt cap. The user is then expected to /clear, /drop, switch model, or switch `--edit-format whole`.

## Architect mode as escalation
`--architect` splits planning model from edit-applying model — used as the human-recommended escalation when reflections keep failing.
