"""
skillopt/splits.py — deterministic stratified train/val/test split (the "dataset").

=== Giải thích ===
SkillOpt chia task thành 3 phần RỜI NHAU:
  - train : optimizer chạy rollout để lấy "bằng chứng" (fail/success) → đề xuất sửa skill.
  - val   : CỔNG kiểm tra — chỉ dùng để CHẤP NHẬN/TỪ CHỐI một bản skill (không train trên đó).
  - test  : KHOÁ — chỉ chấm 1 lần ở cuối (3 lần cho empty/seed/optimized) để báo cáo.
Tỉ lệ mặc định 2:1:7 (như paper) — test cố tình LỚN NHẤT để ước lượng generalization
đáng tin (Wilson CI / McNemar cần N test đủ lớn). Đây KHÔNG phải 60/20/20 của train-weight:
"tham số" ở đây là 1 tài liệu text bé, rollout train tốn kém nên train/val nhỏ, còn test
chỉ chấm vài lần nên để to được.

Phân tầng theo difficulty (easy/medium/hard) để mỗi split đều trải đủ độ khó. Tất định
theo seed (mặc định 42) → cùng seed cho ra cùng split (tái lập được). Tái dùng
discover_tasks/read_task_meta/rel_id của eval harness (không tự đọc lại task.md).
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

from eval.run import TASKS_DIR, discover_tasks, read_task_meta, rel_id


def _apportion(total: int, weights: list[int]) -> list[int]:
    """Chia số nguyên `total` theo weights bằng LARGEST-REMAINDER (Hamilton).

    Tổng kết quả == total (khi total >= 0). Khác phép `//` (floor) ở chỗ phần dư KHÔNG
    bị vứt: nó được phát cho các phần tử có phần lẻ (exact - floor) lớn nhất. Đây là
    cách sửa GỐC của cả 2 bug cũ — floor làm `val` rỗng, và `max(3,…)` làm `total` vô
    tác dụng — thay cho cả hai.
    """
    n = len(weights)
    s = sum(weights)
    if total <= 0 or s <= 0:
        return [0] * n
    exact = [total * w / s for w in weights]
    base = [int(x) for x in exact]                 # floor
    rem = total - sum(base)                         # số suất dư cần phát
    # phát cho phần tử có phần lẻ lớn nhất; tie-break theo index nhỏ hơn (tất định)
    order = sorted(range(n), key=lambda i: (exact[i] - base[i], -i), reverse=True)
    for k in range(rem):
        base[order[k % n]] += 1
    return base


def make_splits(ratio: tuple[int, int, int] = (2, 1, 7), seed: int = 42,
                total: int | None = None, tasks_root: Path | None = None) -> dict[str, list[str]]:
    """Chia task → {"train","val","test"} (rời nhau), phân tầng theo difficulty, tất định.

    ratio = (train, val, test). total = cắt tổng số task (None = dùng hết).
    Dùng largest-remainder ở CẢ 2 cấp: (1) phân bổ `total` cho từng bucket độ khó theo
    kích thước bucket, (2) chia mỗi bucket thành train/val/test theo `ratio`. Nhờ vậy
    `total` luôn được tôn trọng (sum == min(total, n_all)) và `val` không bị floor nuốt.
    Lưới an toàn cuối: nếu đã chọn >= 3 task mà split nào rỗng, mượn 1 từ split lớn nhất
    — đảm bảo loop không bao giờ nhận train/val rỗng kể cả ở total rất nhỏ.
    """
    # Tiền điều kiện: ratio phải là 3 số NGUYÊN DƯƠNG (Codex design review #4). ratio 0/âm làm
    # apportionment vô nghĩa (0:0:0 bỏ hết task; âm ra count vô lý) — fail rõ thay vì âm thầm sai.
    if len(ratio) != 3 or any((not isinstance(w, int)) or w <= 0 for w in ratio):
        raise ValueError(f"ratio phải là 3 số nguyên dương (train,val,test); nhận {ratio!r}")

    root = tasks_root or TASKS_DIR
    tasks = discover_tasks(root)

    # Gom task-id theo difficulty, sắp xếp ổn định rồi xáo trộn (tất định theo seed).
    by_diff: dict[str, list[str]] = {}
    for t in tasks:
        diff = read_task_meta(t)["difficulty"]
        by_diff.setdefault((diff or "unknown").lower(), []).append(rel_id(t))
    rng = random.Random(seed)
    diffs = sorted(by_diff)
    for d in diffs:
        by_diff[d] = sorted(by_diff[d])
        rng.shuffle(by_diff[d])

    n_all = sum(len(v) for v in by_diff.values())
    target = n_all if total is None else max(0, min(total, n_all))
    # Bao nhiêu task lấy từ mỗi bucket (theo kích thước bucket) — largest-remainder.
    takes = _apportion(target, [len(by_diff[d]) for d in diffs])

    out: dict[str, list[str]] = {"train": [], "val": [], "test": []}
    for d, take in zip(diffs, takes):
        chosen = by_diff[d][:take]
        n_tr, n_va, n_te = _apportion(take, list(ratio))   # chia train/val/test trong bucket
        out["train"] += chosen[:n_tr]
        out["val"] += chosen[n_tr:n_tr + n_va]
        out["test"] += chosen[n_tr + n_va:n_tr + n_va + n_te]

    # Lưới an toàn: loop bắt buộc cần train & val non-empty. Nếu đã chọn >= 3 task mà
    # split nào rỗng → mượn 1 phần tử từ split LỚN NHẤT (tất định, vẫn rời rạc).
    if sum(len(v) for v in out.values()) >= 3:
        for need in ("train", "val", "test"):
            if not out[need]:
                donor = max(("train", "val", "test"), key=lambda k: len(out[k]))
                if len(out[donor]) >= 2:
                    out[need].append(out[donor].pop())
    return out


def write_manifests(splits: dict[str, list[str]], out_dir: Path) -> dict[str, Path]:
    """Ghi mỗi split thành 1 file <name>.txt (mỗi dòng 1 task-id) cho `--tasks-file`."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for name, ids in splits.items():
        p = out_dir / f"{name}.txt"
        p.write_text("\n".join(sorted(ids)) + "\n", encoding="utf-8")
        paths[name] = p
    return paths


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Generate stratified SkillOpt train/val/test splits.")
    ap.add_argument("--ratio", default="2:1:7", help="train:val:test (mặc định 2:1:7)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--total", type=int, default=None, help="cắt tổng số task (None = hết)")
    ap.add_argument("--out", type=Path, required=True, help="thư mục ghi train.txt/val.txt/test.txt")
    a = ap.parse_args()
    ratio = tuple(int(x) for x in a.ratio.split(":"))  # type: ignore[assignment]
    sp = make_splits(ratio=ratio, seed=a.seed, total=a.total)  # type: ignore[arg-type]
    paths = write_manifests(sp, a.out)
    for name in ("train", "val", "test"):
        print(f"{name:5s}: {len(sp[name]):4d} tasks -> {paths[name]}")
