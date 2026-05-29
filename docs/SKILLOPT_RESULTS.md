# SkillOpt results (held-out test split)

Báo cáo trên TEST (chấm 1 lần). Tối ưu chỉ dùng train+val.

| arm | pass@1 | k/n | Wilson 95% CI |
|---|---|---|---|
| empty | 0.786 | 66/84 | [0.687, 0.860] |
| seed | 0.738 | 62/84 | [0.635, 0.820] |
| optimized | 0.774 | 65/84 | [0.674, 0.850] |

## pass@1 theo difficulty
| difficulty | empty | seed | optimized |
|---|---|---|---|
| easy | 26/28 (0.93) | 24/28 (0.86) | 25/28 (0.89) |
| hard | 19/27 (0.70) | 18/27 (0.67) | 18/27 (0.67) |
| medium | 21/29 (0.72) | 20/29 (0.69) | 22/29 (0.76) |

## Paired McNemar vs optimized (exact binomial)
- optimized vs empty: 1 tasks improved, 2 regressed (n_discordant=3, exact-binomial p=1.000)
- optimized vs seed: 5 tasks improved, 2 regressed (n_discordant=7, exact-binomial p=0.453)

## Run-to-run instability (empty chạy lại cùng config)
- empty#1 0.786 (66/84) vs empty#2 0.738 (62/84): **6 task lật** chỉ do phi tất định (vLLM batching ở temp=0 KHÔNG tất định). ⚠️ Đây là MỘT lần đo (1 draw) — chỉ ƯỚC LƯỢNG độ bất ổn run-to-run, KHÔNG phải 'sàn nhiễu' chính thức (Codex methodology review).
- So flips giữa arm: empty–seed=8, empty–optimized=3, seed–optimized=7. Khác biệt lớn nhất (8) chỉ sát mức bất ổn (6) → vẫn nên coi là chưa kết luận; cần nhiều run/arm để chắc.

## Mechanism check (optimized vs điểm xuất phát seed)
- val: seed 0.667 → best 0.750 (Δ=+0.083) — ⚠️ |val| rất nhỏ (xem manifest, ở run này = 12 task → 1 task ≈ 0.083); nên tín hiệu val chỉ là VÀI task, không phải bằng chứng mạnh.
- test: seed 0.738 → optimized 0.774 (Δ=+0.036; 5 task tốt lên, 2 task tệ đi trên |test|=84, McNemar p=0.453); chiều DƯƠNG (optimized > seed), **KHÔNG đạt p<0.05 → nằm trong nhiễu**, CHƯA thể khẳng định edit 'transfer' (tín hiệu hướng yếu, không ý nghĩa thống kê).

## Overfit meter
- best val (train-side) 0.750; optimized test 0.774; gap = -0.024 (lớn dương = nghi học vẹt trên val).

## Verdict (tự động)
- **INCONCLUSIVE (under-powered).** Khác biệt giữa arm (empty↔optimized=3, empty↔seed=8, seed↔optimized=7) CÙNG CỠ với độ bất ổn run-to-run (empty chạy lại lật 6 task), và KHÔNG McNemar exact nào đạt p<0.05. Point-estimate (empty 0.786 / seed 0.738 / optimized 0.774) là 1 mẫu nhiễu/arm ở N=84. **Không có bằng chứng tin cậy rằng skill (seed hay optimized) giúp HAY hại** — khác biệt quan sát nhỏ hơn hoặc ngang mức bất ổn đo được. Đây là kết luận trung thực; muốn quyết: ≥3–5 run/arm (trung bình) hoặc N test lớn hơn nhiều. (Lưu ý: 'mức bất ổn' là heuristic 1-lần-đo, không phải test thống kê — xem McNemar exact ở trên.)
