# SkillOpt — reference cache (Rule B)

- **Paper:** *SkillOpt: Executive Strategy for Self-Evolving Agent Skills*
- **arXiv:** 2605.23904 (Microsoft, May 2026, cs.AI) — https://arxiv.org/abs/2605.23904
- **Code:** https://github.com/microsoft/SkillOpt — **MIT License**
- **Retrieved:** 2026-05-27
- **⚠️ Verify before citing on a slide:** this assistant's training cutoff predates this paper;
  open the arXiv + GitHub URLs in a browser to confirm it is real before presenting it.

## Cached files
- `README.md` — repo README.
- `src-evaluation-gate.py` — the validation gate (strict `>` accept/reject); our `skillopt/loop.py`
  gate mirrors this.
- `src-optimizer-skill.py` — edit ops + protected slow-update region; our `skillopt/skill.py` is a
  faithful port (attribution in the module docstring).

## What we ported (faithful core)
Skill doc + 4 edit ops + protected slow-update region; contrastive reflect (failure/success channels,
failures bucketed by our `finish_reason`); failure-first merge; clip-to-L (textual learning rate);
strict-`>` validation gate; rejected-edit buffer; epoch slow-update.
**Deferred (decorative per the paper's ablations):** optimizer meta-skill, parallel hierarchical
merge, autonomous-LR, cosine schedule, rewrite mode.

## Grounding prior art (real, arXiv-verified)
Voyager 2305.16291 · TextGrad 2406.07496 · GEPA 2507.19457 · OPRO 2309.03409 · ExpeL 2308.10144 · Reflexion 2303.11366
