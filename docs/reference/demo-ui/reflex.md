# Reflex (cache)

Sources: https://reflex.dev/ ; https://github.com/reflex-dev/reflex ; https://reflex.dev/blog/top-python-web-frameworks/

## What it is

Pure-Python full-stack web framework. Backend = FastAPI, frontend = compiles to React, glue via WebSockets. >60 built-in components (Radix-style), Tailwind support, custom React component wrapping.

## State

```python
class State(rx.State):
    messages: list[dict] = []
    @rx.event(background=True)
    async def send(self, prompt):
        async with self:
            self.messages.append({"role": "user", "content": prompt})
        async for chunk in agent.stream(prompt):
            async with self:
                self.messages[-1]["content"] += chunk
```

Reactive — UI auto-updates when state changes.

## Pros for agent demo

- Real web app, real React under the hood — can match Chainlit polish if you spend the time.
- Built-in code block (`rx.code_block`) with syntax highlighting.
- Reflex Build (AI scaffolder) and Reflex Cloud (one-command deploy) launched 2025.

## Cons for a 10-15 min demo

- No out-of-box "agent step / tool-call card" component. You build it from primitives (`rx.accordion`, `rx.box`).
- LOC is high: a chat UI with streaming + collapsible tool-call cards is ~200-400 LOC.
- Two processes (backend + frontend dev server) — more demo-day surface area for things to break.
- The pain point ("OK in curl, broken in browser") applies — Reflex compiles to JS, so curl-testing the backend tells you nothing about the actual rendered UI.

## Verdict for this project

Powerful framework but overkill for a one-shot 10-15 min demo. Reserve for if the agent UI becomes a product.
