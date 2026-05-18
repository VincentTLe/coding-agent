# NIAH, InfiniteBench, LooGLE, ZeroSCROLLS — Reference Notes

## NIAH (Needle-in-a-Haystack)
Greg Kamradt's original test (gkamradt/LLMTest_NeedleInAHaystack). Single
"needle" sentence inserted at varying depths/lengths; model retrieves it.

**Status, 2026:** saturated at 200K for every frontier model. No longer a
robust indicator. Production workloads are multi-needle; single-needle
overstates true capability by 15–40 points (digitalapplied.com).

**Variants in use:** RULER NIAH (multi-key, multi-value, multi-query),
Sequential-NIAH (arXiv 2504.04713), NoLiMa (associative, not literal match),
U-NIAH, MRCR v2 (multi-round, Anthropic).

## InfiniteBench / ∞Bench
**Source:** OpenBMB/InfiniteBench, arXiv 2402.13718 (ACL 2024).

First benchmark with avg sample > 100K tokens. 12 tasks, 5 domains
(retrieval, code, math, novels, dialog). EN/ZH. Notable tasks:
- Retrieve.KV — key→value lookup in large JSON
- En.MC — multiple-choice over a novel
- Math.Find — pick one of seven key numbers from an array

Used as a HELM Long Context component (En.MC, En.Sum) — GPT-4.1 leads.

## LooGLE
**Source:** bigai-nlco/LooGLE, ACL 2024 (arXiv 2311.04939). LooGLE v2 at
arXiv 2510.22548 (Oct 2025).

Avg 24K tokens per doc, post-2022 docs, 6K newly-generated QA pairs.
Short-dependency tasks (cloze, short QA) are easy; long-dependency tasks
(across the full doc) are where models struggle.

LooGLE v2 (2025): 16K → 2M, 10 domain-specific long-dependency tasks
(law, finance, game, code). Best model 59.2% overall.

## ZeroSCROLLS
**Source:** arXiv 2305.14196 (Findings of EMNLP 2023).

Zero-shot only, test + small validation, no training data. 6 tasks from
SCROLLS plus 4 new ones, including aggregation tasks (SpaceDigest,
BookSumSort) that require contextualizing across whole inputs. Still used
as a "naturally long" zero-shot bar; older than RULER/InfiniteBench so
many models saturate the easier sub-tasks. Live leaderboard.

## Bottom line on benchmark choice (May 2026)
- **For pure retrieval at depth** → RULER (NIAH + multi-key) at 32K, 64K, 128K.
- **For real reasoning at depth** → LongBench v2, LooGLE v2.
- **For 100K+ end-to-end** → InfiniteBench (En.MC, Retrieve.KV).
- **For NIAH stress** → Sequential-NIAH or NoLiMa, not vanilla NIAH.
- **HELM Long Context** (Stanford CRFM) is the closest thing to a fair
  cross-benchmark composite as of late 2025.
