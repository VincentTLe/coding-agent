# WebArena, SWE-Lancer, AgentBench, AgentBoard — reference

## WebArena
Source: web-arena-x/webarena (https://github.com/web-arena-x/webarena), webarena.dev

### What
812 tasks across 4 self-hosted sites: e-commerce (Magento), social (Reddit clone), code (Gitlab), CMS (Wordpress). Programmatic grading. Long-horizon multi-step browser tasks.

### Setup
- Self-host: AWS t3a.xlarge + 1000 GB EBS recommended.
- Docker images per site (one image per site, self-contained).
- All available on Docker Hub (https://hub.docker.com/u/webarena/).
- Homepage on :4399; sites on dedicated ports.

### Cost / hardware
- One t3a.xlarge + 1 TB EBS for hosting = ~$5-10/day on AWS, or run on a beefy local box (the 1 TB is the constraint).
- Eval loop: agent calls a headless browser (Playwright) → tokens cost only.

### Leaderboard (May 2026)
- Claude Mythos Preview = 68.7%; OpAgent = 71.6% (SOTA Jan 2026); DeepSeek v3.2 = 74%.
- Human baseline = 78%.
- Up from 14% at launch (2 years ago).

### Realistic vs synthetic
Hybrid — real software stacks (Gitlab, Wordpress, Magento) but seeded fixed-state databases, not live sites. Good middle ground.

---

## SWE-Lancer
Source: openai/SWELancer-Benchmark (https://github.com/openai/SWELancer-Benchmark), OpenAI blog (https://openai.com/index/swe-lancer/)

### What
Real Upwork freelance SWE tasks, $50 bug fix to $32K feature. Two task types: (1) Independent Coder (end-to-end tests, triple-verified), (2) SWE Manager (pick between proposals). Built around Expensify codebase.

### Setup
- Docker required. Heavy image (full Expensify-style stack).
- pip install + provider keys; agent gets a repo + task description.

### Cost / hardware
- Docker images large. Full benchmark needs significant disk + per-task container spin-up.
- Per-task token cost is high (long context).

### Leaderboard
- GPT-5.1 Codex = 0.663 (top of 4 self-reported entries).
- Mean across reported = 0.386.
- No verified open-weight entries.

### Realistic vs synthetic
Maximally realistic — real freelance jobs. But: tight to Expensify codebase, so generalization unclear.

### Critical
Very high per-task cost; small sample of evaluated models. Not a quick win for a 2-week demo.

---

## AgentBench
Source: THUDM/AgentBench (https://github.com/THUDM/AgentBench), paper (https://arxiv.org/abs/2308.03688) ICLR 2024

### What
8 environments: OS shell, DB SQL, Knowledge Graph, Digital Card Game, Lateral Thinking Puzzles, House-Holding (ALFWorld), Web Shopping (WebShop), Web Browsing (Mind2Web). Single overall score.

### Setup
- Docker recommended. Different sub-tasks need different deps.
- Provider-agnostic; vLLM works.

### Cost
- Moderate. Lighter than OSWorld. Free except API tokens.

### Realistic vs synthetic
Mostly synthetic — most environments are toy or simulated. Card game, puzzles dilute the signal. Less load-bearing in 2026.

---

## AgentBoard
Source: hkust-nlp/AgentBoard (https://github.com/hkust-nlp/AgentBoard), NeurIPS 2024 Oral

### What
9 multi-turn tasks + 1013 environments. Embodied AI, game, web, tool. Headline metric = **progress rate** (per-step subgoal advancement, not just success).

### Setup
- conda env Python 3.8.13 + git clone + HF data + setup script.
- ~30-min quick start (their claim).
- Docker option also available.
- WandB-integrated analytics.

### Cost
- Low. Token-only.

### Realistic vs synthetic
Synthetic environments but the **progress rate** metric is the unique value — gives partial-credit signal, useful for diagnosing weak loop early.
