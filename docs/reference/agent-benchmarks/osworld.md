# OSWorld reference

Source: xlang-ai/OSWorld (https://github.com/xlang-ai/OSWorld), OSWorld-Verified (https://xlang.ai/blog/osworld-verified), paper (NeurIPS 2024)

## What it tests
369 real computer tasks in actual VMs: Ubuntu desktop, browser, GIMP, LibreOffice, VSCode. Agent acts via screenshots + mouse/keyboard. Open-ended, multi-app workflows. Programmatic grading by checking final file/system state.

## Setup
- QEMU/KVM (Linux) OR VMware (macOS) OR Docker OR AWS.
- Each VM: ~24 GB disk, dedicated CPU+RAM, display stack.
- OSWorld-Verified moved infra to AWS for 50× parallelization.
- OSGym (Apr 2026): manages 1000+ replicas at $0.23/replica/day.

## Cost / hardware
- API-based agents: $60-80/run.
- 3 runs/week: $180-240 API or ~$1,785 self-hosted H200 spot.
- Local: a single A6000 box CANNOT run 369 VMs in parallel — need to serialize or use spot cloud VMs.
- Eval time on cloud parallel: ~1 hour. Serial on one box: days.

## Leaderboard (May 2026)
- OSWorld-Verified: Claude Mythos Preview = 79.6%, GPT-5.5 = 78.7%, Claude Opus 4.7 = 78.0%.
- Original OSWorld: Claude Opus 4.6 = 72.7%, Claude Sonnet 4.6 = 72.5%, Qwen3-VL-235B = 66.7%.
- Berkeley RDI study (2026): 8 agent benchmarks including OSWorld exploitable to near-perfect without solving tasks — be careful citing scores.

## Realistic vs synthetic
Maximally realistic — actual desktop OS, actual apps. Bash-only or text-only agents cannot play; needs vision-language model + GUI grounding.

## Critical for our project
NOT a fit. Qwen 3.6-27B is text-only via vLLM. OSWorld requires multimodal screen grounding. Would need Qwen3-VL or external vision pipeline + heavy VM infra. Skip.
