#!/usr/bin/env bash
# #65 QA walkthrough — stream_encoding_issues 找 __main__ 從 tree.body 改成 ast.walk(bug fix)。
# 全程 xtrace,指令與輸出同一份。
#
# 用法:bash scripts/qa/65-walkthrough.sh "$(mktemp -d)/qa65"
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

echo "==== STEP 1b  self-check 真的咬得到本票的 mutation:副本裡把 ast.walk 改回 tree.body -> self-check 轉紅 ===="
grep -n 'ast.walk(tree) if isinstance(n, ast.If)' "$CP/scripts/validate.py"
sed -i 's|for n in ast.walk(tree) if isinstance(n, ast.If)|for n in tree.body if isinstance(n, ast.If)|' "$CP/scripts/validate.py"
grep -n 'for n in tree.body if isinstance' "$CP/scripts/validate.py"
set +e
python "$CP/scripts/validate.py" --self-check
echo "exit $?  <- 非 0 是要的:#65 的病一還原,self-check 就該紅"
set -e
# 還原副本,後面幾步要用乾淨的它
cp "$ROOT/scripts/validate.py" "$CP/scripts/validate.py"

echo "==== STEP 2  副本未動過 -> 綠(證明後面判紅的是 probe,不是副本壞了)===="
python "$CP/scripts/validate.py"

echo "==== STEP 3  票上的重現 scenario 原樣重跑:__main__ 縮排在 try 底下的裸 print ===="
cat > "$CP/scripts/_repro65.py" <<'PY'
import sys
try:
    if __name__ == "__main__":
        print("要開的票")
except Exception:
    pass
PY
set +e
python "$CP/scripts/validate.py"
echo "exit $?  <- 非 0 是要的:期望紅"
set -e
rm "$CP/scripts/_repro65.py"

echo "==== STEP 3b  票上第二條:if True 底下同理 ===="
cat > "$CP/scripts/_repro65b.py" <<'PY'
import sys
if True:
    if __name__ == "__main__":
        print("要開的票")
PY
set +e
python "$CP/scripts/validate.py"
echo "exit $?  <- 非 0 是要的:期望紅"
set -e
rm "$CP/scripts/_repro65b.py"

echo "==== STEP 4  同型全掃:__main__ 能被包在哪些 block 底下 × 裸 print / 有 pin 兩個方向 ===="
python "$ROOT/scripts/qa/65-nesting-sweep.py" "$ROOT"

echo "==== STEP 4b  對照組:同一份母體在 #65 修之前(3d402e9^)有幾條無聲過關 ===="
set +e
python "$ROOT/scripts/qa/65-nesting-sweep.py" "$ROOT" --old
echo "exit $?  <- 非 0 是預期的:證明這一整族都是這次修掉的"
set -e

echo "==== STEP 5  完工定義第二條:60-mention-sweep --skips 前兩條要變 ok ===="
set +e
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --skips
echo "exit $?  <- 非 0 是預期的:第三條(SyntaxError)是 #66,不在本票範圍"
set -e

echo "==== STEP 6  不得誤紅:#60 的全表與位置判準沒退步,#57 的對照組還咬得到 ===="
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --positional
python "$ROOT/scripts/qa/57-guard-sweep.py" "$ROOT"

echo "==== STEP 7  本輪 finding:一個檔有兩個 __main__ 時,守門只看 next() 找到的第一個 ===="
set +e
python "$ROOT/scripts/qa/65-nesting-sweep.py" "$ROOT" --decoy
echo "exit $?  <- 非 0:2 條期望紅、實際綠"
set -e

echo "==== STEP 7b  對照組:同樣 5 條在 #65 修之前(3d402e9^)壞 3 條 -> 這是舊天花板,#65 修好了 1 條 ===="
set +e
python "$ROOT/scripts/qa/65-nesting-sweep.py" "$ROOT" --decoy --old
echo "exit $?"
set -e

echo "==== STEP 7c  judge 追問:__main__ 判斷式換個等價寫法 -> 守門一樣找不到那個 node ===="
set +e
python "$ROOT/scripts/qa/65-nesting-sweep.py" "$ROOT" --test-form
echo "exit $?  <- 非 0:4 條期望紅、實際綠"
python "$ROOT/scripts/qa/65-nesting-sweep.py" "$ROOT" --test-form --old
echo "exit $?  <- 修之前壞同樣 4 條 -> 舊天花板,不是本輪 regression"
set -e

echo "==== STEP 7d  judge 追問:檔名過濾(擋 __pycache__ 用的)誤傷 package entry point __main__.py ===="
set +e
python "$ROOT/scripts/qa/65-nesting-sweep.py" "$ROOT" --filenames
echo "exit $?  <- 非 0:2 條期望紅、實際綠"
python "$ROOT/scripts/qa/65-nesting-sweep.py" "$ROOT" --filenames --old
echo "exit $?  <- 修之前一樣壞 -> 舊天花板"
set -e

echo "==== STEP 8  repo 本體沒被動過 ===="
python "$ROOT/scripts/validate.py"
git -C "$ROOT" status --short
