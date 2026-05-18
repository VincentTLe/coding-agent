# pytest-recording (VCR cassettes)

Source: https://pypi.org/project/pytest-recording/ ; https://vcrpy.readthedocs.io/en/latest/

- Plugin wrapping VCR.py for pytest. Latest 0.13.4 (May 8 2025). Python 3.9+. [UNVERIFIED for newer 2026 releases.]
- Use `@pytest.mark.vcr` to record/replay HTTP traffic into YAML cassettes.
- Optional `@pytest.mark.default_cassette("name.yaml")` and `@pytest.mark.block_network`.
- Modes via `--record-mode`: `none` (default, replay-only), `once`, `all`, `new_episodes`, `rewrite`.
- Filter secrets:

```python
@pytest.fixture(scope="module")
def vcr_config():
    return {
        "filter_headers": ["authorization", "api-key"],
        "filter_query_parameters": ["api_key"],
    }
```

Notes for LLM testing:

- Records httpx (via vcrpy stubs) so `openai` v2 SDK requests are captured.
- Recommended for E2E smoke tests that hit vLLM once, then replay deterministically in CI.
- Cassettes can become brittle if request bodies (timestamps, IDs) drift; use VCR `match_on` config to relax matching.
