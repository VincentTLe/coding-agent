"""
skillopt — a minimal, faithful implementation of SkillOpt's skill-optimization loop.

SkillOpt (Yang et al., Microsoft, arXiv 2605.23904; github.com/microsoft/SkillOpt, MIT)
treats a natural-language *skill document* as a trainable parameter and "trains" it via
an optimize→evaluate→keep/reject loop while the model weights stay frozen — i.e.
"gradient descent on a text document". This package ports the load-bearing core
(faithful to the paper's §3 method + the MIT repo), scaled to a single local Qwen3-14B
and our 627-task pytest eval harness. See docs/reference/skillopt/ and the project plan.

Modules:
  skill.py         — the skill document + edit ops + protected slow-update region (the parameter)
  splits.py        — deterministic stratified train/val/test split (the dataset)
  optimizer_llm.py — reflect / merge / clip via the optimizer LLM (the textual gradient)
  loop.py          — the step + epoch loop with the validation gate (the optimizer)
  report.py        — honest A/B analysis (pass@1, Wilson CI, McNemar, train-test gap)
"""
