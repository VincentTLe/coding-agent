---
name: start-vllm
description: Start the local vLLM server (Qwen3-14B on GPU1, port 8765) for the coding-agent project, wait for startup to complete, and verify the endpoint is live. Use when the user wants to bring the model server up before running the agent or the demo.
disable-model-invocation: true
---

# Start the vLLM model server

This skill brings up the local model server the coding-agent talks to:
**Qwen3-14B (BF16) served by vLLM on GPU1, OpenAI-compatible API on port 8765**.
It uses the exact command and flags from `scripts/start_vllm.sh` — do not invent
or change flags. The server is run on demand (not always-on) and lives in a tmux
pane on this shared GPU box.

## Step 1 — Check if it is already up

Before starting anything, check whether a server is already answering on port 8765:

```bash
curl -sf http://localhost:8765/v1/models
```

- If this prints JSON containing `"Qwen/Qwen3-14B"`, the server is **already running** —
  STOP here and tell the user it is ready. Do not start a second instance (GPU1 only
  has room for one Qwen3-14B at `--gpu-memory-utilization 0.75`).
- If it errors / connection refused, continue to Step 2.

## Step 2 — Start the server (background, log to /tmp/vllm.log)

Run the project's launcher script. It already does everything: forces the
PyTorch-native sampler (`VLLM_USE_FLASHINFER_SAMPLER=0`), pins to GPU1
(`CUDA_VISIBLE_DEVICES=1`), activates `.venv`, and `tee`s output to `/tmp/vllm.log`.

Start it **in the background** so it keeps running across turns (it is a
long-lived server, not a one-shot command):

```bash
bash scripts/start_vllm.sh
```

The effective command the script runs (for reference — run the script, do not
retype this):

```
vllm serve "$HOME/models/Qwen3-14B" \
    --served-model-name Qwen/Qwen3-14B \
    --tensor-parallel-size 1 \
    --max-model-len 32768 \
    --gpu-memory-utilization 0.75 \
    --reasoning-parser qwen3 \
    --enable-auto-tool-choice \
    --tool-call-parser hermes \
    --port 8765
```

## Step 3 — Wait for "Application startup complete"

Loading Qwen3-14B in BF16 (~28 GB) takes a while (often 1–3 minutes). Poll the
log until you see the readiness line, instead of guessing:

```bash
until grep -q "Application startup complete" /tmp/vllm.log; do sleep 5; done
echo "vLLM startup complete"
```

If instead the log shows a traceback, `CUDA out of memory`, or
`Address already in use`, STOP and report the failure to the user — do not retry
blindly (it may be another user's process on the GPU, or an instance already up).

## Step 4 — Verify the endpoint serves the model

Confirm the OpenAI-compatible endpoint is actually answering and the right model
is registered:

```bash
curl -sf http://localhost:8765/v1/models
```

This must return JSON listing `Qwen/Qwen3-14B`. If it does, report success:
the server is up on `http://localhost:8765/v1` and the agent / demo can now run.

## Notes

- To watch the log live in another shell: `tail -f /tmp/vllm.log`.
- To stop the server: `Ctrl-C` in its tmux pane (or kill the background process).
- The endpoint config lives in `.env` (`VLLM_BASE_URL`, `VLLM_MODEL_NAME`); the
  port can change there — if so, read `.env` and adjust the URL in Steps 1 and 4.
