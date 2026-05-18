# Claude Code system prompt — structural notes (leaked, Opus 4.7)

Sources (downloaded 2026-05-18):
- https://github.com/asgeirtj/system_prompts_leaks/blob/main/Anthropic/claude-code.md
  (Claude Opus 4.7 / Claude Code leak — updated through 2026)
- https://www.infoq.com/news/2026/04/claude-code-source-leak/
  (npm sourcemap leak, Mar 31 2026 — context)
- https://medium.com/coding-nexus/claude-codes-entire-system-prompt-just-leaked-10d16bb30b87

## High-level section layout

1. **Identity / persona** — "interactive agent that helps users with software
   engineering tasks." One sentence.
2. **Tone & output policy** — "Brief is good — silent is not." Complete
   sentences, no jargon. Match length to task complexity. End-turn summaries
   capped at one or two sentences. Users can't see tool calls or thinking, so
   surface key results in text.
3. **Tool-use rules** — Prefer dedicated tools (Read, Glob, Grep) over bash.
   Denied call ≠ retry verbatim; adjust. Parallelize independent calls in one
   response. Never invent tool names.
4. **Security & authorization** — Permits authorized security work
   (pentests, CTFs, defensive). Refuses destructive/offensive/mass-targeting.
   Dual-use tools need explicit authorization context.
5. **Git safety protocol** — No force-push, no `--no-verify`, no `reset --hard`
   unless explicitly requested. Don't commit `.env` / secrets.
6. **File operations** — Read before edit. Never re-read after Edit/Write.
   Prefer Edit over Write for existing files.
7. **Chain-of-thought / planning** — Explain what you're trying to do and why.
   Never delegate *understanding* to subagents — synthesis stays with the
   primary assistant.
8. **Memory** — File-based, four categories: user profile, feedback/guidance,
   project context, external references. Excludes code patterns derivable from
   inspection.
9. **Refusal language** — Anti-jailbreak via "only invoke a skill that
   appears in the list — never guess or invent."

## Notable tactics worth stealing
- "Independent tool calls can run in parallel in one response."
- "If you intend to call multiple tools and there are no dependencies, make
  all the independent calls in the same block."
- "Avoid emojis unless asked."
- "Never proactively create *.md or README files."
- Skill / tool gating: a denied call means the user said no — adapt the plan,
  do not retry the same call.

## Cursor / Aider / AGENTS.md cross-reference
Sources:
- https://github.com/jujumilk3/leaked-system-prompts/blob/main/cursor-ide-sonnet_20241224.md
- https://github.com/agileandy/aider-prompt
- https://github.blog/ai-and-ml/github-copilot/how-to-write-a-great-agents-md-lessons-from-over-2500-repositories/
- https://agents.md/

Common pattern across coding agents:
- Identity → tone → tools → safety → planning → output format.
- AGENTS.md (Linux Foundation, Dec 2025) is the project-side complement to
  the agent's built-in prompt. 60k+ repos. "Always do / Ask first / Never do"
  three-tier boundaries. Show one good code snippet beats three paragraphs.

## Qwen3 / Qwen3-Coder specifics
Sources:
- https://github.com/QwenLM/Qwen3-Coder
- https://qwen.readthedocs.io/en/stable/framework/function_call.html
- https://huggingface.co/blog/qwen-3-chat-template-deep-dive

- Qwen3 ships without a default system prompt — supply one explicitly.
- ChatML format (`<|im_start|>system` / `<|im_end|>`).
- Hermes-style tool use recommended; native XML `<function=name>` /
  `<parameter=x>` is what the model was trained on.
- 256K native context (1M with YaRN).
- 2026-05-18 chat-template fix: removes empty `<think></think>` blocks that
  were causing premature agent-loop aborts.
</content>
</invoke>