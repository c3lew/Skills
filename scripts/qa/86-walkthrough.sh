#!/usr/bin/env bash
# #86 QA walkthrough — deferred 邊界補上 generator 那面。
# 範圍 = #86 的重現 scenario + 既有 regression suite + 拿修法自己的三把尺做的同型全掃。
# 全程 xtrace,指令與輸出同一份。
#
# 用法:bash scripts/qa/86-walkthrough.sh "$(mktemp -d)/qa86"
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

echo "==== STEP 2  #86 的重現 scenario 原樣重跑(票上的母體 12,修前 6 誤放)===="
python "$ROOT/scripts/qa/84-generator-sweep.py" "$ROOT" --generator

echo "==== STEP 3  對照組:#86 修之前(cb7e030)同一組 12 條裡 6 條誤放 ===="
set +e
python "$ROOT/scripts/qa/84-generator-sweep.py" "$ROOT" --generator --prev86
echo "exit $?  <- 非 0 是要的:對照組該紅"
set -e

echo "==== STEP 4  票上宣稱的 mutation 咬合:十四個 knob 逐一改壞 -> self-check 要轉紅 ===="
for M in names_in_no_gen_stop names_in_no_first_iter nodes_in_no_gen_stop \
         nodes_in_no_first_iter consumes_no_builtins consumes_no_for \
         consumes_no_nested_gen consumes_no_comp consumes_no_shadow \
         gens_not_subtracted no_eaten_calls no_eaten_via_name \
         through_no_gens no_gen_fixpoint; do
  echo "---- 4.$M"
  cp "$ROOT/scripts/validate.py" "$CP/scripts/validate.py"
  python "$ROOT/scripts/qa/86-mutate.py" "$CP" "$M"
  set +e
  python "$CP/scripts/validate.py" --self-check 2>&1 | tail -18
  echo "exit ${PIPESTATUS[0]}  <- 非 0 是要的:knob 一改壞,self-check 就該紅"
  set -e
done

echo "==== STEP 5  副本還原後 -> 綠(證明上面判紅的是 mutation,不是副本壞了)===="
cp "$ROOT/scripts/validate.py" "$CP/scripts/validate.py"
python "$CP/scripts/validate.py" --self-check

echo "==== STEP 6  票上「不得放掉的天花板」逐條複驗 ===="
echo "---- 6a  --deferred(#84,11/1,第七格是宣告過的天花板)"
set +e
python "$ROOT/scripts/qa/83-deferred-sweep.py" "$ROOT" --deferred
set -e
echo "---- 6b  --lambda-scope(#83,9/0)"
python "$ROOT/scripts/qa/81-lambda-sweep.py" "$ROOT" --lambda-scope
echo "---- 6c  --own-names(#81,13/0)"
python "$ROOT/scripts/qa/79-return-sweep.py" "$ROOT" --own-names
echo "---- 6d  --return-carry(#79,6/0)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --return-carry
echo "---- 6e  --callgraph(4/0)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --callgraph
echo "---- 6f  --live-overapprox(5/0)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --live-overapprox
echo "---- 6g  --bypass-position(6/0)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --bypass-position
echo "---- 6h  --mention(13/0)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT"
echo "---- 6i  --positional(#58 原病,4/0)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --positional
echo "---- 6j  #73 的三把尺(6/0 ×3)"
python "$ROOT/scripts/qa/73-reach-sweep.py" "$ROOT" --reach-shapes
python "$ROOT/scripts/qa/73-reach-sweep.py" "$ROOT" --call-position
python "$ROOT/scripts/qa/73-reach-sweep.py" "$ROOT" --alias
echo "---- 6k  #75 的 --bind-quiet(11/0)"
python "$ROOT/scripts/qa/75-binding-sweep.py" "$ROOT" --bind-quiet

echo "==== STEP 7  已開票的天花板複驗(known issues,期望維持不變)===="
set +e
echo "---- 7a  --pin-position(#72,6/4)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --pin-position
echo "---- 7b  --print-detect(#74,7/5)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --print-detect
echo "---- 7c  --skips(#66,3/1)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --skips
echo "---- 7d  --name-collision(#80,4/3)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --name-collision
echo "---- 7e  --arg-widen(7/5)"
python "$ROOT/scripts/qa/73-reach-sweep.py" "$ROOT" --arg-widen
echo "---- 7f  #75 的另兩把尺(#77 12/6 / #78 8/5)"
python "$ROOT/scripts/qa/75-binding-sweep.py" "$ROOT" --binding-shapes
python "$ROOT/scripts/qa/75-binding-sweep.py" "$ROOT" --header
echo "---- 7g  #79 的 --result-called(#82,14/3)"
python "$ROOT/scripts/qa/79-return-sweep.py" "$ROOT" --result-called
set -e

echo "==== STEP 8  同型全掃 尺一(誤放):coroutine 也是 deferred body,gens 只認 yield ===="
set +e
python "$ROOT/scripts/qa/86-async-sweep.py" "$ROOT" --async-defer
echo "exit $?  <- 非 0 是本輪 finding"
echo "---- 對照組:#86 修之前(cb7e030)—— 6 條,#86 收掉的是 async generator 那格,剩 5 條不是 regression"
python "$ROOT/scripts/qa/86-async-sweep.py" "$ROOT" --async-defer --prev86
set -e

echo "==== STEP 9  同型全掃 尺二(誤紅):shadowed 走遍每個 scope,不只模組自己綁的 ===="
set +e
python "$ROOT/scripts/qa/86-async-sweep.py" "$ROOT" --shadow-scope
echo "exit $?  <- 非 0 是本輪 finding"
echo "---- 對照組:#86 修之前(cb7e030)—— 那九格全 GREEN,這九條誤紅是 de68088 帶進來的"
python "$ROOT/scripts/qa/86-async-sweep.py" "$ROOT" --shadow-scope --prev86
set -e

echo "==== STEP 10  同型全掃 尺三(誤放):consumes 的 method call 只認 attribute 名字 ===="
set +e
python "$ROOT/scripts/qa/86-async-sweep.py" "$ROOT" --attr-consumer
echo "exit $?  <- 非 0 是本輪 finding"
echo "---- 對照組:#86 修之前(cb7e030)—— 4 條,#86 靠尺二那個過寬的 shadowed 誤打誤撞收掉一格"
python "$ROOT/scripts/qa/86-async-sweep.py" "$ROOT" --attr-consumer --prev86
set -e

echo "==== STEP 11  對照組不是模擬:--prev86 是 git show cb7e030:scripts/validate.py 真的 import 舊版 ===="
sed -n '/^def guard_module/,/return __import__/p' "$ROOT/scripts/qa/60-mention-sweep.py"
git -C "$ROOT" log --oneline -1 cb7e030

echo "==== STEP 12  STEP 2 的尺沒被動到判準:84-generator-sweep.py 只多一個對照組 flag ===="
git -C "$ROOT" diff -- scripts/qa/84-generator-sweep.py

echo "==== STEP 13  repo 本體沒被動過 ===="
python "$ROOT/scripts/validate.py"
git -C "$ROOT" status --short
