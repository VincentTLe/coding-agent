# Inspect AI (cached reference)

Sources:
- https://inspect.aisi.org.uk/
- https://github.com/UKGovernmentBEIS/inspect_ai
- https://hamel.dev/notes/llm/evals/inspect.html

- Open-source Python framework from the UK AI Security Institute (AISI), with Meridian Labs contributions.
- Core abstractions: `Task` (composes `dataset` + `solver` + `scorer`), evaluated via `inspect eval ...`.
- Solvers: built-ins like `generate()`, `chain_of_thought()`, `self_critique()`; you can write custom solvers that call external agents (Claude Code, Codex CLI, Gemini CLI) and grade their patch.
- Scorers: text comparison, model-graded fact checks, custom Python scorers.
- 200+ pre-built evaluations in `inspect_evals`, including coding (HumanEval, MBPP, SWE-bench variants) and agentic tasks; 2026 OWASP Top 10 for Agentic Applications coverage.
- Web-based `Inspect View` for trace inspection and a VS Code extension.
- Not a pytest plugin — runs its own evaluation harness, but can be invoked from CI alongside pytest.

LLM-specific usage notes for a "fix a failing pytest" smoke test:
- Model the task as: dataset sample = (repo snapshot, failing test id); solver = run agent under test in a sandbox; scorer = run the previously-failing test and assert it now passes plus no previously-passing test fails (SWE-bench-style F2P / P2P).
- Use the sandbox feature (Docker / k8s) so the agent's shell is isolated.
- Use `epochs=k` and majority-vote / pass@k scoring to absorb non-determinism instead of trying to make a single run deterministic.
