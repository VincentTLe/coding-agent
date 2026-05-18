# Research Summary — 30-topic Tech Survey

Generated 2026-05-18 by 30 parallel research agents (Claude Opus 4.7, web-verified per AGENTS.md Rule A). Each row points to its full report in `docs/research/<id>-<slug>.md`.

## The decided stack (cross-cutting picks)

| Layer | Choice | Justification (from full report) |
|---|---|---|
| Inference engine | **vLLM v0.21.0 (V1 engine)** | Only engine with first-class Qwen 3.6-27B Gated DeltaNet support on Ampere SM86 + native OpenAI tool/reasoning parsers. (B1, B2) |
| Model | **Qwen 3.6-27B BF16** (status quo); evaluate 35B-A3B | Best dense open-weight coder fitting 2× A6000 at full precision (SWE-V 77.2 / LCB v6 83.9); Apache 2.0. (C1) |
| Quantization | **None — stay BF16**; AWQ W4A16 + Marlin if forced later | 54 GB fits in 96 GB combined; FP8 unsupported on A6000. (B5) |
| Speculative decoding | **MTP, num_speculative_tokens=1** | Only method that works with Qwen 3.6's hybrid Gated DeltaNet; ~1.5-2× decode for zero setup. (B3) |
| KV cache | **prefix caching + chunked prefill (V1 defaults), explicit** | Heavy prefix reuse → 4.3s→0.6s TTFT on 10K reuse. Skip FP8 KV (A6000 unsupported) and swap-space. (B4) |
| Agent loop | **ReAct** | What every 2026 production coding agent (Claude Code, Codex, Cursor, Aider, OpenHands) actually runs; ~60 LOC over OpenAI SDK. (A1) |
| Tool calling | **OpenAI tools schema on the wire + vLLM `--tool-call-parser qwen3_coder`** | Native Qwen 3.6 format, zero adapter code. (A4) |
| System prompt | **Six-block structure** (identity → tone → tool-use → safety → planning → file/git) | Matches 2026 Claude Code / Cursor / AGENTS.md consensus; cache-friendly. (A2) |
| Error recovery | **Typed-termination + classified-retry + bounded-reflection (≤3) + repetition-detection** | Aider's `max_reflections=3`, Claude Code typed exits, OpenAI Agents SDK error classification. (A5) |
| Memory | **File-based** (CLAUDE.md + MEMORY.md + per-task notebook + LLM-summary on overflow) | Single-user CLI agent; full inspectability; clean migration path. (A3) |
| File-edit tool | **Exact string-replace** (`old_string`/`new_string` + read-before-edit + uniqueness check) | Claude Code, OpenHands, Aider-for-Claude all converge on this. (D2) |
| Shell tool | **Claude Code Bash-tool schema + OpenHands soft/hard timeouts** | Single string command + persistent shell; converged 2026 standard. (D3) |
| Sandbox | **bubblewrap (bwrap)** | Unprivileged, zero-cost, what Claude Code uses on Linux. (D1) |
| Web search | **SearXNG self-hosted + Tavily free tier (1K/month) as fallback** | Zero ongoing cost; Tavily fallback for student budget. (D4) |
| Code search | **ripgrep + ast-grep + LSP via Serena/pyright** | Three-layer stack matches Aider/Cursor/Claude Code. (D5) |
| Observability | **Langfuse self-hosted via Docker Compose** | MIT, drop-in OpenAI SDK, nested tool-call traces via `@observe`. (E1) |
| OTel | **Build to OTel-GenAI conventions via OpenLLMetry now** | Client-span attrs are de facto frozen; portable across Langfuse/Phoenix/Datadog. (E2) |
| Cost/token tracking | **vLLM `/metrics` + Prometheus + Grafana + Langfuse v3 custom pricing** | vLLM emits all needed metrics natively. (E4) |
| Package manager | **uv** | Single binary, ~10× faster than Poetry, locks cross-platform, installs CPython. (F1) |
| Ruff | **15-prefix select** (E,W,F,I,UP,B,C4,SIM,RUF,C90,N,PTH,ARG,S,PT,TID) + `ruff format` + pre-commit | Replaces flake8+black+isort+pyupgrade; skip D/ANN/PL upgrade-churn. (F2) |
| Testing | **FakeLLM fixture + respx + pytest-recording + Syrupy** | Three layers: unit (FakeLLM), SDK transport (respx), e2e (one vLLM cassette). (F3, E5) |
| Demo UI | **Chainlit** | Built-in `@cl.step` auto-renders nested tool-call cards; ~20-50 LOC of glue. (F4) |
| Logging | **stdlib `logging` + `rich.logging.RichHandler` via `dictConfig`** | One dep, plays with Langfuse/OTel, per-module levels, contextvars. (F5) |
| Code logging | **Per AGENTS.md Rule C — verbose by default** | Echo every tool invocation + result + reasoning. (cross-cutting) |
| SWE-Bench demo target | **35-45% pass on SWE-Bench Lite** (stretch 55%); **run 100-instance Verified subset** | Lite is 10-15pp easier than Verified; 100-instance run fits the May 29 deadline with debug headroom. (C2, E3) |
| Coding eval set | **LiveCodeBench v6 + BigCodeBench-Hard + HumanEval+ sanity** | LCB has contamination control via time windows; BCB-Hard is realistic Python+library. (C3) |
| Long-context eval | **RULER + LongBench v2 at 128K** | Establish our own bar — Qwen 3.6 has no published RULER scores. (C4) |
| Agent eval | **τ-bench (retail + airline)** + GAIA Level 1 stretch | Pure-pip setup, OpenAI-compatible, ~$40-80 to run on Qwen 3.6-27B. (C5) |

## Open questions to resolve before/during build

Aggregated from the 30 reports. Star (★) = must-resolve before the May 29 demo.

1. ★ **Tool-calling parser**: `qwen3_xml` vs `qwen3_coder` alias on the exact vLLM version we pin (A4). And whether streaming with `qwen3_coder` is fixed before demo (vLLM #31871) (A4).
2. ★ **Spec decode**: does MTP `num_speculative_tokens >= 2` work on BF16 TP=2 builds, or is the reported failure FP8-only? (B3)
3. ★ **A6000 throughput delta** vLLM vs SGLang for Qwen 3.6-27B — public benches are H100/H200/B200 only. (B2)
4. **Qwen 3.6-27B SWE-Bench submission**: model card claims 77.2% Verified but viewer dropdown doesn't list it. Reproducible trajectories? (C2)
5. **No official HumanEval/MBPP/LCB/BCB/MPL-E numbers for Qwen 3.6-27B** — we need to establish our own baseline. (C3)
6. **Real prefix-cache hit rate** on our agent prompt template — needs in-situ `prefix_cache_hit_rate` measurement. (B4)
7. **AWQ accuracy of `QuantTrio/Qwen3.6-27B-AWQ`** on SWE-Bench Verified / LiveCodeBench — not published by uploader. (B5)
8. **Qwen 3.6-27B's native XML tool format** vs OpenAI-SDK JSON on our harness — empirically unverified. (A2, A4)
9. **bubblewrap on lambdavector2**: does Ubuntu AppArmor allow unprivileged user namespaces? (D1)
10. **SearXNG upstream rate-limits** under heavy agent load → backoff/engine rotation needed? (D4)
11. **vcrpy/pytest-recording with vLLM streaming SSE** — works without custom `match_on`? (F3)
12. **vLLM `usage` field break-out for cached prompt tokens** so Langfuse can discount prefix-cache hits in cost calc. (E4)
13. **Langfuse license terms** post-ClickHouse acquisition (Jan 2026) — pin a known-good release tag. (E1)
14. **OTel-GenAI client-span stability**: spec page still says "Development" but used in production. (E2)
15. **Ship LSP layer (find_symbol / find_references) in v1 or defer?** (D5)
16. **Chainlit late-2025 CVE patches** — which version pins them? (F4)

## What to do next (after research, before coding)

Recommended sequence (1-2 days):

1. **Install uv** (`curl -LsSf https://astral.sh/uv/install.sh | sh`), run `uv sync`. Add `vllm`, `openai`, `python-dotenv`, `httpx` to `pyproject.toml` after confirming versions per B1/F1. (F1, B1)
2. **Launch vLLM** with the exact command from B1; verify `/v1/models` and a `chat.completions.create` round-trip with the OpenAI SDK. (B1)
3. **Test tool-calling end-to-end**: a one-line "list files" tool, with `--tool-call-parser qwen3_coder`. Resolves open question 1. (A4)
4. **Write the system prompt** per A2's six-block template. Cache `docs/reference/prompt-engineering/claude-code-prompt-structure.md` is the model.
5. **Implement the ReAct loop** from A1 (~60 LOC) with the recovery policies from A5.
6. **Add file-system + shell tools** per D2/D3 (string-replace edit, persistent-shell bash with timeouts).
7. **Wire Langfuse** (Docker Compose) for observability; instrument the OpenAI client via OpenLLMetry. (E1, E2)
8. **Add Chainlit UI** as a thin shell over the loop. (F4) — *verify in browser, not just curl* (per [[feedback_verify_in_browser]]).
9. **Smoke tests**: a single end-to-end test against vLLM cassette (F3) and a "fix the failing pytest in demo_repo/" SWE-Bench-Lite style task.
10. **Run 100-instance SWE-Bench Verified subset** ~1 week before demo (E3); target 35-45% Lite-equivalent (C2).

## File layout produced

```
docs/research/
  _SUMMARY.md                        ← this file
  A1..A5 / B1..B5 / C1..C5 / D1..D5 / E1..E5 / F1..F5   (30 reports, ~85-300 lines each, ~5,000 lines total)

docs/reference/                      ← 111 cached official-source summaries
  INDEX.md
  agent-benchmarks/  agent-memory/  agent-patterns/  agent-recovery/
  code-sandbox/      code-search/   coding-benchmarks/  coding-llms/
  cost-tracking/     demo-ui/       file-tools/         flash-attention/
  inference-engines/ kv-cache/      llm-observability/  llm-regression/
  long-context-evals/ nvidia-a6000/ otel-genai/         paged-attention/
  prompt-engineering/ pytest-llm/   python-logging/     python-package-mgr/
  quantization/      qwen-3.6-27b/  ruff/               shell-tool/
  speculative-decoding/ swe-bench/  swe-bench-harness/  tool-calling/
  vllm/              web-search-tools/
```

## Per-report quick reference

| ID | Topic | Pick | Report file |
|---|---|---|---|
| A1 | Agent loop patterns | ReAct | [A1-agent-loop-patterns.md](A1-agent-loop-patterns.md) |
| A2 | Prompt engineering | Six-block structure | [A2-prompt-engineering-coding-agent.md](A2-prompt-engineering-coding-agent.md) |
| A3 | Agent memory | File-based (Claude Code pattern) | [A3-agent-memory-architectures.md](A3-agent-memory-architectures.md) |
| A4 | Tool calling | OpenAI schema + `--tool-call-parser qwen3_coder` | [A4-tool-calling-schemas.md](A4-tool-calling-schemas.md) |
| A5 | Error handling | Typed-term + classified-retry + bounded-reflection | [A5-error-handling-and-recovery.md](A5-error-handling-and-recovery.md) |
| B1 | vLLM 2026 features | v0.21.0 with full flag set | [B1-vllm-2026-features.md](B1-vllm-2026-features.md) |
| B2 | vLLM vs SGLang vs TRT-LLM | vLLM v0.21.0 | [B2-vllm-vs-sglang-vs-tensorrt-llm.md](B2-vllm-vs-sglang-vs-tensorrt-llm.md) |
| B3 | Speculative decoding | MTP, n=1 | [B3-speculative-decoding.md](B3-speculative-decoding.md) |
| B4 | KV cache | Prefix caching + chunked prefill | [B4-kv-cache-optimization.md](B4-kv-cache-optimization.md) |
| B5 | Quantization | None now; AWQ+Marlin if forced | [B5-quantization-landscape-2026.md](B5-quantization-landscape-2026.md) |
| C1 | Open coding LLMs | Qwen 3.6-27B BF16; eval 35B-A3B | [C1-open-coding-llms-comparison.md](C1-open-coding-llms-comparison.md) |
| C2 | SWE-Bench 2026 | 35-45% Lite as demo target | [C2-swe-bench-2026.md](C2-swe-bench-2026.md) |
| C3 | Coding benchmarks | LCB v6 + BCB-Hard + HumanEval+ | [C3-coding-benchmarks-overview.md](C3-coding-benchmarks-overview.md) |
| C4 | Long-context evals | RULER + LongBench v2 at 128K | [C4-long-context-evals.md](C4-long-context-evals.md) |
| C5 | Agent benchmarks | τ-bench (retail+airline) + GAIA L1 | [C5-agent-benchmarks.md](C5-agent-benchmarks.md) |
| D1 | Code sandbox | bubblewrap (bwrap) | [D1-sandboxed-code-execution.md](D1-sandboxed-code-execution.md) |
| D2 | File-system tools | String-replace with read-before-edit | [D2-file-system-tools-design.md](D2-file-system-tools-design.md) |
| D3 | Shell tool | Claude Code Bash + OpenHands timeouts | [D3-shell-execution-tool.md](D3-shell-execution-tool.md) |
| D4 | Web search | SearXNG + Tavily free-tier fallback | [D4-web-search-tools.md](D4-web-search-tools.md) |
| D5 | Code search | rg + ast-grep + LSP-via-Serena | [D5-code-search-tools.md](D5-code-search-tools.md) |
| E1 | Observability | Langfuse self-hosted | [E1-llm-observability.md](E1-llm-observability.md) |
| E2 | OTel GenAI | Build to OTel-GenAI via OpenLLMetry | [E2-otel-genai-semantic-conventions.md](E2-otel-genai-semantic-conventions.md) |
| E3 | SWE-Bench locally | 100-instance Verified subset | [E3-running-swe-bench-locally.md](E3-running-swe-bench-locally.md) |
| E4 | Cost tracking | vLLM /metrics + Grafana + Langfuse | [E4-cost-token-tracking-vllm.md](E4-cost-token-tracking-vllm.md) |
| E5 | Regression testing | Outcome smoke + pytest-recording + Syrupy + DeepEval gate | [E5-regression-testing-llm-agents.md](E5-regression-testing-llm-agents.md) |
| F1 | Python package mgmt | uv | [F1-uv-vs-pip-poetry-pdm.md](F1-uv-vs-pip-poetry-pdm.md) |
| F2 | Ruff config | 15-prefix select + ruff format | [F2-ruff-config-python-3-12.md](F2-ruff-config-python-3-12.md) |
| F3 | pytest patterns | FakeLLM + respx + pytest-recording + syrupy | [F3-pytest-llm-testing-patterns.md](F3-pytest-llm-testing-patterns.md) |
| F4 | Demo UI | Chainlit | [F4-demo-ui-options.md](F4-demo-ui-options.md) |
| F5 | Logging | stdlib `logging` + Rich via dictConfig | [F5-python-logging.md](F5-python-logging.md) |

## Methodology and caveats

- All 30 agents ran in parallel, each with mandatory web-search per Rule A. Sources cited in each full report.
- Models, flags, and version numbers are accurate **as of 2026-05-18**. Per Rule A re-verify before pinning anything more than 30 days old.
- Per Rule B, official material was cached as markdown summaries (not raw HTML dumps) — 111 files across 35 tech-folders under `docs/reference/`. Search the `INDEX.md` for the canonical pointer.
- Where sources contradicted, the full report flags the disagreement. Where a claim couldn't be verified in ~2 min, the full report marks it `[UNVERIFIED]`.
