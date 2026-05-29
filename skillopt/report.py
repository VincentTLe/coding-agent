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
    """McNemar EXACT (binomial). b,c = số task đảo chiều mỗi hướng. Trả (n_discordant, p).

    Dùng exact binomial thay vì xấp xỉ chi-square (Codex methodology review): với discordant
    count NHỎ (ở đây 3-8) xấp xỉ chi-square kém tin. Dưới H0 mỗi cặp lệch chia đều 50/50, nên
    p HAI PHÍA = min(1, 2·P(X ≤ min(b,c))) với X ~ Binom(b+c, 0.5). Thuần stdlib (math.comb).
    """
    n = b + c
    if n == 0:
        return (0.0, 1.0)
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) * (0.5 ** n)
    return (float(n), min(1.0, 2.0 * tail))


def _load(path: Path) -> dict[str, dict]:
    """Đọc JSONL kết quả → {task_id: record} cho pass@1.

    CHỈ giữ repeat_idx==0 (lần thử đầu = định nghĩa pass@1; nếu file có repeats>1 thì
    các lần sau bị bỏ, không để lần may mắn đẩy số lên). Với run repeats=1 mọi record
    đều repeat_idx==0 nên đây là phòng thủ. Báo lỗi rõ nếu thiếu file (chạy tự động phải
    fail to, không sinh report rác).
    """
    if not path.exists():
        raise FileNotFoundError(f"report: thiếu file kết quả {path} — eval arm này chưa chạy xong?")
    out: dict[str, dict] = {}
    for ln in path.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        r = json.loads(ln)
        if r.get("repeat_idx", 0) != 0:   # chỉ pass@1 (lần đầu)
            continue
        if r.get("task") not in out:       # giữ lần đầu gặp
            out[r["task"]] = r
    return out


def _rate(recs: dict[str, dict]) -> tuple[int, int]:
    k = sum(1 for r in recs.values() if r.get("passed"))
    return k, len(recs)


def _by_difficulty(recs: dict[str, dict]) -> dict[str, tuple[int, int]]:
    """{difficulty: (k, n)} — pass@1 tách theo độ khó (plan yêu cầu)."""
    buckets: dict[str, list[dict]] = {}
    for r in recs.values():
        buckets.setdefault(r.get("difficulty", "?"), []).append(r)
    return {d: (sum(1 for r in rs if r.get("passed")), len(rs)) for d, rs in buckets.items()}


def _paired(a: dict[str, dict], b: dict[str, dict]) -> tuple[int, int]:
    """(b, c) cho McNemar: b = a-pass & b-fail, c = a-fail & b-pass, trên task chung."""
    common = set(a) & set(b)
    bb = sum(1 for t in common if a[t].get("passed") and not b[t].get("passed"))
    cc = sum(1 for t in common if not a[t].get("passed") and b[t].get("passed"))
    return bb, cc


def _flips(a: dict[str, dict], b: dict[str, dict]) -> int:
    """Số task đổi pass↔fail giữa 2 lần đo (trên task chung)."""
    common = set(a) & set(b)
    return sum(1 for t in common if a[t].get("passed") != b[t].get("passed"))


def compare(empty: Path, seed: Path, optimized: Path, train_traj: Path | None = None,
            empty_rerun: Path | None = None) -> str:
    """Sinh báo cáo markdown trung thực so 3 nhánh trên test.

    empty_rerun (tuỳ chọn): kết quả chạy LẠI arm empty cùng config → đo SÀN NHIỄU
    (bao nhiêu task lật chỉ do phi tất định của vLLM ở temp=0). Sàn nhiễu là thước đo
    BẮT BUỘC để biết các khác biệt giữa arm có vượt nhiễu hay không.
    """
    arms = {"empty": _load(empty), "seed": _load(seed), "optimized": _load(optimized)}
    rates = {name: _rate(recs) for name, recs in arms.items()}
    lines = ["# SkillOpt results (held-out test split)\n",
             "Báo cáo trên TEST (chấm 1 lần). Tối ưu chỉ dùng train+val.\n"]
    # Paired comparison CHỈ hợp lệ khi 3 arm chấm ĐÚNG cùng tập task — cảnh báo to nếu lệch
    # (Codex methodology review: _paired() âm thầm lấy giao → có thể giấu task thiếu/thừa).
    sets = {n: set(a) for n, a in arms.items()}
    if not (sets["empty"] == sets["seed"] == sets["optimized"]):
        common = sets["empty"] & sets["seed"] & sets["optimized"]
        lines.append(f"> ⚠️ **CẢNH BÁO: 3 arm KHÔNG cùng tập task** (empty {len(sets['empty'])}, "
                     f"seed {len(sets['seed'])}, optimized {len(sets['optimized'])}; giao = {len(common)}). "
                     "So sánh paired chỉ tính trên phần giao — đọc số thận trọng.\n")
    lines += ["| arm | pass@1 | k/n | Wilson 95% CI |", "|---|---|---|---|"]
    for name in ("empty", "seed", "optimized"):
        k, n = rates[name]
        lo, hi = wilson_ci(k, n)
        lines.append(f"| {name} | {k/n:.3f} | {k}/{n} | [{lo:.3f}, {hi:.3f}] |" if n else
                     f"| {name} | — | 0/0 | — |")

    # pass@1 theo difficulty (mỗi arm 1 cột) — cho thấy skill giúp/hại ở nhóm nào.
    diffs = {name: _by_difficulty(recs) for name, recs in arms.items()}
    all_d = sorted({d for dd in diffs.values() for d in dd})
    if all_d:
        lines.append("\n## pass@1 theo difficulty")
        lines.append("| difficulty | empty | seed | optimized |")
        lines.append("|---|---|---|---|")
        for d in all_d:
            cells = []
            for name in ("empty", "seed", "optimized"):
                k, n = diffs[name].get(d, (0, 0))
                cells.append(f"{k}/{n} ({k/n:.2f})" if n else "—")
            lines.append(f"| {d} | {cells[0]} | {cells[1]} | {cells[2]} |")

    lines.append("\n## Paired McNemar vs optimized (exact binomial)")
    mcn = {}
    for base in ("empty", "seed"):
        b, c = _paired(arms[base], arms["optimized"])
        n_disc, p = mcnemar(b, c)
        mcn[base] = (b, c, p)
        lines.append(f"- optimized vs {base}: {c} tasks improved, {b} regressed "
                     f"(n_discordant={n_disc:.0f}, exact-binomial p={p:.3f})")

    # --- SÀN NHIỄU (chạy lại empty cùng config) → reframe mọi khác biệt -------
    noise_flips = None
    if empty_rerun is not None and empty_rerun.exists():
        e2 = _load(empty_rerun)
        noise_flips = _flips(arms["empty"], e2)
        k2, n2 = _rate(e2)
        ke0, ne0 = rates["empty"]
        es = _flips(arms["empty"], arms["seed"])
        eo = _flips(arms["empty"], arms["optimized"])
        so = _flips(arms["seed"], arms["optimized"])
        lines.append("\n## Run-to-run instability (empty chạy lại cùng config)")
        lines.append(f"- empty#1 {ke0/ne0:.3f} ({ke0}/{ne0}) vs empty#2 {k2/n2:.3f} ({k2}/{n2}): "
                     f"**{noise_flips} task lật** chỉ do phi tất định (vLLM batching ở temp=0 KHÔNG "
                     "tất định). ⚠️ Đây là MỘT lần đo (1 draw) — chỉ ƯỚC LƯỢNG độ bất ổn run-to-run, "
                     "KHÔNG phải 'sàn nhiễu' chính thức (Codex methodology review).")
        # Diễn giải CÓ ĐIỀU KIỆN — và chỉ là HEURISTIC (không phải test thống kê chính thức).
        max_between = max(es, eo, so)
        if max_between <= noise_flips:
            verdict_noise = (f"Mọi khác biệt giữa arm (≤{max_between}) CÙNG CỠ hoặc nhỏ hơn độ bất ổn "
                             f"run-to-run ({noise_flips}) → KHÔNG kết luận được (heuristic).")
        elif max_between <= noise_flips + 2:
            verdict_noise = (f"Khác biệt lớn nhất ({max_between}) chỉ sát mức bất ổn ({noise_flips}) → "
                             "vẫn nên coi là chưa kết luận; cần nhiều run/arm để chắc.")
        else:
            verdict_noise = (f"Khác biệt lớn nhất ({max_between}) vượt mức bất ổn ({noise_flips}) → "
                             "có thể là tín hiệu; đọc kèm McNemar exact bên dưới (đó mới là test).")
        lines.append(f"- So flips giữa arm: empty–seed={es}, empty–optimized={eo}, seed–optimized={so}. "
                     + verdict_noise)

    # --- Mechanism check + overfit meter (cần trajectory) --------------------
    # Tối ưu LUÔN xuất phát từ seed. Hai câu hỏi tách bạch:
    #   (1) Cơ chế: optimized có hơn ĐIỂM XUẤT PHÁT (seed) không, và cải thiện val có
    #       TRANSFER sang test không? (val Δ từ trajectory; test Δ = optimized−seed)
    #   (2) Triển khai: có nên chèn skill nào không? = optimized vs empty (verdict dưới).
    seed_val = best_val = None
    if train_traj and train_traj.exists():
        recs = [json.loads(l) for l in train_traj.read_text().splitlines() if l.strip()]
        init = [r for r in recs if r.get("event") == "init"]
        done = [r for r in recs if r.get("event") == "done"]
        if init:
            seed_val = init[0].get("seed_val_score")
        if done:
            best_val = done[-1].get("best_val_score")
    ke, ne = rates["optimized"]
    test_opt = ke / ne if ne else 0.0
    ks, ns = rates["seed"]
    test_seed = ks / ns if ns else 0.0
    b_so, c_so = _paired(arms["seed"], arms["optimized"])  # b=optimized tệ hơn, c=optimized tốt hơn
    _, p_so = mcnemar(b_so, c_so)
    lines.append("\n## Mechanism check (optimized vs điểm xuất phát seed)")
    if seed_val is not None and best_val is not None:
        lines.append(f"- val: seed {seed_val:.3f} → best {best_val:.3f} (Δ={best_val - seed_val:+.3f}) "
                     "— ⚠️ |val| rất nhỏ (xem manifest, ở run này = 12 task → 1 task ≈ 0.083); "
                     "nên tín hiệu val chỉ là VÀI task, không phải bằng chứng mạnh.")
    # Diễn giải CÓ ĐIỀU KIỆN theo dấu(Δ) và p (không hard-code "DƯƠNG/trong nhiễu").
    d_test = test_opt - test_seed
    direction = "DƯƠNG (optimized > seed)" if d_test > 0 else ("ÂM (optimized < seed)" if d_test < 0 else "BẰNG NHAU")
    if p_so < 0.05 and d_test > 0:
        interp = "**có ý nghĩa thống kê (p<0.05)** → edit học được transfer sang test (tín hiệu dương thật)."
    elif p_so < 0.05 and d_test < 0:
        interp = "**có ý nghĩa thống kê (p<0.05) NHƯNG theo chiều ÂM** → optimized TỆ hơn seed trên test."
    else:
        interp = ("**KHÔNG đạt p<0.05 → nằm trong nhiễu**, CHƯA thể khẳng định edit 'transfer' "
                  "(tín hiệu hướng yếu, không ý nghĩa thống kê).")
    lines.append(f"- test: seed {test_seed:.3f} → optimized {test_opt:.3f} (Δ={d_test:+.3f}; "
                 f"{c_so} task tốt lên, {b_so} task tệ đi trên |test|={ns}, McNemar p={p_so:.3f}); "
                 f"chiều {direction}, {interp}")
    if best_val is not None:
        lines.append(f"\n## Overfit meter\n- best val (train-side) {best_val:.3f}; optimized test "
                     f"{test_opt:.3f}; gap = {best_val - test_opt:+.3f} (lớn dương = nghi học vẹt trên val).")

    # --- Verdict tự động (data-driven, không để người điền) -------------------
    ko, no = rates["optimized"]
    opt = ko / no if no else 0.0
    best_base_name = max(("empty", "seed"), key=lambda n: (rates[n][0] / rates[n][1]) if rates[n][1] else 0)
    kb, nb = rates[best_base_name]
    base_best = kb / nb if nb else 0.0
    sig = [base for base in ("empty", "seed")
           if mcn[base][2] < 0.05 and mcn[base][1] > mcn[base][0]]  # p<.05 và improved>regressed
    lines.append("\n## Verdict (tự động)")
    # Sàn nhiễu ƯU TIÊN: nếu mọi khác biệt giữa arm ≤ sàn nhiễu → under-powered, KHÔNG
    # kết luận hơn/kém được, dù point-estimate có chênh. Đây là sự thật mạnh hơn "null".
    if noise_flips is not None:
        eo = _flips(arms["empty"], arms["optimized"])   # câu hỏi chính: skill tối ưu vs không skill
        es = _flips(arms["empty"], arms["seed"])
        so = _flips(arms["seed"], arms["optimized"])
        max_between = max(eo, es, so)
        # Under-powered nếu KHÔNG có McNemar significant VÀ khác biệt chính (empty↔optimized)
        # không vượt sàn nhiễu → point-estimate không đáng tin ở N này.
        if not sig and eo <= noise_flips:
            lines.append(
                f"- **INCONCLUSIVE (under-powered).** Khác biệt giữa arm (empty↔optimized={eo}, "
                f"empty↔seed={es}, seed↔optimized={so}) CÙNG CỠ với độ bất ổn run-to-run "
                f"(empty chạy lại lật {noise_flips} task), và KHÔNG McNemar exact nào đạt p<0.05. "
                f"Point-estimate (empty {rates['empty'][0]/rates['empty'][1]:.3f} / seed "
                f"{rates['seed'][0]/rates['seed'][1]:.3f} / optimized {opt:.3f}) là 1 mẫu nhiễu/arm ở "
                f"N={no}. **Không có bằng chứng tin cậy rằng skill (seed hay optimized) giúp HAY hại** — "
                "khác biệt quan sát nhỏ hơn hoặc ngang mức bất ổn đo được. Đây là kết luận trung thực; "
                "muốn quyết: ≥3–5 run/arm (trung bình) hoặc N test lớn hơn nhiều. (Lưu ý: 'mức bất ổn' "
                "là heuristic 1-lần-đo, không phải test thống kê — xem McNemar exact ở trên.)")
            return "\n".join(lines) + "\n"
    if opt > base_best and sig:
        lines.append(f"- **Optimized cao hơn baseline** ({opt:.3f} vs {best_base_name} {base_best:.3f}) "
                     f"VÀ có ý nghĩa thống kê theo McNemar (p<0.05) so với: {', '.join(sig)}. "
                     "Tín hiệu dương — nhưng vẫn đọc CI + #task (N nhỏ thì khiêm tốn khi kết luận).")
    elif opt > base_best:
        lines.append(f"- Optimized nhỉnh hơn baseline ({opt:.3f} vs {best_base_name} {base_best:.3f}) "
                     "NHƯNG McNemar KHÔNG đạt p<0.05 → khác biệt nằm trong nhiễu. "
                     "**Honest:** chưa đủ bằng chứng skill tối ưu vượt baseline trên test.")
    else:
        mech = ("Cơ chế VẪN chạy đúng hướng (optimized > seed trên test: "
                f"{test_opt:.3f} > {test_seed:.3f}) — edit học được transfer sang test; "
                if test_opt > test_seed else
                "Và optimized cũng không vượt seed trên test — cơ chế không transfer; ")
        lines.append(f"- **Null/negative (triển khai):** optimized ({opt:.3f}) KHÔNG vượt baseline "
                     f"tốt nhất ({best_base_name} {base_best:.3f}). {mech}"
                     "nhưng kết luận triển khai trung thực: trên slice coding-only + N test này, "
                     "base model đóng băng đã gần trần — chèn skill (seed hay optimized) không "
                     "thắng được 'không skill'. Phát hiện null hợp lệ, ghi đúng sự thật.")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Honest SkillOpt A/B report on the test split.")
    ap.add_argument("--empty", type=Path, required=True)
    ap.add_argument("--seed", type=Path, required=True)
    ap.add_argument("--optimized", type=Path, required=True)
    ap.add_argument("--train-traj", type=Path, default=None)
    ap.add_argument("--empty-rerun", type=Path, default=None,
                    help="empty chạy lại cùng config → đo sàn nhiễu (reframe mọi khác biệt)")
    ap.add_argument("--out", type=Path, default=Path("docs/SKILLOPT_RESULTS.md"))
    a = ap.parse_args()
    md = compare(a.empty, a.seed, a.optimized, a.train_traj, a.empty_rerun)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(md, encoding="utf-8")
    print(f"wrote {a.out}\n\n{md}")
