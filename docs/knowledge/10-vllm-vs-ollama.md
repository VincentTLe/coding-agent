# 10 — vLLM vs Ollama

## Core idea (1-2 sentences)

vLLM and Ollama both serve open-weight LLMs locally, but optimize for different problems. vLLM optimizes **throughput** for multi-user/multi-request workloads via continuous batching and PagedAttention. Ollama optimizes **ergonomics** for single-user, multi-model local experimentation via a CLI built on llama.cpp.

## Why it matters for our project

The agent we're building will issue many model calls — one per ReAct step, sometimes in parallel for branching exploration. vLLM serves these efficiently; Ollama can't batch effectively beyond one request. Plus vLLM exposes the OpenAI-compatible API natively, which lets us use the standard `openai` Python SDK without adapters.

But Ollama still has its place on this server (open-webui, casual chat, swapping between many models) and the user already runs it for other purposes. **We are not displacing Ollama**; we are running vLLM in parallel for the agent backend.

## The intuition

- **Ollama** is a TV remote control. Press a button, get a model. Switch channels at will. Designed for one person watching one show at a time.
- **vLLM** is a cinema. Designed for hundreds of seats filled simultaneously. Specialized seating (PagedAttention), continuous show-starts (continuous batching), industrial efficiency. Annoying for one person who just wants to flip channels.

Use the right tool for the job.

## The mechanics

### vLLM's key innovations

**1. PagedAttention — efficient KV cache memory**

KV cache memory grows and shrinks dynamically with each request's length. Naive contiguous allocation wastes memory due to fragmentation (you allocate for the worst-case-length, then most requests are shorter). PagedAttention treats KV cache like operating-system virtual memory:

- Memory is divided into fixed-size **blocks** (e.g., 16 tokens per block).
- Each request gets blocks as it grows.
- Blocks are non-contiguous in physical memory; vLLM maintains a per-request block table.
- Result: "near-zero waste in KV cache memory."
- Bonus: blocks can be **shared** across requests with common prefixes — e.g., many requests sharing the same system prompt. Prefix caching.

Paper: Kwon et al., "Efficient Memory Management for Large Language Model Serving with PagedAttention" (SOSP 2023).

**2. Continuous batching — throughput from request-level concurrency**

Naive batching ("static" batching): wait for N requests, run them together, return all when slowest finishes. Wasteful — short requests are forced to wait for long ones.

Continuous batching (introduced by Orca, OSDI 2022): at every *iteration* (every token generation step), the scheduler can:
- Add new requests to the batch as slots open up.
- Remove completed requests from the batch.
- Run all currently-active requests in one fused forward pass through the model.

Effect: GPU is kept busy at near-peak utilization. Throughput improvements vs static batching are reported as **2x** (continuous batching alone) and **23x** (combined with PagedAttention) by vLLM/Anyscale benchmarks on naive serving baselines.

**3. OpenAI-compatible API**

vLLM exposes `/v1/chat/completions`, `/v1/completions`, `/v1/embeddings` matching the OpenAI spec. This means:

- The official `openai` Python SDK works unchanged. Set `base_url="http://localhost:8765/v1"`.
- Existing OpenAI-ecosystem tools (LangChain integrations, evaluation harnesses) work.
- Future migration to a different provider is one line of config.

This is the single biggest reason we chose vLLM for the agent's serving layer.

**4. Built-in features that matter for agents**

- Tool calling (function calling): supported, with structured `tool_calls` in responses.
- Streaming responses (`stream=True`): tokens arrive as they're generated.
- Logprobs: useful for confidence estimation in agent decisions.
- Speculative decoding, prefix caching, multi-LoRA serving: present, can be enabled if needed.

### Ollama's strengths

- **One-line model swap**: `ollama run llama4` and you're chatting in seconds. We use this for casual experimentation.
- **Multiple models loaded on demand**: keeps recently-used models in RAM, swaps as needed.
- **GGUF format**: portable, well-quantized, runs everywhere from a phone to a workstation.
- **No setup complexity**: single binary, no Python env, no CUDA toolkit needed.
- **Open WebUI integration**: the user already has this running on `:3001` (per server audit).

### Ollama's weaknesses (for our use case)

- **No continuous batching** in the way vLLM does. Multiple concurrent requests largely serialize through one worker.
- **No native OpenAI tool-calling API** until very recently (and ergonomics still inferior to vLLM in 2026).
- **Single-process serving** — can't easily scale across multiple GPUs the way vLLM does with `--tensor-parallel-size`.

### Under the hood

| Aspect            | vLLM                          | Ollama                            |
|-------------------|-------------------------------|-----------------------------------|
| Language          | Python + CUDA + Triton kernels | Go wrapper around llama.cpp (C/C++) |
| Inference engine  | Custom (PagedAttention)        | llama.cpp                         |
| Default model format | Safetensors (BF16/FP16/quant) | GGUF                              |
| Multi-GPU         | Tensor parallel native         | Limited                           |
| Batching          | Continuous, iteration-level    | One request at a time effectively |
| API               | OpenAI-compatible, full        | Ollama-native + partial OpenAI    |
| Best for          | Production serving, agents     | Local chat, prototyping           |

### Why we *chose vLLM* — articulated

1. **Concurrent agent steps**: our agent may issue parallel tool calls or run multiple agent loops simultaneously (e.g., one for planning, one for execution). vLLM batches them transparently.
2. **OpenAI SDK**: standard library, no custom client code. Big simplification of our codebase.
3. **Tensor parallelism**: 54 GB BF16 needs 2 GPUs cleanly; vLLM handles this.
4. **Production trajectory**: if this project grows beyond the course (or someone wants to reuse the agent), vLLM is the path. Ollama is a dev tool, not a deployment target.

### When Ollama is the right tool

- **Casual chat with the model** (no agent loop): use Open WebUI → Ollama. Already configured.
- **Comparing multiple models quickly**: `ollama pull` is easier than configuring vLLM for each.
- **Resource-constrained environments**: laptops, single 8 GB GPU. GGUF Q4 quants run everywhere.
- **Quick prototypes**: spinning up Ollama is faster than vLLM's first launch.

For the agent itself, vLLM. Don't conflate the two roles.

## Concrete numbers for our setup

- vLLM target port: **8765** (per `.env.example`). Other ports on this server (from audit): 8003 used by Open Deep Research, 3001 used by Open WebUI, 11434 used by system Ollama, 8080 used by something else. 8765 is free.
- vLLM start command (reference): see [09-tensor-parallelism.md](09-tensor-parallelism.md).
- Ollama already runs as a systemd service on 127.0.0.1:11434. Leave it alone (Rule from AGENTS.md / SERVER_STATE.md).
- The user also previously launched a second Ollama instance on port 11437 with a custom OLLAMA_MODELS dir (per shell history) — not running now. Don't reintroduce it.

### What our agent code calls

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8765/v1",
    api_key="not-needed",  # vLLM ignores this
)

response = client.chat.completions.create(
    model="Qwen/Qwen3.6-27B",
    messages=[...],
    tools=[...],
)
```

That's it. Same code would work against OpenAI's servers, Anthropic via a proxy, or any OpenAI-compatible endpoint. **This is the single biggest leverage point of choosing vLLM.**

## Likely questions from the professor

**Q: Why not use llama.cpp directly?**
A: llama.cpp is great as a library / binary but doesn't natively expose the OpenAI API at scale. Ollama wraps it; vLLM does not use llama.cpp at all (it's a parallel implementation with PagedAttention etc.). For our agent, vLLM's batching and OpenAI compatibility win.

**Q: What is the difference between continuous batching and dynamic batching?**
A: Continuous batching = iteration-level scheduling (a new request can join after every single token step). Dynamic batching (older term) usually meant "wait a few ms to fill a batch, then process." Continuous is finer-grained and strictly more efficient.

**Q: Does PagedAttention work for our hybrid Gated DeltaNet model?**
A: PagedAttention applies to the standard-attention layers (which have a KV cache). Linear-attention layers like Gated DeltaNet have a *constant-size* recurrent state instead of a KV cache — different memory management. vLLM handles both transparently; we don't need to do anything different.

**Q: Could we serve Qwen 3.6-27B with Ollama?**
A: Yes, the GGUF-quantized version (`qwen3.6:27b`, ~17 GB on disk) runs on Ollama and we have it installed. But the quality is lower (it's quantized to Q4/Q5), tool calling is more fragile, and batching is poor — wrong tradeoffs for an agent.

**Q: What happens when two agent loops hit the vLLM server simultaneously?**
A: vLLM batches them in the same forward pass when possible. PagedAttention isolates their KV caches. No interference. Throughput scales near-linearly until the GPU is saturated.

**Q: Is vLLM only for NVIDIA GPUs?**
A: It supports NVIDIA primarily, with growing AMD ROCm and TPU support. Our setup is NVIDIA so this is moot.

## Common misconceptions / gotchas

- **"vLLM and Ollama compete for the same job."** They overlap but optimize for different things. Best mental model: vLLM = production server; Ollama = dev tool.
- **"Continuous batching speeds up a single request."** No — it improves throughput when *many* requests are concurrent. A single request gets no speedup from batching (might get a tiny slowdown from scheduler overhead).
- **"Prefix caching is automatic in all serving frameworks."** Specifically a vLLM (and a few others') feature. Ollama doesn't do it by default. For an agent re-sending a long system prompt every turn, prefix caching saves a lot of compute.
- **"GGUF is a quantization method."** GGUF is a *file format* that *supports* quantization. The actual quantization happens during conversion (Q4_K_M, Q5_K_M, etc., are llama.cpp quantization recipes).
- **Previously confused with model formats**: vLLM loads safetensors (the HuggingFace standard format) directly. To use a GGUF model with vLLM, you'd need to convert or use a different path. Don't try to point vLLM at the Ollama models directory.

## Sources

- Kwon et al., "Efficient Memory Management for Large Language Model Serving with PagedAttention" (vLLM paper, SOSP 2023): https://arxiv.org/abs/2309.06180 (accessed 2026-05-17)
- Yu et al., "Orca: A Distributed Serving System for Transformer-Based Generative Models" (continuous batching, OSDI 2022): https://www.usenix.org/conference/osdi22/presentation/yu
- Anyscale blog, "How continuous batching enables 23x throughput..." (vLLM throughput benchmarks): https://www.anyscale.com/blog/continuous-batching-llm-inference (accessed 2026-05-17)
- vLLM docs (OpenAI-compatible server, supported features): https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html
- Ollama project (architecture, llama.cpp under the hood): https://github.com/ollama/ollama
- llama.cpp GGUF spec: https://github.com/ggerganov/llama.cpp/blob/master/docs/gguf.md
- Local server audit (port usage, existing Ollama systemd service): SERVER_STATE.md, 2026-05-17
