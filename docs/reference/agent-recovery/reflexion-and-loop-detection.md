# Reflexion + Loop Detection (cached)

## Reflexion (Shinn et al., NeurIPS 2023; widely referenced through 2026)
Source: https://arxiv.org/abs/2303.11366

Algorithm:
1. Actor attempts the task and gets feedback (test result, env signal, eval).
2. On failure, a self-reflection model writes a **verbal critique** of why it failed.
3. The critique is appended to an **episodic memory buffer**.
4. Actor retries the task with the memory buffer in its context.

Headline coding number cited in the paper: **91% pass@1 on HumanEval** vs ~80% for the GPT-4 baseline at the time. Method does not update weights — purely in-context.

Implication for our agent: after a tool-call failure, ask the model to *explicitly diagnose what went wrong* before letting it pick the next action, rather than just feeding the raw error back.

## Loop / repetition detection (2025–2026 standard)
Sources: OpenClaw tool-loop detection docs, MiniMax M2.7 self-evolved scaffold note (MarkTechPost 2026-04), forum.cursor.com bug threads, anthropics/claude-code issue #29944 ("Model retries identical failing Edit tool call multiple times without diagnosing error").

Common detection signals:
- **Same tool + same args** seen N times within a sliding window.
- **Same error string** returned N times in a row (regardless of args).
- Same `(tool, hash(args))` pair appears > k times in the last m turns.
- Context-overflow → compact → exact-same-loop cycle.

Common responses, in escalation order:
1. **Inject a steering message**: "You've already tried X with result Y. Try a different approach or call AskUserQuestion."
2. **Dampen**: refuse to execute the duplicate call; return a synthetic tool_result telling the model to change tack.
3. **Abort**: end the loop with a `loop_detected` reason if the steering messages don't unblock progress.

Quote from the apxml.com / fast.io best-practice writeups: errors fall into four classes — **syntactic** (malformed JSON), **semantic** (valid but wrong), **environmental** (API/network/rate), **intentional** (hallucinated tool name) — and they need different retry policies. Only environmental errors are appropriate for raw exponential-backoff retry. Syntactic/semantic errors should re-prompt the model with the error inline (no backoff needed). Intentional errors (made-up tool) should be rejected and reported back, not silently retried.

## Backoff numbers cited
- 1s / 2s / 4s exponential with jitter is the conventional starting point for 429/5xx (markaicode.com, fast.io, mightybot.ai, chat-deep.ai).
- Anthropic SDK rate-limit errors are surfaced as `error_during_execution` with `is_error: true`.
