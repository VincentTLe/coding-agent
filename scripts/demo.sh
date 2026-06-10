#!/usr/bin/env bash
# Live demo, một lệnh duy nhất.
# Spec đưa vào, KHÔNG có test cho sẵn. Agent tự viết code VÀ tự viết cách kiểm tra rồi tự chạy.
# Đây mới đúng bản chất: nó giải từ mô tả như người, không nhìn test rồi chép đáp án.
#
#   bash scripts/demo.sh                 # mặc định: int_to_roman + roman_to_int, tự kiểm round-trip (đã test, đúng cả 1..3999)
#   bash scripts/demo.sh "your spec..."  # tự đặt bài bất kỳ
#
# Spec dự phòng đã test sẵn (đổi vào nếu muốn bài khác):
#   RLE round-trip (chỉ chữ cái): "Create rle.py with encode(s) doing run-length encoding (aaabbc -> a3b2c1) and decode(s) reversing it, for strings of lowercase letters. No tests. At the bottom, check decode(encode(s)) == s for 'aaabbc', 'xyz', and the empty string, print PASS or FAIL, and finish only when all pass."
#   wordfreq CLI: "Write wordfreq.py that reads a text file from sys.argv[1], counts word frequencies (lowercase, ignore punctuation), and prints the top 5 as 'word: count'. No tests. Create sample.txt, run it, and check the output before finishing."
set -euo pipefail
cd "$(dirname "$0")/.."

TASK="${1:-Create roman.py with two functions, int_to_roman(n) and roman_to_int(s), covering 1 to 3999. No tests are provided. At the bottom of the file, check the round trip: for n in [4, 9, 58, 1994, 3999] confirm that roman_to_int(int_to_roman(n)) equals n, print PASS or FAIL for each, and only call finish when they all pass.}"

WS="/tmp/agent_demo"
rm -rf "$WS" && mkdir -p "$WS"   # workspace rỗng, agent tự tạo mọi file (không cần copy repo)

# Kiểm vLLM trước để không chết giữa demo. Endpoint đọc từ .env (nguồn chân lý duy nhất
# cho port/model — đừng hardcode :8765/Qwen3-14B ở đây kẻo .env đổi là check nói dối).
# curl -f: HTTP lỗi (4xx/5xx) → exit khác 0; chỉ cần server trả lời được /models là đủ.
VLLM_BASE_URL="$(grep -m1 '^VLLM_BASE_URL=' .env 2>/dev/null | cut -d= -f2- || true)"
VLLM_BASE_URL="${VLLM_BASE_URL:-http://localhost:8765/v1}"
curl -sf --max-time 5 "$VLLM_BASE_URL/models" >/dev/null \
  || { echo "!! vLLM chưa chạy tại $VLLM_BASE_URL — bật: tmux attach -t vllm  (hoặc  bash scripts/start_vllm.sh)"; exit 1; }

echo ">>> SPEC: $TASK"
echo ">>> workspace rỗng: $WS"
echo
.venv/bin/python cli/solve.py "$TASK" --workspace "$WS" --max-iters 18
echo
echo ">>> file agent đã tạo:"; ls -1 "$WS"
