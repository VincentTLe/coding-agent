# pytest-recording + VCR.py (cached reference)

Sources:
- https://github.com/kiwicom/pytest-recording
- https://vcrpy.readthedocs.io/
- https://til.simonwillison.net/pytest/pytest-recording-vcr
- https://anaynayak.medium.com/eliminating-flaky-tests-using-vcr-tests-for-llms-a3feabf90bc5

- `pytest-recording` is a pytest plugin powered by VCR.py.
- Latest pytest-recording release: 0.13.4 (May 8, 2025). VCR.py latest: 8.0.0. [UNVERIFIED — confirm on PyPI/Read-the-Docs.]
- Records HTTP interactions to YAML cassettes; replays them on subsequent runs so no live HTTP is made.
- Default record mode is `none` (block accidental network). Useful modes: `once`, `new_episodes`, `all`, `rewrite`.
- Decorators: `@pytest.mark.vcr`, `@pytest.mark.default_cassette("name.yaml")`, `@pytest.mark.block_network`.
- Sensitive-header filtering via `vcr_config` fixture (`filter_headers=["authorization"]`, `filter_query_parameters=["api_key"]`).

LLM-specific usage notes:
- Cassette captures the HTTP call to the LLM provider, so the test sees the same bytes-for-bytes response every replay — perfect for unit/regression coverage of agent control flow.
- Record once against the real API with a real key; commit the cassette; CI replays for free and offline.
- Match on request body (POST messages) so cassettes are keyed on the prompt; a prompt change triggers a cassette miss, surfacing prompt drift.
- For streaming SSE / chunked transfer, VCR.py 8.x supports recording the chunk stream; verify the chosen client (openai, anthropic, httpx) plays back cleanly.
- Pair with a low-cost evaluation test that *does* hit the live model on a small schedule, so cassettes don't mask upstream model changes silently.
