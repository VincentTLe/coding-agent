# Cache: Epoch AI — "Run SWE-bench Verified in one hour on one machine"

Source: https://epoch.ai/blog/swebench-docker
Fetched: 2026-05-18

## Headline numbers

- Full SWE-bench Verified (500 tasks) eval ran in **62–73 minutes** on a single machine.
  - Gemini 2.0 Flash: 62 min
  - GPT-4o: 70 min
  - Claude 3.5 Sonnet: 63 min
- ~8 s wall-clock per sample (with parallel workers; eval is the patch-apply + pytest step, not inference).

## Hardware used

- GitHub Actions standard runner equivalent.
- 32 CPU cores, 128 GB RAM, x86_64.
- **No GPU** — the harness step is CPU + disk + Docker. GPU only matters for the *inference* step that produces the patches.

## Disk

- Original (vanilla) SWE-bench Verified images: **189 GB**.
- Epoch's optimized image set: **30 GB** for all 500 Verified images (~6× smaller via layer dedup).
- Optimized registry hosted at `ghcr.io/epoch-ai/swebench-images` (auth required).

## Known issue surfaced

`PIP_NO_CACHE_DIR=1` crashes on pre-19.0 pip versions used by some legacy Python repos in the dataset. Counter-intuitive fix: set `PIP_NO_CACHE_DIR=0` for legacy envs.

## Cost note

API run: ~100–150 M tokens per full Verified pass (cache-heavy).
