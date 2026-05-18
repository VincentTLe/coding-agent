# Tavily Search API - Pricing Reference

Source: https://www.tavily.com/pricing (fetched 2026-05-18)

## Plans

- **Researcher (Free)** - 1,000 API credits/month, no credit card required, email support.
- **Pay As You Go** - $0.008 per credit, flexible usage.
- **Project** - Monthly subscription with 4,000+ API credits/month, higher rate limits.
- **Enterprise** - Custom pricing, custom rate limits, SLAs.

## Notable

- Tavily offers complimentary access for students (per pricing page note).
- Pricing is metered in "API credits"; basic search = 1 credit, advanced search = more.
- Built specifically for AI agents - returns ranked, relevance-filtered snippets with optional answer-synthesis layer.

## Independent benchmarks (2026)

- Exa scores 81% vs Tavily 71% on complex retrieval (per Exa's published vs page).
- Tavily p95 latency 3.8-4.5s (per AIMultiple agentic-search benchmark).
- Tavily preferred for "agent-shaped" queries; cleaner JSON shape with `answer`, `results[]`.
