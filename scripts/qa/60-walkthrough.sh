#!/usr/bin/env bash
# #60 QA walkthrough — stream_encoding_issues 的豁免從全檔 substring 改成 AST 判準(bug fix)。
# 全程 xtrace,指令與輸出同一份。
#
# 用法:bash scripts/qa/60-walkthrough.sh "$(mktemp -d)/qa60"
# 這支不寫任何東西到 GitHub,也不碰 repo 本體 — mutation 全部跑在拋棄式暫存目錄的副本上。
set -e
PS4='+ '
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
QA="$1"
rm -rf "$QA"
mkdir -p "$QA"
CP="$QA/repo"
mkdir -p "$CP"
cp -r "$ROOT/scripts" "$ROOT/skills" "$ROOT/docs" "$CP/"
set -x

echo "==== STEP 1  regression suite(validate + 五支 self-check)===="
python "$ROOT/scripts/validate.py"
python "$ROOT/scripts/validate.py" --self-check
python "$ROOT/scripts/batch.py" --self-check
python "$ROOT/skills/build-batch/batch.py" --self-check
python "$ROOT/scripts/install.py" --self-check
python "$ROOT/scripts/hooks/triage-to-maintain.py" --self-check

echo "==== STEP 1b  self-check 真的咬得到「散文當 code」:副本裡把豁免改回 substring -> self-check 轉紅 ===="
grep -n 'norm(bypass) in whole' "$CP/scripts/validate.py"
sed -i 's|if norm(bypass) in whole or|if bypass in py.read_text(encoding="utf-8") or|' "$CP/scripts/validate.py"
grep -n 'bypass in py.read_text' "$CP/scripts/validate.py"
set +e
python "$CP/scripts/validate.py" --self-check
echo "exit $?  <- 非 0 是要的:#60 的病一還原,self-check 就該紅"
set -e
# 還原副本,後面幾步要用乾淨的它
cp "$ROOT/scripts/validate.py" "$CP/scripts/validate.py"

echo "==== STEP 2  副本未動過 -> 綠(證明後面判紅的是 mutation,不是副本壞了)===="
python "$CP/scripts/validate.py"

echo "==== STEP 3  票上的重現 scenario 原樣重跑:裸 print + 一行「沒走 sys.stdout.buffer」註解 ===="
cat > "$CP/scripts/_repro60.py" <<'PY'
if __name__ == "__main__":
    print("要開的票")
    # 這裡沒走 sys.stdout.buffer
PY
set +e
python "$CP/scripts/validate.py"
echo "exit $?"
set -e
rm "$CP/scripts/_repro60.py"

echo "==== STEP 4  同型全掃:「提到」的所有寫法 vs 「用到」的所有寫法 ===="
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT"

echo "==== STEP 5  不得誤紅:真的走 buffer 的 triage-to-maintain.py 仍被豁免 ===="
grep -n 'sys.stdout.buffer' "$ROOT/scripts/hooks/triage-to-maintain.py"
python - "$ROOT" <<'PY'
import sys, pathlib
sys.path.insert(0, sys.argv[1] + "/scripts")
sys.stdout.reconfigure(encoding="utf-8")
import validate as V
repo = pathlib.Path(sys.argv[1])
errs = [e for e in V.stream_encoding_issues(repo) if "triage-to-maintain" in e]
print("triage-to-maintain.py 的 error 數 ->", len(errs))
assert errs == []
PY

echo "==== STEP 6  #58 的原病沒退步:pin 放在 main() 而不是 __main__ block -> 仍判紅 ===="
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --positional

echo "==== STEP 6b  本輪抓到的:守門靜默跳過的兩條路(期望紅、實際綠)===="
set +e
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --skips
echo "exit $?  <- 非 0 是預期的,這三條是本輪 QA 的 finding,不是 AC"
set -e

echo "==== STEP 6c  對照組:同樣兩個 case 在改之前(d3cc9ed^)是判紅的 ===="
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --skips --old

echo "==== STEP 7  repo 本體沒被動過 ===="
python "$ROOT/scripts/validate.py"
git -C "$ROOT" status --short
