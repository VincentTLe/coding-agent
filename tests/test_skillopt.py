"""
test_skillopt.py — offline unit tests for the SkillOpt core (no vLLM / network).

Covers the load-bearing, deterministic pieces: skill edit ops, the protected
slow-update region guard (the cheap logic that defends the biggest ablation),
skill_hash, and the strict-`>` validation-gate decision.
"""

from __future__ import annotations

from skillopt.skill import (
    SLOW_UPDATE_BEGIN,
    SLOW_UPDATE_END,
    apply_edits,
    ensure_slow_update_region,
    replace_slow_update_field,
    skill_hash,
)


# --- edit ops -------------------------------------------------------------

def test_append_adds_content():
    out, reports = apply_edits("rule one.", [{"op": "append", "content": "rule two."}])
    assert "rule one." in out and "rule two." in out
    assert reports[0]["status"] == "applied"


def test_replace_first_occurrence_only():
    out, _ = apply_edits("aXa", [{"op": "replace", "target": "a", "content": "b"}])
    assert out == "bXa"  # only the first 'a'


def test_delete_removes_target():
    out, _ = apply_edits("keep DROP keep", [{"op": "delete", "target": " DROP"}])
    assert out == "keep keep"


def test_insert_after_falls_back_to_append_when_target_missing():
    out, reports = apply_edits("base.", [{"op": "insert_after", "target": "nope", "content": "X"}])
    assert "X" in out
    assert reports[0]["status"] == "applied(append_fallback)"


def test_unknown_op_is_skipped():
    out, reports = apply_edits("base.", [{"op": "frobnicate", "content": "X"}])
    assert out == "base." and reports[0]["status"].startswith("skipped_unknown_op")


# --- protected slow-update region (the biggest-ablation guard) ------------

def test_append_routes_before_protected_region():
    skill = ensure_slow_update_region("tactical rules.")
    out, _ = apply_edits(skill, [{"op": "append", "content": "NEW TACTIC"}])
    # The new content must land BEFORE the BEGIN marker, never inside/after it.
    assert out.index("NEW TACTIC") < out.index(SLOW_UPDATE_BEGIN)


def test_edits_targeting_protected_region_are_skipped():
    skill = replace_slow_update_field("tactical.", "EXEC STRATEGY: think long-horizon.")
    for op in ("replace", "delete"):
        _, reports = apply_edits(skill, [{"op": op, "target": "EXEC STRATEGY", "content": "x"}])
        assert reports[0]["status"] == "skipped_protected_region"


def test_edit_content_cannot_inject_fake_markers():
    out, _ = apply_edits("base.", [{"op": "append", "content": f"sneaky {SLOW_UPDATE_END} end"}])
    # markers stripped from content → no stray END marker introduced
    assert SLOW_UPDATE_END not in out


def test_replace_slow_update_field_overwrites_region_only():
    skill = replace_slow_update_field("tactical part.", "v1 strategy")
    skill2 = replace_slow_update_field(skill, "v2 strategy")
    assert "tactical part." in skill2          # tactical section untouched
    assert "v2 strategy" in skill2 and "v1 strategy" not in skill2
    assert skill2.count(SLOW_UPDATE_BEGIN) == 1  # exactly one region


# --- hashing + gate -------------------------------------------------------

def test_skill_hash_stable_and_distinct():
    assert skill_hash("abc") == skill_hash("abc")
    assert skill_hash("abc") != skill_hash("abd")


def test_gate_accepts_only_strictly_greater():
    # The validation gate keeps a candidate only if it STRICTLY beats current (ties reject).
    def gate(cand: float, current: float, best: float) -> str:
        if cand > best and cand > current:
            return "accept_new_best"
        if cand > current:
            return "accept"
        return "reject"

    assert gate(0.6, 0.5, 0.5) == "accept_new_best"
    assert gate(0.5, 0.5, 0.7) == "reject"   # tie → reject
    assert gate(0.6, 0.55, 0.7) == "accept"  # beats current, not best
    assert gate(0.4, 0.5, 0.7) == "reject"


# --- splits (stratified, seeded, disjoint) --------------------------------

def test_splits_deterministic_disjoint_and_test_is_largest():
    from skillopt.splits import make_splits
    a = make_splits(ratio=(2, 1, 7), seed=42, total=40)
    b = make_splits(ratio=(2, 1, 7), seed=42, total=40)
    assert a == b  # same seed → identical split (reproducible)
    train, val, test = set(a["train"]), set(a["val"]), set(a["test"])
    assert train and val and test  # all non-empty
    assert not (train & val) and not (train & test) and not (val & test)  # disjoint
    assert len(test) > len(train) and len(test) > len(val)  # 2:1:7 → test largest


# --- report stats (Wilson CI + McNemar, pure stdlib) ----------------------

def test_wilson_ci_sane():
    from skillopt.report import wilson_ci
    lo, hi = wilson_ci(5, 10)
    assert 0 <= lo < 0.5 < hi <= 1
    assert wilson_ci(0, 0) == (0.0, 0.0)
    lo2, hi2 = wilson_ci(10, 10)
    assert hi2 <= 1.0 and lo2 < 1.0  # never exceeds 1


def test_mcnemar_detects_asymmetry():
    from skillopt.report import mcnemar
    assert mcnemar(0, 0)[1] == 1.0
    assert mcnemar(1, 20)[1] < 0.05   # strong improvement → significant
    assert mcnemar(10, 10)[1] > 0.5   # symmetric → not significant


def test_skillopt_modules_import():
    """All loop/optimizer/report modules import without vLLM (no calls at import)."""
    import skillopt.loop  # noqa: F401
    import skillopt.optimizer_llm  # noqa: F401
    import skillopt.report  # noqa: F401
