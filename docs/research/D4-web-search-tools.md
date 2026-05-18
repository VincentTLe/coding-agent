# D4 — Web Search APIs for AI Agents (2026)

## TL;DR

For a budget-sensitive student, **Tavily's free Researcher plan (1,000 credits/month, no credit card)** is the cheapest reasonable hosted option and is agent-native. For zero ongoing cost or higher volume, **self-host SearXNG in Docker** - free, AGPL, clean JSON. Bing Search API is dead (retired 2025-08-11). Brave killed its no-card free tier in Feb 2026.

## Why

A `web_search` tool lets the agent resolve "how do I X in library Y v1.2?" without baking docs into the prompt. Coding queries are keyword-shaped (error messages, function names, versions), so freshness and snippet quality matter more than semantic recall. Cost matters because one agent loop can fire 3-10 searches.

## State of the art (May 2026)

- **Bing Search API retired** Aug 2025; Microsoft pushes "Grounding with Bing" inside Azure AI Foundry, not a drop-in. [1]
- **Brave** removed its free no-card tier in Feb 2026; $5/mo prepaid credit (~1k req), card required, no spending cap. [2]
- **Tavily and Exa** are the agent-native leaders. Exa wins on semantic retrieval (81% vs 71%) and speed (p95 1.4-1.7s vs 3.8-4.5s); Tavily wins on agent ergonomics and free-tier generosity. [3][4]
- **Serper** is cheapest raw-Google SERP: $0.30-$1/1k, 2,500 free credits, no card. [5]
- **SearXNG** has matured into the default self-hosted option, with built-in LangChain/LiteLLM/n8n wrappers. [6]

## Most-used in 2026

Tavily and Exa dominate hosted agent stacks; SearXNG dominates self-hosted; Serper is the budget keyword fallback; Perplexity Sonar is used when you want synthesized answers + citations instead of raw results.

## Comparison

| Provider | Free tier | Paid rate | Latency p95 | JSON shape | Best for |
|---|---|---|---|---|---|
| **Tavily** | 1,000 credits/mo, no card [7] | $0.008/credit | 3.8-4.5s [3] | `{answer, results[{title,url,content,score}]}` | Agent-first, answer synthesis |
| **Exa** | 1,000 req/mo [8] | $7/1k | 1.4-1.7s [3] | results + page contents inline | Semantic retrieval, fast |
| **Serper** | 2,500 credits, no card [5] | $0.083-$1/1k | ~1-2s | Raw Google SERP JSON | Cheapest keyword search at scale |
| **Brave** | $5/mo credit (~1k), card required [2] | $5/1k | n/a | LLM-optimized snippets | Independent index |
| **Perplexity Sonar** | Pro subs: $5/mo credit | Search API $5/1k [9] | n/a | Answer + citations | Synthesized answers |
| **You.com** | $100 credit | $5/1k (Mar 2026 cut) [10] | n/a | Web + Contents | Research workflows |
| **DuckDuckGo** | Free, no key [11] | Free | Variable | HTML-scraped, libs normalize | Zero-cost dev, can break |
| **SearXNG (self-host)** | Unlimited, free [6] | $0 | LAN + upstream | `format=json` clean | Zero cost, privacy, control |
| **Bing** | RETIRED [1] | n/a | n/a | n/a | Migrate off |

[UNVERIFIED] Tavily Researcher tier publishes no daily/RPM rate limit. Latency figures are from a third-party AIMultiple benchmark, not Tavily's SLA. Exa's $1,000 startup/education credit eligibility for individual students is unclear from the public page.

## Recommendation

**Primary: SearXNG self-hosted in Docker.** Zero ongoing cost, fits the from-scratch ethos, returns clean JSON that maps trivially to the agent's tool schema, no API key to leak. One `docker run searxng/searxng` next to the agent gives a `/search?q=...&format=json` endpoint. Aggregates Google/DDG/Brave - plenty for coding queries.

**Secondary fallback: Tavily Researcher (free).** Drop-in if SearXNG returns thin results or breaks. 1,000 credits/month with no card is the most generous agent-native free tier in 2026; the JSON shape with synthesized `answer` can save a follow-up LLM call.

**Skip:** Brave (no longer free without a card), Bing (retired), Perplexity Sonar (overkill - you have your own LLM), You.com (no edge for coding), Exa (excellent but free tier matches Tavily with smaller benefit for keyword-shaped queries).

## Next steps

1. Add a `web_search` tool with swappable backend via `WEB_SEARCH_BACKEND=searxng|tavily`.
2. Stand up SearXNG locally (Docker, enable JSON output in `settings.yml`).
3. Wire Tavily as fallback; key in `.env`, never commit.
4. Cap calls per agent loop (e.g. 5) to protect both backends.
5. Cache by `(query, top_k)` per session - coding queries repeat.

## Open questions

- Does SearXNG localhost get rate-limited by upstream Google/Bing under heavy agent load? (Likely - need backoff and engine rotation.)
- Per-second rate limit on Tavily's free tier - undocumented.
- Empirical coding-quality delta between SearXNG-via-Google and Serper-via-Google? Worth a small eval once wired in.

## Sources

1. https://learn.microsoft.com/en-us/lifecycle/announcements/bing-search-api-retirement
2. https://api-dashboard.search.brave.com/documentation/pricing
3. https://aimultiple.com/agentic-search
4. https://exa.ai/versus/tavily
5. https://serper.dev/
6. https://docs.langchain.com/oss/python/integrations/providers/searx
7. https://www.tavily.com/pricing
8. https://exa.ai/pricing
9. https://docs.perplexity.ai/docs/getting-started/pricing
10. https://you.com/resources/lower-search-api-cost
11. https://github.com/topics/duckduckgo-api
12. https://docs.searxng.org/dev/search_api.html
