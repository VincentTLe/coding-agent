# Examples

One concept per file. Each file runs standalone. Read top-to-bottom in numerical order. Each file is heavily commented because the owner needs to understand every line.

Planned order (files written by the owner, not by AI assistants):

1. `01_chat.py` — basic LLM call, multi-turn chat, demonstrates stateless API
2. `02_tool_use.py` — first tool call, JSON schema, parsing model output
3. `03_file_tool.py` — read_file as a real tool
4. `04_bash_tool.py` — shell execution with timeout
5. `05_agent_loop.py` — the core while-loop tying everything together
