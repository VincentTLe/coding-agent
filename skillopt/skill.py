"""
skillopt/skill.py — the skill document (the "trainable parameter") + its edit ops.

=== Giải thích cho người chưa biết ===
Trong SkillOpt, "skill" là một tài liệu văn bản (markdown) — KHÔNG phải code, KHÔNG
phải trọng số model. Nó là phần DUY NHẤT được "huấn luyện": optimizer đề xuất các
"edit" (sửa văn bản) và ta áp dần. Có 4 loại edit (giống repo gốc microsoft/SkillOpt):
  - append:       nối thêm một đoạn vào cuối
  - insert_after: chèn sau lần xuất hiện đầu của một đoạn mốc (target)
  - replace:      thay lần xuất hiện đầu của target bằng content
  - delete:       xoá lần xuất hiện đầu của target

QUAN TRỌNG — vùng được bảo vệ (protected slow-update region): skill có một khu vực
nằm giữa 2 marker SLOW-UPDATE, chứa "chiến lược điều hành" chỉ được ghi ở RANH GIỚI
EPOCH (slow update). Các edit cấp-step KHÔNG được đụng vào đó. Đây chính là phần rẻ
tiền (~vài chục dòng xử lý chuỗi) nhưng bảo vệ kết quả lớn nhất trong ablation của
paper (bỏ slow-update + protected region khiến điểm rớt mạnh). Ta port logic này
trung thực: edit nhắm vào vùng protected bị bỏ qua; append/insert không có target
được định tuyến vào TRƯỚC vùng đó; marker bị gỡ khỏi content của edit để không ai
"chèn marker giả".

Port + chú thích từ microsoft/SkillOpt (MIT) `optimizer/skill.py`. Thuần stdlib, không
cần vLLM/network → test được offline.
"""

from __future__ import annotations

import hashlib

# Marker phân định vùng "executive strategy" chỉ sửa ở ranh giới epoch.
SLOW_UPDATE_BEGIN = "<!-- SLOW-UPDATE:BEGIN (executive strategy — epoch-boundary only) -->"
SLOW_UPDATE_END = "<!-- SLOW-UPDATE:END -->"


def skill_hash(skill: str) -> str:
    """Hash ổn định 16 ký tự của nội dung skill — để cache điểm gate theo phiên bản."""
    return hashlib.sha256(skill.encode("utf-8")).hexdigest()[:16]


def _region_span(skill: str) -> tuple[int, int] | None:
    """(start, end) ký tự của vùng protected (gồm cả 2 marker), hoặc None nếu chưa có."""
    b = skill.find(SLOW_UPDATE_BEGIN)
    if b == -1:
        return None
    e = skill.find(SLOW_UPDATE_END, b)
    if e == -1:
        return None
    return (b, e + len(SLOW_UPDATE_END))


def _is_in_slow_update_region(skill: str, target: str) -> bool:
    """True nếu target ĐỤNG vào vùng protected (overlap), KHÔNG chỉ check start.

    Bug pre-fix: chỉ kiểm `span[0] <= idx < span[1]` (chỉ vị trí bắt đầu) → một target
    bắt đầu NGOÀI vùng nhưng kéo dài INTO/THROUGH vùng vẫn pass guard → replace/delete
    xoá marker BEGIN → phá vùng vĩnh viễn. Bản fix: kiểm tra overlap thật giữa range
    của target [idx, idx+len(target)) và range của vùng [span[0], span[1]).
    """
    span = _region_span(skill)
    if span is None or not target:
        return False
    idx = skill.find(target)
    if idx == -1:
        return False
    # Hai khoảng overlap khi: idx < span[1] AND span[0] < idx + len(target).
    return idx < span[1] and span[0] < idx + len(target)


def _strip_markers(text: str) -> str:
    """Gỡ mọi marker SLOW-UPDATE khỏi content của edit (chống chèn marker giả)."""
    return text.replace(SLOW_UPDATE_BEGIN, "").replace(SLOW_UPDATE_END, "")


def _append_before_region(skill: str, content: str) -> str:
    """Nối content vào cuối — nhưng TRƯỚC vùng protected nếu có (không lọt vào/sau nó)."""
    span = _region_span(skill)
    if span is None:
        sep = "" if (not skill or skill.endswith("\n")) else "\n"
        return skill + sep + content + "\n"
    return skill[:span[0]] + content + "\n\n" + skill[span[0]:]


def apply_edits(skill: str, edits: list[dict]) -> tuple[str, list[dict]]:
    """Áp tuần tự danh sách edit lên skill; trả (skill_mới, reports).

    edit = {"op": append|insert_after|replace|delete, "target": str?, "content": str?}.
    Mỗi op chỉ tác động occurrence ĐẦU TIÊN. Vùng protected được bảo vệ (xem module
    docstring). reports ghi trạng thái từng edit để log/audit (applied / skipped_*).
    """
    reports: list[dict] = []
    for e in edits:
        op = (e.get("op") or "").strip()
        # Strip marker khỏi CẢ target VÀ content — chống "đặt tên" marker để né guard
        # (cùng với _is_in_slow_update_region đã overlap-aware, là 2 lớp phòng thủ).
        target = _strip_markers(e.get("target") or "")
        content = _strip_markers(e.get("content") or "")
        status = "applied"

        if op == "append":
            skill = _append_before_region(skill, content)

        elif op == "insert_after":
            if not target or target not in skill:
                skill = _append_before_region(skill, content)  # target thiếu → fallback append
                status = "applied(append_fallback)"
            elif _is_in_slow_update_region(skill, target):
                status = "skipped_protected_region"
            else:
                idx = skill.find(target) + len(target)
                skill = skill[:idx] + "\n" + content + skill[idx:]

        elif op == "replace":
            if not target or target not in skill:
                status = "skipped_target_not_found"
            elif _is_in_slow_update_region(skill, target):
                status = "skipped_protected_region"
            else:
                skill = skill.replace(target, content, 1)

        elif op == "delete":
            if not target or target not in skill:
                status = "skipped_target_not_found"
            elif _is_in_slow_update_region(skill, target):
                status = "skipped_protected_region"
            else:
                skill = skill.replace(target, "", 1)

        else:
            status = f"skipped_unknown_op:{op}"

        reports.append({"op": op, "target": target[:60], "status": status})
    return skill, reports


def ensure_slow_update_region(skill: str) -> str:
    """Đảm bảo skill có ĐÚNG 1 vùng slow-update; CHUẨN HOÁ marker mồ côi (BEGIN-not-END
    hoặc END-not-BEGIN, hoặc marker thừa ngoài vùng).

    Nếu có vùng hợp lệ → strip mọi marker NGOÀI vùng (chống ô nhiễm). Nếu không có vùng
    (kể cả khi có marker mồ côi do edit cũ phá), strip sạch rồi gắn vùng rỗng ở cuối.
    """
    span = _region_span(skill)
    if span is not None:
        prefix = skill[:span[0]].replace(SLOW_UPDATE_BEGIN, "").replace(SLOW_UPDATE_END, "")
        suffix = skill[span[1]:].replace(SLOW_UPDATE_BEGIN, "").replace(SLOW_UPDATE_END, "")
        return prefix + skill[span[0]:span[1]] + suffix
    # không có vùng → strip mồ côi (nếu có) rồi gắn vùng rỗng ở cuối
    clean = skill.replace(SLOW_UPDATE_BEGIN, "").replace(SLOW_UPDATE_END, "")
    return clean.rstrip() + "\n\n" + SLOW_UPDATE_BEGIN + "\n" + SLOW_UPDATE_END + "\n"


def replace_slow_update_field(skill: str, content: str) -> str:
    """Ghi đè nội dung vùng slow-update (CHỈ gọi ở ranh giới epoch / slow update).

    STRIP marker khỏi `content` (Codex design review HIGH): nếu prose của optimizer lỡ chứa
    SLOW_UPDATE_BEGIN/END, ghi thẳng vào vùng sẽ tạo marker THỪA → _region_span bám nhầm END
    → phá vùng bảo vệ. Step-edit đã strip qua apply_edits; slow-update giờ cũng strip cho khớp.
    """
    skill = ensure_slow_update_region(skill)
    span = _region_span(skill)
    assert span is not None  # ensure_… vừa tạo nên chắc chắn có
    new_region = SLOW_UPDATE_BEGIN + "\n" + _strip_markers(content).strip() + "\n" + SLOW_UPDATE_END
    return skill[:span[0]] + new_region + skill[span[1]:]
