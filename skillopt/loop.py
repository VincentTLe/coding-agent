"""
skillopt/loop.py — the SkillOpt training loop (the "optimizer") + validation gate + CLI.

=== Giải thích ===
Đây là vòng lặp chính = "optimizer". Mỗi STEP:
  1. ROLLOUT: chạy agent với skill HIỆN TẠI trên split train (gọi eval/run.py).
  2. REFLECT: optimizer đọc ca fail/success → đề xuất edit (qua optimizer_llm).
  3. MERGE: gộp (ưu tiên failure).  4. CLIP: giới hạn L edit (learning rate).
  5. APPLY: áp edit → skill ỨNG VIÊN (giữ vùng protected).
  6. GATE: chấm ứng viên trên split val; CHẤP NHẬN chỉ khi điểm > hiện tại (chặt;
     hoà cũng loại). Tốt hơn best → ghi best_skill.md. Bị loại → vào rejected buffer.
Cuối mỗi EPOCH: so skill đầu-epoch vs cuối-epoch trên cùng 1 mẫu → 4 nhóm (cải thiện/
thụt lùi/fail dai dẳng/thành công ổn định) → 1 lần gọi optimizer → ghi "slow-update
field" (vùng protected) → cho qua gate. Checkpoint sau MỖI step (skill + trajectory.jsonl)
nên dừng đúng deadline vẫn ra trạng thái hợp lệ; rollout idempotent qua eval/run.py --resume.

Cache rollout theo (skill_hash, split): khi 1 ứng viên bị loại, skill hiện tại KHÔNG đổi,
nên rollout train ở step sau lấy lại từ cache (miễn phí). Đây là chốt tiết kiệm GPU lớn.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from skillopt import optimizer_llm as olm
from skillopt.skill import (
    apply_edits,
    ensure_slow_update_region,
    replace_slow_update_field,
    skill_hash,
)

REPO = Path(__file__).resolve().parent.parent


def _read_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    out: list[dict] = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        try:                       # bỏ qua dòng cuối bị cắt dở (rollout bị kill giữa chừng)
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return out


def _cases(results: list[dict]) -> list[dict]:
    """Rút gọn kết quả eval thành 'ca' cho optimizer đọc."""
    out = []
    for r in results:
        out.append({"task": r.get("task"), "passed": bool(r.get("passed")),
                    "finish_reason": r.get("finish_reason"),
                    "summary": f"finish_reason={r.get('finish_reason')}; "
                               f"pytest: {(r.get('pytest_tail') or '')[-300:]}"})
    return out


def _rollout(skill_text: str | None, split_name: str, tasks_file: Path, *, jobs: int,
             scratch: Path, cache: dict, agent_timeout: float | None = 420) -> tuple[float | None, list[dict]]:
    """Chạy agent với skill_text trên split → (pass_rate, cases). Cache theo (hash, split).

    pass_rate = None nghĩa là ROLLOUT HỎNG vì hạ tầng (timeout / subprocess chết / thiếu
    task) — KHÁC với 0.0 (điểm 0% thật). Caller PHẢI kiểm None để không gate bằng điểm ảo.

    agent_timeout: trần wall-clock MỖI task (giây) → chặn task kẹt ăn hết thời gian của
    run dài không người trông. Mặc định 420s (probe thấy task nặng nhất ~258s → còn dư).
    """
    key = (skill_hash(skill_text) if skill_text else "EMPTY", split_name)
    if key in cache:
        return cache[key]
    cmd = [sys.executable, "eval/run.py", "--tasks-file", str(tasks_file),
           "--jobs", str(jobs), "--temperature", "0", "--resume"]
    if agent_timeout:
        cmd += ["--agent-timeout", str(agent_timeout)]
    out = scratch / f"{split_name}_{key[0]}.jsonl"
    cmd += ["--out", str(out)]
    if skill_text is not None:
        skill_file = scratch / f"skill_{key[0]}.md"
        skill_file.write_text(skill_text, encoding="utf-8")
        cmd += ["--skill-path", str(skill_file)]
    # Trần wall-clock cho CẢ subprocess (chống vLLM/queue/pool deadlock): scale theo
    # số task + jobs. Khác với --agent-timeout (chỉ trần MỖI task) — đây trần cả lần gọi.
    try:
        n_tasks = sum(1 for ln in tasks_file.read_text(encoding="utf-8").splitlines() if ln.strip())
    except Exception:
        n_tasks = 16
    sub_timeout = (agent_timeout or 420) * max(1, (n_tasks + jobs - 1) // max(1, jobs)) + 600
    try:
        subprocess.run(cmd, cwd=REPO, check=False, timeout=sub_timeout)
    except subprocess.TimeoutExpired:
        # subprocess hang → KHÔNG cache (để lần sau thử lại). Trả score=None (LỖI HẠ TẦNG),
        # KHÔNG phải 0.0 — để caller phân biệt "rollout hỏng" với "điểm 0% thật" và không
        # đầu độc gate bằng baseline/candidate ảo.
        return None, []
    results = _read_jsonl(out)
    n_done = len({r.get("task") for r in results})
    if not results or n_done < n_tasks:
        # Rỗng HOẶC THIẾU task: subprocess chết giữa chừng nhưng KHÔNG qua TimeoutExpired
        # (OOM/SIGKILL/host crash → run trả về với check=False). Chấm trên tập con cho ra
        # score sai. Trả None (lỗi hạ tầng), KHÔNG cache, KHÔNG chấm → caller xử lý.
        return None, []
    score = sum(1 for r in results if r.get("passed")) / len(results)
    cases = _cases(results)
    cache[key] = (score, cases)
    return score, cases


def _format_rejected(buffer: list[dict]) -> str:
    """Tóm tắt buffer edit bị loại để optimizer khỏi đề xuất lại."""
    return "\n".join(f"- (Δ={b['drop']:+.3f}) {json.dumps(b['edits'], ensure_ascii=False)[:300]}"
                     for b in buffer[-6:])


def _slow_update(prev_skill: str, curr_skill: str, sample_file: Path, *, jobs: int,
                 scratch: Path, cache: dict) -> str:
    """Ranh giới epoch: so prev vs curr trên train → 4 nhóm → nội dung slow-update.

    Dùng split_name "train" để TÁI DÙNG cache rollout của các step (prev/curr skill hầu
    như đã được chấm trên train rồi) → slow-update gần như miễn phí, không re-roll thừa.
    """
    _, prev_cases = _rollout(prev_skill, "train", sample_file, jobs=jobs, scratch=scratch, cache=cache)
    _, curr_cases = _rollout(curr_skill, "train", sample_file, jobs=jobs, scratch=scratch, cache=cache)
    pp = {c["task"]: c["passed"] for c in prev_cases}
    buckets = {"regressed": [], "persistent_fail": [], "improved": [], "stable_success": []}
    for c in curr_cases:
        prev_ok, curr_ok = pp.get(c["task"], False), c["passed"]
        key = ("stable_success" if prev_ok and curr_ok else "improved" if curr_ok else
               "regressed" if prev_ok else "persistent_fail")
        buckets[key].append(c["task"])
    summary = "; ".join(f"{k}={len(v)}" for k, v in buckets.items())
    user = (f"CURRENT SKILL:\n{curr_skill}\n\nAcross this epoch, comparing previous vs current "
            f"skill on the same tasks: {summary}. REGRESSIONS are highest priority. Write a SHORT "
            f"'executive strategy' block (durable, long-horizon guidance) to stabilize the skill — "
            f"prose only, no edit JSON.")
    content = olm._call("You write SkillOpt's epoch-level executive-strategy field.", user,
                        max_tokens=512) or summary
    return content.strip()


def optimize(seed_path: Path, splits_dir: Path, run_dir: Path, *, epochs: int, steps: int,
             L: int, jobs: int, slow_samples: int,
             max_minutes: float | None = None, smoke: bool = False) -> dict:
    """Chạy vòng lặp SkillOpt. Trả summary + ghi best_skill.md + trajectory.jsonl.

    max_minutes: ngân sách wall-clock — chạm ngưỡng thì DỪNG SẠCH ở ranh giới step (đã
    checkpoint best_skill.md + trajectory.jsonl sau mỗi step), summary có stopped_early=True.
    smoke: cấu hình nhanh (1 epoch / 1 step / slow_samples=2) để verify end-to-end.
    """
    if smoke:
        epochs, steps, slow_samples = 1, 1, 2
    run_dir.mkdir(parents=True, exist_ok=True)
    deadline = (time.monotonic() + max_minutes * 60) if max_minutes else None
    scratch = REPO / "eval" / "results" / "skillopt" / run_dir.name
    scratch.mkdir(parents=True, exist_ok=True)
    train_f, val_f = splits_dir / "train.txt", splits_dir / "val.txt"
    cache: dict = {}

    current = ensure_slow_update_region(seed_path.read_text(encoding="utf-8"))
    current_score, _ = _rollout(current, "val", val_f, jobs=jobs, scratch=scratch, cache=cache)
    if current_score is None:
        # Seed/baseline rollout HỎNG (hạ tầng) → KHÔNG được tiếp tục với baseline ảo 0.0
        # (sẽ auto-accept candidate đầu + báo lift ảo). Dừng rõ ràng để người dùng sửa hạ
        # tầng (vLLM/eval) rồi chạy lại.
        raise RuntimeError("SkillOpt: seed/baseline val rollout failed (infra error: timeout/"
                           "incomplete). Aborting — kiểm tra vLLM/eval rồi chạy lại, không tối "
                           "ưu trên baseline ảo.")
    seed_score = current_score          # điểm seed GỐC (current_score bị ghi đè khi accept)
    best, best_score = current, current_score
    (run_dir / "best_skill.md").write_text(best, encoding="utf-8")
    traj_f = run_dir / "trajectory.jsonl"
    traj_f.write_text("", encoding="utf-8")

    def log(rec: dict):
        with traj_f.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    log({"event": "init", "seed_val_score": seed_score, "best_score": best_score})

    stopped = False
    for epoch in range(epochs):
        if stopped:
            break
        epoch_start_skill = current
        rejected: list[dict] = []   # buffer reset mỗi epoch
        for step in range(steps):
            if deadline and time.monotonic() > deadline:   # hết ngân sách → dừng SẠCH
                log({"event": "stopped", "reason": "max_minutes", "epoch": epoch, "step": step})
                stopped = True
                break
            tr_score, cases = _rollout(current, "train", train_f, jobs=jobs, scratch=scratch, cache=cache)
            if tr_score is None:               # train rollout hỏng → không có tín hiệu, bỏ step
                log({"event": "rollout_failed", "epoch": epoch, "step": step, "phase": "train"})
                continue
            fails = [c for c in cases if not c["passed"]]
            succ = [c for c in cases if c["passed"]]
            fe = olm.reflect(current, fails, "failure", _format_rejected(rejected), L)
            se = olm.reflect(current, succ, "success", "", L)
            clipped = olm.clip(current, olm.merge(current, fe, se), L)
            opt_calls = olm.drain_trace()      # AUDITABILITY: response thô của optimizer step này
            cand, reports = apply_edits(current, clipped)
            cand_score, _ = _rollout(cand, "val", val_f, jobs=jobs, scratch=scratch, cache=cache)
            if cand_score is None:             # val rollout hỏng → KHÔNG gate trên điểm ảo
                log({"event": "rollout_failed", "epoch": epoch, "step": step,
                     "phase": "val_candidate", "n_edits": len(clipped), "edits": clipped,
                     "optimizer_calls": opt_calls})
                continue

            decision = "reject"
            if cand_score > current_score:           # strict >, ties reject
                current, current_score, decision = cand, cand_score, "accept"
                if cand_score > best_score:
                    best, best_score, decision = cand, cand_score, "accept_new_best"
                    (run_dir / "best_skill.md").write_text(best, encoding="utf-8")
            else:
                rejected.append({"edits": clipped, "drop": cand_score - current_score})

            # AUDITABILITY: log NỘI DUNG edit (không chỉ n_edits) + snapshot skill ứng viên
            # mỗi step → tái dựng được "luật học từ đâu" và diff từng bước (audit HIGH).
            log({"event": "step", "epoch": epoch, "step": step, "train_score": tr_score,
                 "cand_score": cand_score, "current_score": current_score, "best_score": best_score,
                 "decision": decision, "n_edits": len(clipped), "edits": clipped,
                 "edit_reports": reports, "optimizer_calls": opt_calls})
            steps_dir = run_dir / "steps"
            steps_dir.mkdir(exist_ok=True)
            (steps_dir / f"e{epoch}_s{step}_{decision}.md").write_text(cand, encoding="utf-8")
            (run_dir / "current_skill.md").write_text(current, encoding="utf-8")

        # --- epoch boundary: slow / executive-strategy update (≥ epoch 1 meaningful) ---
        # Bỏ qua nếu vừa dừng giữa epoch vì hết ngân sách (khỏi chạy thêm rollout).
        if not stopped and (epoch >= 1 or epochs == 1):
            if deadline and time.monotonic() > deadline:
                # Hết ngân sách ngay trước slow-update → KHÔNG chạy thêm rollout, dừng SẠCH.
                stopped = True
                log({"event": "stopped", "reason": "max_minutes_at_epoch_boundary", "epoch": epoch})
            else:
                try:
                    slow = _slow_update(epoch_start_skill, current, train_f, jobs=jobs,
                                        scratch=scratch, cache=cache)
                    slow_calls = olm.drain_trace()   # drain NGAY (không để step epoch sau dính trace cũ — Codex #8)
                    cand = replace_slow_update_field(current, slow)
                    cand_score, _ = _rollout(cand, "val", val_f, jobs=jobs, scratch=scratch, cache=cache)
                    if cand_score is None:       # rollout hỏng → bỏ slow-update, giữ current
                        log({"event": "slow_update", "epoch": epoch, "cand_score": None,
                             "accepted": False, "reason": "rollout_failed", "optimizer_calls": slow_calls})
                    else:
                        accepted = cand_score >= current_score   # slow-update: không tệ đi thì giữ
                        if accepted:
                            current, current_score = cand, cand_score
                            if cand_score > best_score:
                                best, best_score = cand, cand_score
                                (run_dir / "best_skill.md").write_text(best, encoding="utf-8")
                        log({"event": "slow_update", "epoch": epoch, "cand_score": cand_score,
                             "accepted": accepted, "slow_field": slow[:300], "optimizer_calls": slow_calls})
                except Exception as e:  # noqa: BLE001 — slow-update KHÔNG được giết run dài
                    log({"event": "slow_update_error", "epoch": epoch, "error": repr(e)[:300]})

    summary = {"epochs": epochs, "steps_per_epoch": steps, "L": L, "jobs": jobs,
               "seed_val_score": seed_score, "best_val_score": best_score,
               "stopped_early": stopped, "best_skill": str(run_dir / "best_skill.md")}
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    log({"event": "done", **summary})
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Run the SkillOpt optimization loop (needs vLLM up).")
    ap.add_argument("--seed", type=Path, required=True, help="seed skill .md")
    ap.add_argument("--splits", type=Path, required=True, help="dir with train.txt/val.txt/test.txt")
    ap.add_argument("--run-dir", type=Path, required=True, help="output dir (skillopt/runs/<id>/)")
    ap.add_argument("--epochs", type=int, default=4)
    ap.add_argument("--steps", type=int, default=3, help="steps per epoch")
    ap.add_argument("--L", type=int, default=4, help="edit budget (textual learning rate)")
    ap.add_argument("--jobs", type=int, default=8, help="parallel rollouts (set to vLLM-saturating value)")
    ap.add_argument("--slow-samples", type=int, default=16)
    ap.add_argument("--max-minutes", type=float, default=None,
                    help="ngân sách wall-clock: chạm ngưỡng thì dừng sạch ở ranh giới step")
    ap.add_argument("--smoke", action="store_true",
                    help="cấu hình nhanh (1 epoch/1 step/slow_samples=2) verify end-to-end")
    a = ap.parse_args()
    s = optimize(a.seed, a.splits, a.run_dir, epochs=a.epochs, steps=a.steps, L=a.L,
                 jobs=a.jobs, slow_samples=a.slow_samples,
                 max_minutes=a.max_minutes, smoke=a.smoke)
    print(json.dumps(s, indent=2))
