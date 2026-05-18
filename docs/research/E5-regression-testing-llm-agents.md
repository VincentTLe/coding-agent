# E5 — Regression testing for non-deterministic LLM-calling code (2026)

## TL;DR
The smoke test for an agent that must "fix the failing pytest in `demo_repo/`" should be **outcome-based**: sandbox a copy of the repo, run the agent, then run pytest and assert the previously-failing test now passes and previously-passing ones still pass (SWE-bench F2P/P2P). Under it, layer **VCR cassettes (`pytest-recording`)** for agent control-flow unit tests, **Syrupy snapshots** for structured tool-call payloads, and **DeepEval `assert_test`** as a PR gate on a small golden set. Use `temperature=0` + `seed` (best-effort, never guaranteed per OpenAI's cookbook) and `epochs>=3` with majority-vote scoring for residual noise.

## Why this is hard
Pytest `assert ==` presumes determinism; LLMs are not deterministic even at `temperature=0` and fixed `seed`. Three regression modes drive tool choice:
1. **Prompt regression** — output shape breaks the parser (snapshot/cassette catches cheaply).
2. **Behavior regression** — plan changes; "valid but wrong" (golden-trace or LLM-judge).
3. **Outcome regression** — agent fails the task (only end-to-end smoke test catches this).

## State of the art (2026)
- **Snapshot**: Syrupy v5.x (MIT, pytest>=8) dominates Python; pytest-insta is the alternative with a review TUI. Both compare live Python objects with matchers that mask non-determinism (`path_type` for UUIDs/timestamps).
- **VCR / cassettes**: vcrpy 8.x + pytest-recording 0.13.x. Cassettes keyed by request body, so prompt diff = cassette miss. Filter `authorization` via `vcr_config`.
- **Eval frameworks**: DeepEval 4.x is pytest-native (`assert_test`). RAGAS = RAG-specialist. Promptfoo = YAML/CLI, strongest for red-teaming and prompt sweeps (now under OpenAI per its homepage — [UNVERIFIED]). Inspect AI (UK AISI) is the heavyweight harness — tasks/solvers/scorers/sandboxes, 200+ canned evals.
- **Golden-trace**: still mostly DIY; LangSmith pytest integration (SDK v0.3+) is closest off-the-shelf.
- **Semantic equivalence**: cosine on sentence embeddings, threshold ~0.85–0.95; pin the embedding model — it drifts on upgrades.

## Most used (community signal, 2026)
Agent glue-code unit tests: **pytest-recording**. Structured-output regression: **Syrupy**. PR gate: **DeepEval**. Benchmark-grade: **Inspect AI**. Prompt sweeps / red-team: **Promptfoo**.

## Comparison table

| Tool | Layer | Pytest native | Determinism strategy | Best for |
|---|---|---|---|---|
| Syrupy | Snapshot | yes | `path_type` matchers + temp=0/seed | structured tool-call payloads |
| pytest-insta | Snapshot | yes | matchers + review TUI | binary/pickle snapshots |
| pytest-recording (vcrpy) | Record/replay | yes | replay bytes; prompt diff = miss | agent control-flow tests |
| DeepEval | Eval / metrics | yes (`assert_test`) | threshold + multi-run avg | PR quality gate, golden set |
| RAGAS | Eval / metrics | callable | threshold + multi-run avg | RAG retrieval failures |
| Promptfoo | Sweep / red-team | no (CLI) | YAML asserts + llm-rubric | prompt/model A/B, red-team |
| LangSmith pytest | Eval / trace | yes (SDK v0.3+) | dataset-driven | LangChain/LangGraph apps |
| Inspect AI | Agent eval harness | no (own CLI) | `epochs=k`, pass@k | benchmark-grade agent evals |

## Recommendation for `coding-agent`
Three layers, all CI-gated:
1. **Outcome smoke test (load-bearing).** Copy `demo_repo/` to temp, confirm the canary fails, invoke the agent with `temperature=0` / fixed `seed` / pinned fingerprint, run `pytest demo_repo/`, assert F2P + P2P. Wrap with `epochs=3`, threshold pass@2/3 — single-run gating is noise.
2. **Cassette-backed unit tests.** `@pytest.mark.vcr` on planning/tool-routing tests for offline, deterministic runs. Filter `authorization`. Cassette diff *is* the prompt-regression signal.
3. **Snapshot + judge on the structured plan.** Syrupy snapshot of the parsed action plan with `path_type` masks; DeepEval `GEval` (threshold ≥0.8) for free-text fields.

Skip Inspect AI for now; revisit when the eval set crosses ~20 tasks.

## Next steps
1. Add `pytest-recording`, `syrupy`, `deepeval` to dev deps (TODO, no installs in this task).
2. Build `demo_repo/` with one intentionally failing test; commit failing state.
3. Write `tests/smoke/test_fix_failing_pytest.py` using the three-layer recipe.
4. Pin model fingerprint in `.env.test`; expose `LLM_SEED`, `LLM_TEMPERATURE`.
5. CI: `pytest --record-mode=none`; manual cassette-refresh workflow with `--record-mode=once`.

## Open questions
- How to detect silent VCR cassette drift when the hosted model is retrained? (Nightly `--record-mode=all` diff?)
- Is `temperature=0` + `seed` enough on our provider to skip multi-epoch on the outcome test? Measure.
- Local open-weights via vLLM (deterministic kernels) for tests + hosted model only in a "drift detector" suite? [UNVERIFIED tradeoff.]

## Sources
- Syrupy: https://github.com/syrupy-project/syrupy
- pytest-insta: https://github.com/vberlier/pytest-insta
- pytest-recording: https://github.com/kiwicom/pytest-recording ; vcrpy: https://vcrpy.readthedocs.io/
- DeepEval: https://github.com/confident-ai/deepeval ; https://deepeval.com/docs/evaluation-unit-testing-in-ci-cd
- RAGAS: https://docs.ragas.io/
- Promptfoo: https://www.promptfoo.dev/
- Inspect AI: https://inspect.aisi.org.uk/ ; https://github.com/UKGovernmentBEIS/inspect_ai
- LangSmith pytest: https://blog.langchain.com/pytest-and-vitest-for-langsmith-evals/
- OpenAI seed best-effort: https://cookbook.openai.com/examples/reproducible_outputs_with_the_seed_parameter
- Langfuse guide: https://langfuse.com/blog/2025-10-21-testing-llm-applications
- SWE-bench: https://www.swebench.com/SWE-bench/
- Eliminating flaky LLM tests with VCR: https://anaynayak.medium.com/eliminating-flaky-tests-using-vcr-tests-for-llms-a3feabf90bc5
- Non-determinism: https://www.sitepoint.com/testing-ai-agents-deterministic-evaluation-in-a-non-deterministic-world/
