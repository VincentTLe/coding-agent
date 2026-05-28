"""
skillopt/optimizer_llm.py — the optimizer LLM calls = the "textual gradient".

=== Giải thích ===
Đây là phần tính "gradient bằng chữ": một model (optimizer — mặc định CÙNG Qwen3-14B,
có thể đổi qua env AGENT_OPTIMIZER_MODEL) ĐỌC các ca fail/success rồi ĐỀ XUẤT chỉnh
sửa cho skill dưới dạng JSON edit (append/insert_after/replace/delete).
  - reflect():  từ một batch ca (failure HOẶC success) → list edit. Failure → luật
                khắc phục; success → luật củng cố. Ca failure được gắn nhãn finish_reason
                (no_action / timeout / failed-tests …) để optimizer biết KIỂU lỗi.
  - merge():    gộp edit từ 2 kênh, ƯU TIÊN failure, khử trùng/giải mâu thuẫn (1 lần gọi
                LLM + fallback nối thẳng nếu LLM hỏng).
  - clip():     nếu số edit > L thì xếp hạng giữ top-L (1 lần gọi) — đây là "learning
                rate" giới hạn bước; fallback cắt L cái đầu.
Model local 14B trả JSON không phải lúc nào cũng chuẩn → mọi hàm có FALLBACK an toàn
(không bao giờ raise vào loop). Cấu trúc prompt phỏng theo microsoft/SkillOpt (MIT)
`gradient/`+`optimizer/` (analyst_error/analyst_success/merge/ranking), viết gọn lại.
"""

from __future__ import annotations

import json
import os
import re

from src.agent import get_client, get_model

# Loại op hợp lệ cho một edit (khớp skillopt/skill.py).
_VALID_OPS = {"append", "insert_after", "replace", "delete"}


def _optimizer_model() -> str:
    """Model đóng vai optimizer: env AGENT_OPTIMIZER_MODEL nếu có, else = target model."""
    return os.environ.get("AGENT_OPTIMIZER_MODEL") or get_model()


def _call(system: str, user: str, *, max_tokens: int = 2048, temperature: float = 0.0) -> str:
    """Gọi optimizer LLM 1 lượt (non-stream), trả về text. Lỗi mạng → chuỗi rỗng."""
    try:
        resp = get_client().chat.completions.create(
            model=_optimizer_model(),
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return resp.choices[0].message.content or ""
    except Exception as e:  # noqa: BLE001 — optimizer không bao giờ được giết vòng lặp
        return f""  # rỗng → caller dùng fallback


def _extract_json(text: str) -> dict:
    """Bóc khối JSON object đầu tiên từ text (model hay bọc bằng ```json / lời dẫn)."""
    if not text:
        return {}
    # ưu tiên khối ```json ... ```
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    raw = m.group(1) if m else None
    if raw is None:  # else: lấy từ '{' đầu tới '}' cuối
        i, j = text.find("{"), text.rfind("}")
        raw = text[i:j + 1] if (i != -1 and j > i) else ""
    try:
        return json.loads(raw)
    except Exception:  # noqa: BLE001
        return {}


def _sanitize_edits(raw_edits: list) -> list[dict]:
    """Giữ lại các edit hợp lệ: op trong _VALID_OPS, có content/target phù hợp."""
    out: list[dict] = []
    for e in raw_edits if isinstance(raw_edits, list) else []:
        if not isinstance(e, dict):
            continue
        op = str(e.get("op", "")).strip()
        if op not in _VALID_OPS:
            continue
        edit = {"op": op, "target": str(e.get("target", "") or ""),
                "content": str(e.get("content", "") or "")}
        # replace/delete/insert_after cần target; append cần content
        if op in {"replace", "delete", "insert_after"} and not edit["target"]:
            if op != "insert_after":   # insert_after không target → sẽ fallback append
                continue
        if op in {"append", "insert_after", "replace"} and not edit["content"]:
            continue
        out.append(edit)
    return out


_OP_SCHEMA = (
    'Return STRICT JSON: {"edits": [{"op": "...", "target": "...", "content": "..."}]}\n'
    'op ∈ {append, insert_after, replace, delete}. "append"/"insert_after"/"replace" need '
    '"content"; "insert_after"/"replace"/"delete" need an exact "target" substring of the skill. '
    "Propose GENERALIZABLE rules (no task-specific hardcoding, no duplicates). Keep edits small."
)


def reflect(skill: str, cases: list[dict], kind: str, rejected_summary: str, L: int) -> list[dict]:
    """Đề xuất ≤L edit từ một batch ca (kind='failure' hoặc 'success')."""
    if not cases:
        return []
    if kind == "failure":
        intent = ("These task attempts FAILED. Each shows finish_reason (no_action=model talked "
                  "without acting; timeout=ran out of steps; finished-but-failed=wrong solution). "
                  "Propose corrective rules the skill is MISSING that would prevent these failures.")
    else:
        intent = ("These task attempts SUCCEEDED. Propose rules that PRESERVE/REINFORCE the "
                  "behaviors that made them work, without bloating the skill.")
    case_text = "\n".join(
        f"- [{c.get('task')}] passed={c.get('passed')} finish_reason={c.get('finish_reason')}\n"
        f"  {(c.get('summary') or '')[:400]}" for c in cases[:8])
    reject_block = f"\nEdits already tried and REJECTED (do not re-propose):\n{rejected_summary}" if rejected_summary else ""
    user = (f"CURRENT SKILL:\n{skill}\n\n{intent}\n\nCASES:\n{case_text}{reject_block}\n\n"
            f"Propose at most {L} edits. {_OP_SCHEMA}")
    edits = _sanitize_edits(_extract_json(_call(
        "You are SkillOpt's optimizer: you improve a coding agent's skill document from evidence.",
        user)).get("edits", []))
    return edits[:L]


def merge(skill: str, fail_edits: list[dict], success_edits: list[dict]) -> list[dict]:
    """Gộp edit 2 kênh, ƯU TIÊN failure, khử trùng/giải mâu thuẫn. Fallback: nối thẳng."""
    if not fail_edits and not success_edits:
        return []
    if not (fail_edits and success_edits):
        return fail_edits or success_edits  # 1 kênh rỗng → khỏi gọi LLM
    pool = {"failure_high_priority": fail_edits, "success_lower_priority": success_edits}
    user = (f"CURRENT SKILL:\n{skill}\n\nMerge these proposed edits into a deduplicated, "
            f"non-contradictory list. Failure-driven edits take PRIORITY over success-driven "
            f"ones when they conflict.\n{json.dumps(pool, ensure_ascii=False)}\n\n{_OP_SCHEMA}")
    merged = _sanitize_edits(_extract_json(_call(
        "You merge skill edits, prioritizing failure fixes.", user)).get("edits", []))
    return merged or (fail_edits + success_edits)  # fallback: failure-first concat


def clip(skill: str, edits: list[dict], L: int) -> list[dict]:
    """Giới hạn về L edit (learning rate). >L → xếp hạng giữ top-L; fallback cắt L đầu."""
    if len(edits) <= L:
        return edits  # dưới ngân sách → không cần gọi LLM (tiết kiệm)
    numbered = "\n".join(f"[{i}] {e['op']}: {(e.get('content') or e.get('target') or '')[:200]}"
                         for i, e in enumerate(edits))
    user = (f"CURRENT SKILL:\n{skill}\n\nSelect the {L} most useful edits below. Return STRICT "
            f'JSON {{"selected": [indices]}} (0-based, priority order).\n{numbered}')
    sel = _extract_json(_call("You rank skill edits by expected utility.", user)).get("selected", [])
    chosen, seen = [], set()
    for idx in sel if isinstance(sel, list) else []:
        if isinstance(idx, int) and 0 <= idx < len(edits) and idx not in seen:
            seen.add(idx)
            chosen.append(edits[idx])
        if len(chosen) >= L:
            break
    return chosen or edits[:L]  # fallback: cắt L cái đầu
