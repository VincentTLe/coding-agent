# syrupy

Source: https://github.com/syrupy-project/syrupy

- Zero-dep pytest snapshot plugin. Idiomatic syntax: `assert value == snapshot`.
- Fails the suite when snapshot is missing (not just on diff) - prevents silent gaps.
- Update with `pytest --snapshot-update`. Snapshots stored under `__snapshots__/` next to test.
- Default `AmberSnapshotExtension` produces `.ambr` files; `JSONSnapshotExtension` produces `.json` (good for LLM tool-call payloads / agent transcripts).

```python
from syrupy.extensions.json import JSONSnapshotExtension

@pytest.fixture
def snapshot_json(snapshot):
    return snapshot.with_defaults(extension_class=JSONSnapshotExtension)

def test_agent_trajectory(snapshot_json, fake_llm):
    out = run_agent("write hello", llm=fake_llm)
    assert out.trajectory == snapshot_json
```

Matchers/excludes handle volatile fields (timestamps, UUIDs):

```python
from syrupy.matchers import path_type
matcher = path_type({"created_at": (int,)}, replace_data=True)
assert payload == snapshot(matcher=matcher)
```

## vs pytest-insta

- pytest-insta (vberlier/pytest-insta) offers REPL-driven review and a `snapshot.json` fixture; smaller community.
- syrupy has wider adoption and active maintenance; default for LLM agent projects in 2026.
