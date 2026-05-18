# DeepEval, RAGAS, Promptfoo (cached reference)

## DeepEval
- https://github.com/confident-ai/deepeval
- Version 4.0.2 (May 13, 2026). [UNVERIFIED — confirm on PyPI.]
- Pytest-native: `assert_test(test_case, [metric])` in a normal `test_*.py`.
- 30–50 metrics: G-Eval (LLM-judge), Answer Relevancy, Faithfulness, Task Completion, Tool Correctness, multimodal.
- Goldens / dataset abstractions; `evals_iterator()` for parametrized regression sweeps.
- Integrations: OpenAI Agents, LangChain, LangGraph, CrewAI, Pydantic AI.
- Companion SaaS (Confident AI) for trace storage; OSS metrics work fully local.

## RAGAS
- https://docs.ragas.io/
- Library for "systematic evaluation loops" with research-backed RAG metrics (faithfulness, answer_relevancy, context_precision, context_recall).
- 2026 scope extended to agent evaluation, but RAG is still the sweet spot.
- No first-class pytest plugin; commonly invoked from pytest as plain Python.

## Promptfoo
- https://www.promptfoo.dev/
- YAML / CLI driven; runs prompt/model A/B sweeps with assertions (`equals`, `contains`, `llm-rubric`, `cosine-similarity`, `javascript`, `python`).
- Strong red-teaming / adversarial suite (500+ attack vectors per 2026 alts pages).
- "Now part of OpenAI" per current homepage; remains open-source. [UNVERIFIED acquisition detail.]
- CI integration via `promptfoo eval --output results.json` + threshold checks; not a pytest plugin per se.

## Picking between them
- **DeepEval**: best PR-gate inside an existing pytest CI; metrics-as-asserts; minimal new tooling.
- **RAGAS**: pick if the agent's failure mode is "wrong retrieval" rather than "wrong action."
- **Promptfoo**: pick to sweep prompts/models and run security tests; less natural as a single-test PR gate.
