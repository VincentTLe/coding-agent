# GAIA reference

Source: gaia-benchmark/leaderboard (https://huggingface.co/spaces/gaia-benchmark/leaderboard), Inspect AI eval (https://ukgovernmentbeis.github.io/inspect_evals/evals/assistants/gaia/), HF Agents course (https://huggingface.co/learn/agents-course/unit4/what-is-gaia)

## What it tests
General AI Assistant tasks: 466 real-world questions requiring reasoning + multimodality + web browsing + tool use. From Meta + HuggingFace + AutoGPT authors. Three levels (1=easy, 3=hard).

## Setup
- pip install inspect_ai inspect_evals
- HF_TOKEN env var (must request dataset access via HF form).
- Docker needed for bash tool execution sandbox.
- `inspect eval inspect_evals/gaia --limit 10` to start small.
- Model via OpenAI-compatible endpoint → works with local vLLM.

## Cost / hardware
- No heavy compute for the harness itself.
- Cost is in agent loop: web browsing + multimodal tool calls. Per-task input tokens can be very large (web pages, images).
- With local Qwen on 2× A6000 via vLLM: hardware-free; only external web fetch tools matter.

## Leaderboard (May 2026)
- Validation set leader: OpenAI Deep Research = 72.57% (Feb 2026).
- Test set: Trase = ~67%, validation 70.3%.
- Public leaderboard hosted on HF Space; submit JSONL answers.

## Realistic vs synthetic
Realistic. Hand-crafted questions, real web, real files. But: tasks require external web access — answers can drift if a referenced page changes. Some answer keys are gated (held-out test).

## Critical
- Multimodal (image, audio, PDF). Qwen 3.6-27B is text-only via vLLM by default — would need to add tool wrappers for image OCR / PDF extraction.
- 300 test questions are hidden; only 165 validation are public for iteration.
