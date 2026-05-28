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
discover_tasks/read_meta/rel_id của eval harness (không tự đọc lại task.md).
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

from eval.run import TASKS_DIR, discover_tasks, read_meta, rel_id


def make_splits(ratio: tuple[int, int, int] = (2, 1, 7), seed: int = 42,
                total: int | None = None, tasks_root: Path | None = None) -> dict[str, list[str]]:
    """Chia task → {"train","val","test"} (rời nhau), phân tầng theo difficulty, tất định.

    ratio = (train, val, test). total = cắt tổng số task (None = dùng hết 627).
    """
    root = tasks_root or TASKS_DIR
    tasks = discover_tasks(root)

    # Gom task-id theo difficulty.
    by_diff: dict[str, list[str]] = {}
    for t in tasks:
        _, diff = read_meta(t)
        by_diff.setdefault((diff or "unknown").lower(), []).append(rel_id(t))

    rng = random.Random(seed)
    out: dict[str, list[str]] = {"train": [], "val": [], "test": []}
    r_sum = sum(ratio)
    n_all = sum(len(v) for v in by_diff.values())

    for diff in sorted(by_diff):
        ids = sorted(by_diff[diff])   # sắp xếp ổn định TRƯỚC khi shuffle (tái lập)
        rng.shuffle(ids)
        if total is not None:         # giữ tỉ lệ difficulty trong tổng đã cắt
            keep = max(3, round(total * len(ids) / n_all))
            ids = ids[:keep]
        n = len(ids)
        n_tr = n * ratio[0] // r_sum
        n_va = n * ratio[1] // r_sum
        out["train"] += ids[:n_tr]
        out["val"] += ids[n_tr:n_tr + n_va]
        out["test"] += ids[n_tr + n_va:]
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
