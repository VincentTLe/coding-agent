# Cached reference docs

Per AGENTS.md Rule B: when a non-trivial technology is introduced, its official docs are cached here.

Format: `<technology>: <URL>, downloaded YYYY-MM-DD, covers <topic>`

- Qwen3-14B: https://huggingface.co/Qwen/Qwen3-14B, downloaded 2026-05-17, covers architecture, tokenizer, BF16 weights, and context length for the model the project actually serves (Qwen3-14B on a single A6000) → `qwen3-14b/model-card-summary.md`
- vLLM parallelism + quantization: https://docs.vllm.ai/en/latest/serving/parallelism_scaling.html and https://docs.vllm.ai/en/latest/features/quantization/index.html, downloaded 2026-05-17, covers `--tensor-parallel-size` flag, NVLink guidance, supported quant methods (AWQ, GPTQ, FP8, INT4, ...) → `vllm/parallelism-and-quantization.md`
- FlashAttention: https://arxiv.org/abs/2307.08691 (v2 paper) + https://arxiv.org/abs/2205.14135 (v1), downloaded 2026-05-17, covers O(N) memory vs naive O(N²), block-wise tiling, 2-4× speedup → `flash-attention/key-claims.md`
- PagedAttention / vLLM paper: https://arxiv.org/abs/2309.06180, downloaded 2026-05-17, covers KV cache block management, 2-4× throughput over baseline serving systems → `paged-attention/key-claims.md`
- NVIDIA RTX A6000 spec: https://www.nvidia.com/en-us/design-visualization/rtx-a6000/, downloaded 2026-05-17, covers 48 GB GDDR6, 768 GB/s mem bw, 112 GB/s NVLink, Ampere (no native FP8) → `nvidia-a6000/specs-summary.md`

## 2026-05-18 — added by 30-topic research batch

Each agent cached its own per-technology summary(ies). Pointers below; see `docs/research/_SUMMARY.md` for picks per topic.

- agent-patterns (ReAct, Plan-and-Execute, Reflexion, ReWOO): arXiv 2210.03629 / 2305.18323 / 2303.11366 + LangChain plan-and-execute blog + https://code.claude.com/docs/en/agent-sdk/agent-loop, downloaded 2026-05-18 → `agent-patterns/*.md`
- prompt-engineering (Anthropic context engineering + Claude Code prompt structure): https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents, downloaded 2026-05-18 → `prompt-engineering/*.md`
- agent-memory (MemGPT, Letta, Mem0, Zep/Graphiti, Generative Agents, Claude Code memory, Cursor rules, context overflow): https://code.claude.com/docs/en/memory + papers, downloaded 2026-05-18 → `agent-memory/*.md`
- tool-calling (vLLM tool-calling parsers + OpenAI/Anthropic/Gemini schemas): https://docs.vllm.ai/en/stable/features/tool_calling/ + provider docs, downloaded 2026-05-18 → `tool-calling/*.md`
- agent-recovery (Claude Code loop, Aider reflections, Reflexion + loop detection): https://code.claude.com/docs/en/agent-sdk/agent-loop, downloaded 2026-05-18 → `agent-recovery/*.md`
- vLLM 2026 features (V1 engine, FP8 KV cache blog, spec decode flags, tool-call parsers): https://vllm.ai/blog/2026-04-22-fp8-kvcache + https://recipes.vllm.ai/Qwen/Qwen3-14B, downloaded 2026-05-18 → `vllm/features-2026.md`
- inference-engines (SGLang, TensorRT-LLM, comparison benchmarks): https://recipes.vllm.ai + sglang + tensorrt-llm docs, downloaded 2026-05-18 → `inference-engines/*.md`
- speculative-decoding (vLLM official docs, Qwen3 recipe, EAGLE-3 alternatives): https://recipes.vllm.ai/Qwen/Qwen3-14B + vLLM speculative-decoding docs, downloaded 2026-05-18 → `speculative-decoding/*.md`
- kv-cache (vLLM prefix caching design, FP8 KV blog, chunked prefill tuning, CPU swap): https://vllm-project.github.io/2026/04/22/fp8-kvcache.html + vLLM docs, downloaded 2026-05-18 → `kv-cache/*.md`
- quantization (vLLM support matrix): https://docs.vllm.ai/en/latest/features/quantization/, downloaded 2026-05-18 → `quantization/vllm-quantization-support-matrix.md`
- coding-llms (Qwen3-14B card, competitor cards): https://huggingface.co/Qwen/Qwen3-14B + DeepSeek/Llama/GLM cards, downloaded 2026-05-18 → `coding-llms/*.md`
- swe-bench (Verified top-15 May 2026, leaderboard, Qwen3 card): https://www.swebench.com + https://huggingface.co/Qwen/Qwen3-14B, downloaded 2026-05-18 → `swe-bench/*.md`
- coding-benchmarks (HumanEval/MBPP/EvalPlus, LiveCodeBench, BigCodeBench, MultiPL-E/EvalPerf/CodeContests/APPS, Qwen3 scores): https://livecodebench.github.io + benchmark sites, downloaded 2026-05-18 → `coding-benchmarks/*.md`
- long-context-evals (RULER overview, LongBench v2, NIAH and friends, Qwen long-context): https://github.com/NVIDIA/RULER + benchmark sites, downloaded 2026-05-18 → `long-context-evals/*.md`
- agent-benchmarks (τ-bench, GAIA, OSWorld, WebArena/SWE-Lancer/AgentBench): https://github.com/sierra-research/tau-bench + benchmark sites, downloaded 2026-05-18 → `agent-benchmarks/*.md`
- code-sandbox (e2b, Daytona, Modal, Firecracker/gVisor microVM, bubblewrap/nsjail/Docker): https://code.claude.com/docs/en/sandboxing + sandbox vendor docs, downloaded 2026-05-18 → `code-sandbox/*.md`
- file-tools (Claude Code tools reference, Aider edit formats, Codex CLI apply-patch, Morph fast-apply): https://code.claude.com/docs/en/tools-reference + Aider docs, downloaded 2026-05-18 → `file-tools/*.md`
- shell-tool (Claude Code Bash tool, OpenHands Bash tool, Aider /run): https://platform.claude.com/docs/en/agents-and-tools/tool-use/bash-tool + OpenHands docs, downloaded 2026-05-18 → `shell-tool/*.md`
- web-search-tools (Tavily pricing, SearXNG self-host): https://www.tavily.com/pricing + https://docs.searxng.org/, downloaded 2026-05-18 → `web-search-tools/*.md`
- code-search (ripgrep, ast-grep, LSP + Serena, Aider repomap): https://github.com/BurntSushi/ripgrep + https://github.com/oraios/serena + Aider docs, downloaded 2026-05-18 → `code-search/*.md`
- llm-observability (Langfuse, Phoenix self-host, OpenLLMetry, comparison): https://langfuse.com/docs/observability/sdk/python/instrumentation + Phoenix/OpenLLMetry, downloaded 2026-05-18 → `llm-observability/*.md`
- otel-genai (GenAI spans spec + 2026 instrumentor libs): https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/, downloaded 2026-05-18 → `otel-genai/*.md`
- swe-bench-harness (Epoch AI Docker walkthrough, official harness commands, mini-swe-agent runner): https://epoch.ai/blog/swebench-docker + SWE-bench harness, downloaded 2026-05-18 → `swe-bench-harness/*.md`
- cost-tracking (vLLM Prometheus metrics, electricity-cost formula, Langfuse custom pricing): https://docs.vllm.ai/en/stable/usage/metrics/, downloaded 2026-05-18 → `cost-tracking/*.md`
- llm-regression (Syrupy, pytest-recording/vcrpy, Inspect AI, DeepEval/ragas/promptfoo): https://langfuse.com/blog/2025-10-21-testing-llm-applications + tool docs, downloaded 2026-05-18 → `llm-regression/*.md`
- python-package-mgr (uv official, poetry/pdm/hatch): https://docs.astral.sh/uv/, downloaded 2026-05-18 → `python-package-mgr/*.md`
- ruff (configuration, linter rules, formatter, pre-commit, editor integration): https://docs.astral.sh/ruff/configuration/, downloaded 2026-05-18 → `ruff/*.md`
- pytest-llm (openai-responses-python, pytest-recording-vcr, respx, syrupy, OpenAI SDK mock patterns): https://callsphere.ai/blog/unit-testing-ai-agents-mocking-llm-calls-deterministic-tests + tool docs, downloaded 2026-05-18 → `pytest-llm/*.md`
- demo-ui (Chainlit step system, Gradio ChatMessage, Streamlit status, Textual/Rich, SSE vanilla HTML, Reflex): https://docs.chainlit.io/concepts/step + UI framework docs, downloaded 2026-05-18 → `demo-ui/*.md`
- python-logging (stdlib + Rich handler setup, loguru/structlog quickref): https://docs.python.org/3.12/library/logging.html + https://rich.readthedocs.io/en/stable/logging.html, downloaded 2026-05-18 → `python-logging/*.md`
