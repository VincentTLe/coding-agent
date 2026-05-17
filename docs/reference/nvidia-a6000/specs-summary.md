# NVIDIA RTX A6000 — Spec Summary

Source: NVIDIA official product page — https://www.nvidia.com/en-us/design-visualization/rtx-a6000/
Accessed: 2026-05-17

Independent confirmation: Leadtek product page (https://www.leadtek.com/eng/products/workstation_graphics(2)/NVIDIA_RTX_A6000(30893)/detail)

## Memory

- **48 GB GDDR6** with error-correcting code (ECC)
- Memory interface: 384-bit
- Memory bandwidth: **768 GB/s** (from Leadtek spec, not on NVIDIA's marketing page in the section we fetched)

## NVLink

- **3rd-generation NVIDIA NVLink**
- Per 2-card bridge: **up to 112 GB/s** aggregate GPU-to-GPU bandwidth
- 2-way only on A6000 (no 4-way option); 2-slot or 3-slot physical bridges
- Combined memory (NVLink pair): **96 GB** (logical, NOT a unified address space — still requires explicit cross-GPU operations like all-reduce via NCCL)

## Compute (from Leadtek)

- CUDA cores: 10,752
- Tensor cores: 336 (3rd gen — supports BF16, FP16, TF32, INT8; **no native FP8**)
- RT cores: 84 (2nd gen)
- Base clock: 1455 MHz
- Boost clock: 1860 MHz

## Architecture

- **Ampere** (GA102 die)
- Native data types: FP32, FP16, BF16, TF32, INT8, INT4
- No native FP8 (FP8 requires Hopper / Ada Lovelace tensor cores or newer)

## Our setup

- 2 cards installed
- NVLink topology reports **NV4** in `nvidia-smi topo -m` — a bonded set of 4 NVLinks between GPU 0 and GPU 1
- Aggregate VRAM: 96 GB (split across cards; access cross-card via NVLink during tensor-parallel all-reduce)

## Relevance

- Determines: "Does Qwen 3.6-27B fit?" → 54 GB BF16 weights, 96 GB combined → fits under TP=2.
- Determines: quantization choice — FP8 emulated only, so AWQ/GPTQ (INT4) would be preferred over FP8 if we ever needed to shrink.
- Determines: tensor parallelism viability — NVLink makes TP efficient; this hardware is well-suited.
