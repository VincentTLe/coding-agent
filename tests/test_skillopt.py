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


def test_boundary_spanning_target_is_skipped_not_destructive():
    """Regression for the pre-fix bug: a target that STARTS outside the protected region
    but EXTENDS INTO it must be rejected — old guard only checked start → could destroy
    the BEGIN marker and permanently corrupt the slow-update region."""
    skill = replace_slow_update_field("# rules\npreamble.\n", "EXECUTIVE STRATEGY: hi.")
    pre = skill.find("preamble.")
    post = skill.find(SLOW_UPDATE_END) + len(SLOW_UPDATE_END)
    target = skill[pre:post]   # spans from outside the region THROUGH the END marker
    for op in ("replace", "delete"):
        out, reports = apply_edits(skill, [{"op": op, "target": target, "content": "OWNED"}])
        # Either defense is acceptable — the SAFETY PROPERTY is what matters: no destruction.
        # (Strip-markers from target makes it not match → "skipped_target_not_found"; if a
        # marker-free target overlapped, the overlap guard would say "skipped_protected_region".)
        assert reports[0]["status"].startswith("skipped"), f"{op} not skipped: {reports[0]}"
        assert SLOW_UPDATE_BEGIN in out and SLOW_UPDATE_END in out, "markers destroyed!"
        assert "EXECUTIVE STRATEGY: hi." in out, "protected body destroyed!"


def test_overlap_guard_direct():
    """Direct test of the overlap-aware guard: a target without markers but whose first
    occurrence falls INSIDE the protected region body must be rejected."""
    skill = replace_slow_update_field("# rules\npreamble.\n", "EXEC STRATEGY: think long.")
    out, reports = apply_edits(skill, [{"op": "replace", "target": "EXEC STRATEGY", "content": "x"}])
    assert reports[0]["status"] == "skipped_protected_region"
    assert "EXEC STRATEGY" in out  # body untouched


def test_ensure_slow_update_region_normalizes_orphans():
    """ensure_slow_update_region must repair skills with only-BEGIN or only-END markers,
    yielding exactly one canonical region."""
    only_begin = f"some text\n{SLOW_UPDATE_BEGIN}\nbody but no END\n"
    fixed = ensure_slow_update_region(only_begin)
    assert fixed.count(SLOW_UPDATE_BEGIN) == 1 and fixed.count(SLOW_UPDATE_END) == 1
    assert fixed.find(SLOW_UPDATE_BEGIN) < fixed.find(SLOW_UPDATE_END)

    only_end = f"prefix\n{SLOW_UPDATE_END}\nmore\n"
    fixed2 = ensure_slow_update_region(only_end)
    assert fixed2.count(SLOW_UPDATE_BEGIN) == 1 and fixed2.count(SLOW_UPDATE_END) == 1
    assert fixed2.find(SLOW_UPDATE_BEGIN) < fixed2.find(SLOW_UPDATE_END)


def test_replace_slow_update_field_strips_injected_markers():
    """Regression (Codex design review HIGH): if the optimizer's slow-update prose contains a
    stray SLOW-UPDATE marker, replace_slow_update_field must STRIP it so exactly ONE canonical
    region remains (else _region_span binds to the wrong END and corrupts the protected area)."""
    out = replace_slow_update_field("tactical.", f"strat {SLOW_UPDATE_END} hi {SLOW_UPDATE_BEGIN} x")
    assert out.count(SLOW_UPDATE_BEGIN) == 1 and out.count(SLOW_UPDATE_END) == 1
    assert "strat  hi  x" in out or "strat" in out   # content kept (markers stripped)


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
    # The validation gate keeps a candidate only if it STRICTLY beats current
    # (ties reject). This imports the REAL decision rule from loop.py — an
    # earlier version of this test asserted against a local re-implementation,
    # which could never fail no matter what optimize() did.
    from skillopt.loop import gate_decision as gate

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


def test_splits_small_total_nonempty_and_capped():
    """Regression: at SMALL totals, train/val/test must all be non-empty AND `total` respected.

    The old make_splits had two bugs that this catches: (a) max(3,...) ignored `total`
    (sum came out > total); (b) per-bucket floor division emptied `val`. Only total=40
    was tested before, where buckets are big enough to mask both.
    """
    from skillopt.splits import make_splits
    for total in (5, 8, 12, 20):
        s = make_splits(ratio=(2, 1, 7), seed=42, total=total)
        sz = {k: len(v) for k, v in s.items()}
        assert sz["train"] >= 1 and sz["val"] >= 1 and sz["test"] >= 1, f"empty split @ total={total}: {sz}"
        assert sum(sz.values()) == total, f"total not respected @ {total}: sum={sum(sz.values())} != {total}"
        tr, va, te = set(s["train"]), set(s["val"]), set(s["test"])
        assert not (tr & va) and not (tr & te) and not (va & te), f"overlap @ total={total}"


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


def test_sanitize_rejects_marker_containing_edits():
    """The optimizer can't sneak SLOW-UPDATE markers into target/content — defense-in-
    depth alongside skill.py's overlap-aware guard."""
    from skillopt.optimizer_llm import _sanitize_edits
    bad = [
        {"op": "replace", "target": f"x {SLOW_UPDATE_BEGIN}", "content": "y"},
        {"op": "append", "content": f"z {SLOW_UPDATE_END} z"},
        {"op": "insert_after", "target": "ok", "content": f"sneaky {SLOW_UPDATE_BEGIN}"},
    ]
    assert _sanitize_edits(bad) == []
    # legit edits still pass
    ok = _sanitize_edits([{"op": "append", "content": "rule one"},
                          {"op": "INSERT-AFTER", "target": "x", "content": "y"}])  # case/separator normalize
    assert {e["op"] for e in ok} == {"append", "insert_after"}


def test_extract_json_handles_prose_plus_blob():
    """Robust _extract_json grabs the right dict from prose+multi-blob output (Qwen3 pattern)."""
    from skillopt.optimizer_llm import _extract_json
    text = ('Let me think... {"thinking": "I need to add a rule."} '
            'Here are the edits: {"edits": [{"op":"append","content":"new rule"}]}')
    obj = _extract_json(text)
    assert "edits" in obj and isinstance(obj["edits"], list)
    assert obj["edits"][0]["op"] == "append"


def test_extract_json_skips_fenced_block_without_edits():
    """Regression (audit HIGH): the code-fence branch must NOT blindly return the FIRST
    fenced dict. Qwen3 often fences a thinking/example blob BEFORE the real answer; the
    old branch returned that thinking dict -> .get('edits',[]) == [] -> 0 edits -> step
    becomes a silent no-op. Must skip fenced blocks lacking 'edits'/'selected'."""
    from skillopt.optimizer_llm import _extract_json
    text = ('```json\n{"thinking": "let me reason about which rules to add"}\n```\n'
            'Now my actual answer:\n'
            '```json\n{"edits": [{"op": "append", "content": "rule X"}]}\n```')
    obj = _extract_json(text)
    assert "edits" in obj, f"grabbed wrong fenced dict: {obj}"
    assert obj["edits"][0]["op"] == "append"


def test_extract_json_fenced_selected_also_found():
    """The clip() path returns {'selected': [...]} — same fence-skip logic must apply."""
    from skillopt.optimizer_llm import _extract_json
    text = ('```\n{"note": "thinking out loud"}\n```\n'
            '```json\n{"selected": [0, 2]}\n```')
    obj = _extract_json(text)
    assert obj.get("selected") == [0, 2]


def test_report_prose_adapts_to_direction(tmp_path):
    """Regression (audit): mechanism-line prose must be data-driven, not hard-code
    'chiều DƯƠNG ... transfer'. When optimized is WORSE than seed it must say ÂM."""
    import json as _json
    from skillopt.report import compare
    def mk(name, passes):
        p = tmp_path / name
        rows = [{"task": f"bench/he_{i:03d}", "difficulty": "easy", "passed": bool(b), "repeat_idx": 0}
                for i, b in enumerate(passes)]
        p.write_text("\n".join(_json.dumps(r) for r in rows), encoding="utf-8")
        return p
    empty = mk("e.jsonl", [1] * 15 + [0] * 5)   # 15/20
    seed = mk("s.jsonl", [1] * 16 + [0] * 4)    # 16/20
    opt = mk("o.jsonl", [1] * 8 + [0] * 12)     # 8/20 — optimized MUCH worse than seed
    md = compare(empty, seed, opt)
    mech = [l for l in md.splitlines() if l.startswith("- test:")][0]
    assert "ÂM" in mech and "DƯƠNG" not in mech, mech
    assert "tín hiệu dương thật" not in mech, "must not claim positive transfer when worse"


def test_read_jsonl_tolerates_torn_final_line(tmp_path):
    """Regression (audit): a crashed/killed rollout can leave a half-written final line.
    _read_jsonl must skip the torn line, not crash the whole resumable run (mirror run.py's
    load_done, which guards per line)."""
    from skillopt.loop import _read_jsonl
    f = tmp_path / "r.jsonl"
    f.write_text('{"task": "a", "passed": true}\n'
                 '{"task": "b", "passed": false}\n'
                 '{"task": "c", "passed": tr', encoding="utf-8")  # torn final line
    rows = _read_jsonl(f)
    assert [r["task"] for r in rows] == ["a", "b"]


def test_skillopt_modules_import():
    """All loop/optimizer/report modules import without vLLM (no calls at import)."""
    import skillopt.loop  # noqa: F401
    import skillopt.optimizer_llm  # noqa: F401
    import skillopt.report  # noqa: F401
