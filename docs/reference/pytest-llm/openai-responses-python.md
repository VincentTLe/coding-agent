# openai-responses-python

Source: https://github.com/mharrisb1/openai-responses-python ; https://pypi.org/project/openai-responses/

- Pytest plugin built on top of RESPX (httpx mock router).
- Auto-mocks OpenAI requests via decorator: `@openai_responses.mock()` on a test function.
- Supports Chat, Embeddings, Models, Moderations, Files, Assistants/Threads/Messages/Runs, Vector Stores.
- Streaming responses supported since v0.4.
- Compatible with `openai` Python SDK v2.0+.
- Status: maintenance mode (per README, May 2025). Community contributions encouraged; risk of deprecation if maintenance > 2 hr/month. [UNVERIFIED whether status changed in 2026.]

Minimal usage (paraphrased from README):

```python
import openai_responses
from openai import OpenAI

@openai_responses.mock()
def test_create_assistant():
    client = OpenAI(api_key="sk-fake")
    asst = client.beta.assistants.create(model="gpt-4o", name="t")
    assert asst.name == "t"
```
