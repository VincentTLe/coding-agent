# Eval task sources & licenses

The evaluation suite under `eval/tasks/` combines third-party benchmark problems
(converted into this repo's task format) with original hand-authored tasks. Attribution
and licensing for each source:

## `eval/tasks/bench/he_*` — HumanEval+ (164 problems)
- **Problems:** HumanEval, by OpenAI — **MIT License**.
  <https://github.com/openai/human-eval>
- **Hardened tests ("+"):** EvalPlus — **Apache-2.0 License**.
  <https://github.com/evalplus/evalplus> · dataset: <https://huggingface.co/datasets/evalplus/humanevalplus>
- Each task reuses the EvalPlus `test` harness (the `check()` function with its augmented
  input/expected cases) verbatim; the stub is the original `prompt` signature + docstring.

## `eval/tasks/bench/mbpp_*` — MBPP, sanitized (427 problems)
- **Problems & tests:** Mostly Basic Python Problems (MBPP), by Google Research —
  **Creative Commons Attribution 4.0 (CC-BY-4.0)**.
  <https://github.com/google-research/google-research/tree/master/mbpp>
  Source file: `sanitized-mbpp.json`. Each task reuses the dataset's `test_list` asserts and
  derives the stub signature from the reference `code`.

## `eval/tasks/curated/*` — original tasks (authored for this repo)
- Hand-authored debugging, refactor, multi-file, DP, graph, data-structure, OOP, parsing,
  and algorithm/recursion tasks. **MIT License** (same as this project). Not derived from any
  external benchmark.

## Reference solutions — `eval/solutions/`
Reference implementations used only by the validation gate (`eval/validate_tasks.py`) to prove
each task is real (reference passes, stub fails). For benchmark tasks these are the upstream
canonical solutions and carry the upstream license above; for curated tasks they are MIT.

## Note
These benchmarks are widely known and partially saturated/contaminated for modern models;
treat the numbers here as a capability + harness sanity signal for a local open-weight model,
not a frontier leaderboard. See `eval/README.md` for scope and honest caveats.
