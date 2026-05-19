#!/usr/bin/env bash
# Start vLLM with Qwen3-14B on a single GPU (GPU1).
# Output is teed to /tmp/vllm.log.
#
# To stop:  Ctrl-C in this tmux pane.
# To monitor from another shell:  tail -f /tmp/vllm.log

set -euo pipefail

# flashinfer JIT needs nvcc which is not available system-wide on this server.
# Force PyTorch-native sampler instead.
export VLLM_USE_FLASHINFER_SAMPLER=0

# Pin to GPU1 (GPU0 left for other lab users).
export CUDA_VISIBLE_DEVICES=1

cd "$HOME/code/coding-agent"
source .venv/bin/activate

exec vllm serve "$HOME/models/Qwen3-14B" \
    --served-model-name Qwen/Qwen3-14B \
    --tensor-parallel-size 1 \
    --max-model-len 32768 \
    --gpu-memory-utilization 0.80 \
    --reasoning-parser qwen3 \
    --enable-auto-tool-choice \
    --tool-call-parser hermes \
    --port 8765 \
    2>&1 | tee /tmp/vllm.log
