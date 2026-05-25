"""
eval/convert_benchmark.py — Tải HumanEval+ & (sanitized) MBPP về và biến mỗi bài
thành 1 task dir theo đúng format harness (task.md + stub .py + test_*.py), kèm
1 file lời giải tham chiếu trong cây song song eval/solutions/ (KHÔNG nằm trong
workspace agent → agent không nhìn thấy).

Vì sao 2 nguồn này:
  - HumanEval+ (evalplus/humanevalplus, HF dataset): 164 bài, field `test` là 1
    module tự chứa định nghĩa check(candidate) với toàn bộ test "+" đã hardcode
    → TÁI SỬ DỤNG NGUYÊN VĂN, không cần trích input hay chạy lời giải.
  - MBPP sanitized (google-research, GitHub raw JSON): 427 bài đã được người
    kiểm, mỗi bài có `test_list` (các assert) + `test_imports` → ghép thẳng.
  Không cần `datasets`/`evalplus`/`pyarrow` — chỉ `huggingface_hub` + `requests`
  (đã có sẵn). MBPP+ chỉ phát hành parquet nên ta dùng MBPP canonical thay thế.

Cách dùng:
    python eval/convert_benchmark.py                 # cả 2 nguồn
    python eval/convert_benchmark.py --only he       # chỉ HumanEval+
    python eval/convert_benchmark.py --mbpp-limit 100

Sau khi chạy, LUÔN chạy eval/validate_tasks.py để loại bài convert hỏng (gate:
lời giải tham chiếu phải PASS, stub phải FAIL).
"""

from __future__ import annotations

import argparse
import ast
import gzip
import json
import re
import sys
from pathlib import Path

import requests
from huggingface_hub import hf_hub_download, list_repo_files

ROOT = Path(__file__).resolve().parent.parent
BENCH_TASKS = ROOT / "eval" / "tasks" / "bench"
BENCH_SOLS = ROOT / "eval" / "solutions" / "bench"
CACHE = ROOT / "eval" / ".cache"

MBPP_URL = ("https://raw.githubusercontent.com/google-research/google-research/"
            "master/mbpp/sanitized-mbpp.json")


# ---------------------------------------------------------------------------
# PHÂN LOẠI category / difficulty (heuristic, chỉ để gộp nhóm — không chấm điểm)
# ---------------------------------------------------------------------------

def _is_recursive(tree: ast.AST) -> bool:
    defs = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in defs:
            return True
    return False


def _loop_depth(node: ast.AST, d: int = 0) -> int:
    best = d
    for ch in ast.iter_child_nodes(node):
        nd = d + (1 if isinstance(ch, (ast.For, ast.While)) else 0)
        best = max(best, _loop_depth(ch, nd))
    return best


def classify_difficulty(src: str) -> str:
    """easy/medium/hard từ HÌNH DÁNG lời giải tham chiếu (số dòng, lồng vòng lặp,
    đệ quy). Không hoàn hảo nhưng đủ để xếp thang dễ→khó."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return "medium"
    nloc = len([ln for ln in src.splitlines()
                if ln.strip() and not ln.strip().startswith("#")])
    if _is_recursive(tree) or _loop_depth(tree) >= 2 or nloc > 14:
        return "hard"
    if any(isinstance(n, (ast.For, ast.While)) for n in ast.walk(tree)) or nloc >= 5:
        return "medium"
    return "easy"


def classify_category(prompt: str, src: str) -> str:
    blob = (prompt + "\n" + src).lower()
    try:
        tree = ast.parse(src)
        if _is_recursive(tree):
            return "recursion"
        if any(isinstance(n, ast.ClassDef) for n in ast.walk(tree)):
            return "oop"
    except SyntaxError:
        pass
    if "import re" in blob or re.search(r"\bre\.", blob):
        return "regex"
    if any(k in blob for k in ("collections", "defaultdict", "counter", "dict(", "{}", " set(")):
        return "data_structures"
    if any(k in blob for k in (".join", ".split", "lower()", "upper()", "char", "string", "vowel", "palindrome")):
        return "strings"
    if any(k in blob for k in ("prime", "factor", "fibonacci", "math.", "divisor", "gcd", "modulo", "%")):
        return "math"
    if any(k in blob for k in ("sort", "range(len", "[i]", "index", "list(", "array", "subarray")):
        return "arrays"
    return "algorithms"


# ---------------------------------------------------------------------------
# GHI 1 TASK DIR
# ---------------------------------------------------------------------------

def write_task(tid: str, module: str, stub: str, test_src: str, reference: str,
               goal: str, category: str, difficulty: str, source_note: str,
               hide_tests: bool = True) -> None:
    """Tạo eval/tasks/bench/<tid>/ {module.py, test_module.py, task.md} +
    eval/solutions/bench/<tid>/<module>.py (lời giải tham chiếu, ngoài workspace).

    hide_tests=True (mặc định cho benchmark): ghi '## Tests: hidden' → harness giấu
    file test khỏi agent (đo implement-từ-spec trung thực, chống hard-code)."""
    tdir = BENCH_TASKS / tid
    sdir = BENCH_SOLS / tid
    tdir.mkdir(parents=True, exist_ok=True)
    sdir.mkdir(parents=True, exist_ok=True)
    (tdir / f"{module}.py").write_text(stub, encoding="utf-8")
    (tdir / f"test_{module}.py").write_text(test_src, encoding="utf-8")
    (tdir / "task.md").write_text(
        f"# {tid} — {module}\n\n"
        f"## Goal\n{goal}\n\n"
        f"## Category\n{category}\n\n"
        f"## Difficulty\n{difficulty}\n\n"
        f"## Tests\n{'hidden' if hide_tests else 'visible'}\n\n"
        f"## Source/License\n{source_note}\n",
        encoding="utf-8",
    )
    (sdir / f"{module}.py").write_text(reference, encoding="utf-8")


# ---------------------------------------------------------------------------
# HUMANEVAL+  (evalplus/humanevalplus trên HF)
# ---------------------------------------------------------------------------

def load_humaneval_plus() -> list[dict]:
    files = list_repo_files("evalplus/humanevalplus", repo_type="dataset")
    jsonl = sorted(f for f in files if f.endswith(".jsonl"))
    if not jsonl:
        raise RuntimeError(f"No .jsonl in evalplus/humanevalplus (files={files})")
    path = hf_hub_download("evalplus/humanevalplus", jsonl[-1], repo_type="dataset",
                           cache_dir=str(CACHE))
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as f:
        recs = [json.loads(ln) for ln in f if ln.strip()]
    print(f"[HE+] resolved {jsonl[-1]} — {len(recs)} records")
    return recs


def emit_humaneval(rec: dict) -> bool:
    """1 bài HumanEval+ → task dir. Tái sử dụng `test` NGUYÊN VĂN (đã chứa
    check(candidate) + toàn bộ ca test '+'). Trả True nếu ghi thành công."""
    try:
        num = rec["task_id"].split("/")[1]
        tid = f"he_{int(num):03d}"
        entry = rec["entry_point"]
        prompt = rec["prompt"]
        canonical = rec["canonical_solution"]
        test = rec["test"]
    except (KeyError, IndexError, ValueError) as e:
        print(f"[HE+] skip malformed record: {e!r}")
        return False

    # Stub: prompt (import + signature + docstring) rồi body báo chưa làm.
    stub = prompt.rstrip("\n") + "\n    raise NotImplementedError\n"
    # Lời giải tham chiếu = prompt + canonical_solution (đúng như HumanEval ghép).
    reference = prompt + canonical
    # Test file: import hàm từ module rồi gọi check() có sẵn của EvalPlus.
    test_src = (
        f"from {entry} import {entry}\n"
        f"{test}\n\n"
        f"def test_humaneval_plus():\n"
        f"    check({entry})\n"
    )
    goal = prompt.strip() + f"\n\nImplement `{entry}` in `{entry}.py` so all tests pass."
    cat = classify_category(prompt, reference)
    dif = classify_difficulty(reference)
    write_task(tid, entry, stub, test_src, reference, goal, cat, dif,
               f"{rec['task_id']} via EvalPlus (HumanEval+). HumanEval: MIT; "
               f"EvalPlus augmented tests: Apache-2.0.")
    return True


# ---------------------------------------------------------------------------
# MBPP sanitized  (GitHub raw JSON array)
# ---------------------------------------------------------------------------

def load_mbpp() -> list[dict]:
    CACHE.mkdir(parents=True, exist_ok=True)
    cached = CACHE / "sanitized-mbpp.json"
    if cached.exists():
        data = json.loads(cached.read_text(encoding="utf-8"))
    else:
        r = requests.get(MBPP_URL, timeout=30)
        r.raise_for_status()
        cached.write_text(r.text, encoding="utf-8")
        data = r.json()
    print(f"[MBPP] sanitized-mbpp.json — {len(data)} records")
    return data


def _mbpp_entry(code: str, test_list: list[str]) -> str | None:
    """Tên hàm cần implement = hàm có def trong code VÀ được gọi trong test_list."""
    called: set[str] = set()
    for t in test_list:
        called.update(re.findall(r"([A-Za-z_]\w*)\s*\(", t))
    try:
        defs = [n.name for n in ast.walk(ast.parse(code)) if isinstance(n, ast.FunctionDef)]
    except SyntaxError:
        return None
    for d in defs:
        if d in called:
            return d
    return defs[0] if defs else None


def emit_mbpp(rec: dict) -> bool:
    try:
        task_id = rec["task_id"]
        code = rec["code"]
        text = rec.get("prompt") or rec.get("text") or "Implement the function described by the tests."
        test_list = rec["test_list"]
        test_imports = rec.get("test_imports", []) or []
    except KeyError as e:
        print(f"[MBPP] skip malformed record: {e!r}")
        return False

    entry = _mbpp_entry(code, test_list)
    if not entry:
        print(f"[MBPP] skip {task_id}: no entry function found")
        return False
    try:
        tree = ast.parse(code)
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == entry)
        sig = ast.unparse(fn.args)
    except (SyntaxError, StopIteration):
        print(f"[MBPP] skip {task_id}: cannot parse signature")
        return False

    tid = f"mbpp_{int(task_id):03d}"
    stub = (f"def {entry}({sig}):\n"
            f'    """See task.md for the spec."""\n'
            f"    raise NotImplementedError\n")
    reference = code if code.endswith("\n") else code + "\n"
    # Test: import lời giải (import * để bắt cả hàm phụ nếu có), ghép import phụ,
    # rồi chạy mọi assert của MBPP trong 1 test.
    imports = "\n".join(test_imports)
    asserts = "\n".join("    " + a.strip() for a in test_list)
    test_src = (f"from {entry} import *\n"
                f"{imports}\n\n"
                f"def test_mbpp():\n{asserts}\n")
    examples = "\n".join(test_list[:2])
    goal = (f"{text.strip()}\n\nImplement `{entry}` in `{entry}.py` so the tests pass. "
            f"Example checks:\n{examples}")
    cat = classify_category(text, reference)
    dif = classify_difficulty(reference)
    write_task(tid, entry, stub, test_src, reference, goal, cat, dif,
               f"MBPP sanitized task {task_id}. MBPP: CC-BY-4.0.")
    return True


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Convert HumanEval+/MBPP into eval task dirs.")
    ap.add_argument("--only", choices=["he", "mbpp"], help="chỉ convert 1 nguồn")
    ap.add_argument("--mbpp-limit", type=int, default=None, help="giới hạn số bài MBPP")
    ap.add_argument("--he-limit", type=int, default=None, help="giới hạn số bài HumanEval+")
    args = ap.parse_args()

    BENCH_TASKS.mkdir(parents=True, exist_ok=True)
    BENCH_SOLS.mkdir(parents=True, exist_ok=True)

    n_he = n_mbpp = 0
    if args.only != "mbpp":
        recs = load_humaneval_plus()
        if args.he_limit:
            recs = recs[:args.he_limit]
        n_he = sum(emit_humaneval(r) for r in recs)
        print(f"[HE+] wrote {n_he}/{len(recs)} tasks")
    if args.only != "he":
        recs = load_mbpp()
        if args.mbpp_limit:
            recs = recs[:args.mbpp_limit]
        n_mbpp = sum(emit_mbpp(r) for r in recs)
        print(f"[MBPP] wrote {n_mbpp}/{len(recs)} tasks")

    print(f"\nTotal benchmark tasks written: {n_he + n_mbpp}  "
          f"(he={n_he}, mbpp={n_mbpp}) → {BENCH_TASKS}")
    print("NEXT: python eval/validate_tasks.py --filter bench --jobs 16  "
          "(prunes any task whose reference fails or stub passes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
