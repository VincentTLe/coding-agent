# SearXNG - Self-Hosted Metasearch Reference

Sources:
- https://docs.searxng.org/ (2026.5.17 build)
- https://docs.searxng.org/dev/search_api.html
- https://docs.langchain.com/oss/python/integrations/providers/searx

## What it is

Free, open-source metasearch engine that aggregates results from up to 244 search services (Google, Bing, DuckDuckGo, Brave, GitHub, Wikipedia, etc.) without tracking or profiling users. AGPL-licensed community fork of Searx.

## JSON API

Endpoint: `GET /search?q=<query>&format=json`

JSON output is NOT enabled by default - must be activated in `settings.yml` under `search.formats`. Returns array of results with `title`, `url`, `content`, `engine` per result, plus `infoboxes`, `suggestions`, `corrections`.

## Hosting

- Docker (`searxng/searxng:latest`) is the canonical install path.
- Runs comfortably in ~256-512 MB RAM. Single-core CPU adequate for personal use.
- Can run on the same machine as the coding agent (localhost:8888) - zero external cost.

## AI Agent Integration

LangChain has first-class wrapper:
```python
from langchain_community.utilities import SearxSearchWrapper
s = SearxSearchWrapper(searx_host="http://localhost:8888")
s.run("what is a large language model?")
```

Also supported by LiteLLM, n8n, Flowise out of the box.

## Caveats

- No SLA, no rate-limit shield. Upstream engines (Google, Bing) may rate-limit your IP if a single agent floods queries.
- Some engines require API keys to enable (e.g. Bing has been removed entirely as of 2025).
- Result quality is roughly Google/Bing/DDG aggregate - not "agent-tuned" the way Tavily/Exa are. Snippets are short.
