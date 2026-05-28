"""
skillopt/report.py — honest A/B analysis on the LOCKED test split.

=== Giải thích ===
Tối ưu skill = chọn theo điểm val → val là "dữ liệu huấn luyện" cho skill. Nên con số
báo cáo PHẢI ở test split (chỉ chấm 1 lần). Module này đọc kết quả 3 nhánh trên test
(empty / seed / optimized), tính:
  - pass@1 tổng + theo difficulty,
  - Wilson 95% CI (khoảng tin cậy cho tỉ lệ — N nhỏ thì khoảng rộng, phải nói thẳng),
  - McNemar paired test (so từng-task empty/seed vs optimized — đúng cho dữ liệu ghép cặp),
  - train−test gap (thước đo overfit: train tăng mà test không = học vẹt).
Báo cáo TRUNG THỰC kể cả khi optimized KHÔNG hơn baseline (null/negative cũng là phát
hiện hợp lệ). Thuần stdlib (math) — không cần scipy.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Khoảng tin cậy Wilson 95% cho tỉ lệ k/n (ổn định hơn normal khi N nhỏ)."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    centre = p + z * z / (2 * n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((centre - half) / d, (centre + half) / d)


def mcnemar(b: int, c: int) -> tuple[float, float]:
    """McNemar (continuity-corrected). b,c = số task đảo chiều mỗi hướng. Trả (chi2, p).

    p cho chi-square 1 dof = erfc(sqrt(chi2/2)) (chính xác, không cần scipy).
    """
    if b + c == 0:
        return (0.0, 1.0)
    chi2 = (abs(b - c) - 1) ** 2 / (b + c)
    p = math.erfc(math.sqrt(chi2 / 2))
    return (chi2, p)


def _load(path: Path) -> dict[str, dict]:
    """Đọc JSONL kết quả → {task_id: record} (lấy repeat_idx=0 nếu có nhiều)."""
    out: dict[str, dict] = {}
    for ln in path.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        r = json.loads(ln)
        if r.get("task") not in out:  # giữ lần đầu
            out[r["task"]] = r
    return out


def _rate(recs: dict[str, dict]) -> tuple[int, int]:
    k = sum(1 for r in recs.values() if r.get("passed"))
    return k, len(recs)


def _paired(a: dict[str, dict], b: dict[str, dict]) -> tuple[int, int]:
    """(b, c) cho McNemar: b = a-pass & b-fail, c = a-fail & b-pass, trên task chung."""
    common = set(a) & set(b)
    bb = sum(1 for t in common if a[t].get("passed") and not b[t].get("passed"))
    cc = sum(1 for t in common if not a[t].get("passed") and b[t].get("passed"))
    return bb, cc


def compare(empty: Path, seed: Path, optimized: Path, train_traj: Path | None = None) -> str:
    """Sinh báo cáo markdown trung thực so 3 nhánh trên test."""
    arms = {"empty": _load(empty), "seed": _load(seed), "optimized": _load(optimized)}
    lines = ["# SkillOpt results (held-out test split)\n",
             "Báo cáo trên TEST (chấm 1 lần). Tối ưu chỉ dùng train+val.\n",
             "| arm | pass@1 | k/n | Wilson 95% CI |", "|---|---|---|---|"]
    for name, recs in arms.items():
        k, n = _rate(recs)
        lo, hi = wilson_ci(k, n)
        lines.append(f"| {name} | {k/n:.3f} | {k}/{n} | [{lo:.3f}, {hi:.3f}] |" if n else
                     f"| {name} | — | 0/0 | — |")

    lines.append("\n## Paired McNemar vs optimized")
    for base in ("empty", "seed"):
        b, c = _paired(arms[base], arms["optimized"])
        chi2, p = mcnemar(b, c)
        lines.append(f"- optimized vs {base}: {c} tasks improved, {b} regressed "
                     f"(χ²={chi2:.2f}, p={p:.3f})")

    # train−test gap (overfit meter), nếu có trajectory
    if train_traj and train_traj.exists():
        recs = [json.loads(l) for l in train_traj.read_text().splitlines() if l.strip()]
        done = [r for r in recs if r.get("event") == "done"]
        if done:
            d = done[-1]
            ke, ne = _rate(arms["optimized"])
            test_rate = ke / ne if ne else 0.0
            lines.append(f"\n## Overfit meter\n- best val score (train-side): "
                         f"{d.get('best_val_score'):.3f}; optimized test pass@1: {test_rate:.3f}; "
                         f"gap = {d.get('best_val_score', 0) - test_rate:+.3f} "
                         f"(lớn dương = nghi học vẹt trên val).")

    lines.append("\n## Verdict\n_(điền sau khi đọc số: optimized có vượt baseline trên test với "
                 "CI không chồng / McNemar p<0.05 không? Nếu không → null/negative, ghi trung thực.)_")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Honest SkillOpt A/B report on the test split.")
    ap.add_argument("--empty", type=Path, required=True)
    ap.add_argument("--seed", type=Path, required=True)
    ap.add_argument("--optimized", type=Path, required=True)
    ap.add_argument("--train-traj", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=Path("docs/SKILLOPT_RESULTS.md"))
    a = ap.parse_args()
    md = compare(a.empty, a.seed, a.optimized, a.train_traj)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(md, encoding="utf-8")
    print(f"wrote {a.out}\n\n{md}")
