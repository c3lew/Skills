#!/usr/bin/env bash
# #87 QA walkthrough — deferred 邊界補上第三面(coroutine)。
# 範圍 = #87 的重現 scenario + 既有 regression suite + 全域修前對照 + 獨立實跑 oracle
#        + 拿修法自己的三把尺做的同型全掃。
# 全程 xtrace,指令與輸出同一份。
#
# 用法:bash scripts/qa/87-walkthrough.sh "$(mktemp -d)/qa87"
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

echo "==== STEP 2  #87 的重現 scenario 原樣重跑(票上的母體 12,修前 5 誤放)===="
python "$ROOT/scripts/qa/86-async-sweep.py" "$ROOT" --async-defer

echo "==== STEP 3  對照組:#87 修之前(55fc8eb)同一組 12 條裡 5 條誤放 ===="
set +e
python "$ROOT/scripts/qa/86-async-sweep.py" "$ROOT" --async-defer --prev87
echo "exit $?  <- 非 0 是要的:對照組該紅"
set -e

echo "==== STEP 4  c51ba98 自己的三個 knob 改壞 -> self-check 該轉紅(本輪 finding:三個都不紅)===="
for M in gens_no_async consumes_no_await consumes_no_driven; do
  echo "---- 4.$M"
  cp "$ROOT/scripts/validate.py" "$CP/scripts/validate.py"
  python "$ROOT/scripts/qa/87-mutate.py" "$CP" "$M"
  set +e
  python "$CP/scripts/validate.py" --self-check 2>&1 | tail -3
  echo "exit ${PIPESTATUS[0]}  <- 0 = 這條判準沒有證據住在預設會跑的地方"
  set -e
  echo "---- 同一個 mutation 下,#87 的母體 12 掉幾格:"
  set +e
  python "$ROOT/scripts/qa/86-async-sweep.py" "$CP" --async-defer | tail -2
  set -e
done

echo "==== STEP 5  de68088 的十四個 knob(兩個錨重新對齊)逐一改壞 -> self-check 要轉紅 ===="
for M in names_in_no_gen_stop names_in_no_first_iter nodes_in_no_gen_stop \
         nodes_in_no_first_iter consumes_no_builtins consumes_no_for \
         consumes_no_nested_gen consumes_no_comp consumes_no_shadow \
         gens_not_subtracted no_eaten_calls no_eaten_via_name \
         through_no_gens no_gen_fixpoint; do
  echo "---- 5.$M"
  cp "$ROOT/scripts/validate.py" "$CP/scripts/validate.py"
  python "$ROOT/scripts/qa/87-mutate.py" "$CP" "$M"
  set +e
  python "$CP/scripts/validate.py" --self-check 2>&1 | tail -6
  echo "exit ${PIPESTATUS[0]}  <- 非 0 是要的:knob 一改壞,self-check 就該紅"
  set -e
done

echo "==== STEP 6  副本還原後 -> 綠(證明上面判紅的是 mutation,不是副本壞了)===="
cp "$ROOT/scripts/validate.py" "$CP/scripts/validate.py"
python "$CP/scripts/validate.py" --self-check

echo "==== STEP 7  票上「不得放掉的天花板」逐條複驗 ===="
echo "---- 7a  --generator(#86,12/0)"
python "$ROOT/scripts/qa/84-generator-sweep.py" "$ROOT" --generator
echo "---- 7b  --deferred(#84,11/1,第七格是宣告過的天花板)"
set +e
python "$ROOT/scripts/qa/83-deferred-sweep.py" "$ROOT" --deferred
set -e
echo "---- 7c  --lambda-scope(#83,9/0)"
python "$ROOT/scripts/qa/81-lambda-sweep.py" "$ROOT" --lambda-scope
echo "---- 7d  --own-names(#81,13/0)"
python "$ROOT/scripts/qa/79-return-sweep.py" "$ROOT" --own-names
echo "---- 7e  --return-carry(#79,6/0)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --return-carry
echo "---- 7f  --callgraph(4/0)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --callgraph
echo "---- 7g  --live-overapprox(5/0)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --live-overapprox
echo "---- 7h  --bypass-position(6/0)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --bypass-position
echo "---- 7i  --mention(13/0)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT"
echo "---- 7j  --positional(#58 原病,4/0)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --positional
echo "---- 7k  #73 的三把尺(6/0 ×3)"
python "$ROOT/scripts/qa/73-reach-sweep.py" "$ROOT" --reach-shapes
python "$ROOT/scripts/qa/73-reach-sweep.py" "$ROOT" --call-position
python "$ROOT/scripts/qa/73-reach-sweep.py" "$ROOT" --alias
echo "---- 7l  #75 的 --bind-quiet(11/0)"
python "$ROOT/scripts/qa/75-binding-sweep.py" "$ROOT" --bind-quiet

echo "==== STEP 8  已開票的天花板複驗(known issues,期望維持不變)===="
set +e
echo "---- 8a  --pin-position(#72,6/4)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --pin-position
echo "---- 8b  --print-detect(#74,7/5)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --print-detect
echo "---- 8c  --skips(#66,3/1)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --skips
echo "---- 8d  --name-collision(#80,4/3)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --name-collision
echo "---- 8e  --arg-widen(7/5)"
python "$ROOT/scripts/qa/73-reach-sweep.py" "$ROOT" --arg-widen
echo "---- 8f  #75 的另兩把尺(#77 12/6 / #78 8/5)"
python "$ROOT/scripts/qa/75-binding-sweep.py" "$ROOT" --binding-shapes
python "$ROOT/scripts/qa/75-binding-sweep.py" "$ROOT" --header
echo "---- 8g  #79 的 --result-called(#82,14/3)"
python "$ROOT/scripts/qa/79-return-sweep.py" "$ROOT" --result-called
echo "---- 8h  #86 的 --shadow-scope(11/9)與 --attr-consumer(6/3)"
python "$ROOT/scripts/qa/86-async-sweep.py" "$ROOT" --shadow-scope
python "$ROOT/scripts/qa/86-async-sweep.py" "$ROOT" --attr-consumer
set -e

echo "==== STEP 9  全域修前對照:222 格 fixture 逐格比 55fc8eb vs c51ba98 ===="
set +e
python "$ROOT/scripts/qa/87-prevdiff.py" "$ROOT"
echo "exit $?  <- 非 0 是本輪引入的誤判"
set -e

echo "==== STEP 10  獨立 oracle:不讀 validate.py 一行,把 fixture 真的跑起來看 bypass 有沒有執行 ===="
set +e
python "$ROOT/scripts/qa/87-oracle.py" "$ROOT"
echo "exit $?  <- 非 0 = 有 fixture 的期望值跟實跑對不上"
set -e

echo "==== STEP 11  同型全掃 尺一(誤紅):DRIVEN_BY 的名字被 shadowed 劃掉 ===="
set +e
python "$ROOT/scripts/qa/87-drive-sweep.py" "$ROOT" --driven-shadow
echo "exit $?  <- 非 0 是本輪 finding"
echo "---- 對照組:#87 修之前(55fc8eb)"
python "$ROOT/scripts/qa/87-drive-sweep.py" "$ROOT" --driven-shadow --prev87
set -e

echo "==== STEP 12  同型全掃 尺二(誤放):DRIVEN_BY 的 method call 只認 attribute 名字 ===="
set +e
python "$ROOT/scripts/qa/87-drive-sweep.py" "$ROOT" --driven-attr
echo "exit $?  <- 非 0 是本輪 finding"
echo "---- 對照組:#87 修之前(55fc8eb)—— 同樣 10 格,病因換人,不是本輪引入"
python "$ROOT/scripts/qa/87-drive-sweep.py" "$ROOT" --driven-attr --prev87
set -e

echo "==== STEP 13  同型全掃 尺三(誤紅):真的被驅動、但驅動位置不在名單上 ===="
set +e
python "$ROOT/scripts/qa/87-drive-sweep.py" "$ROOT" --await-shapes
echo "exit $?  <- 非 0 是本輪 finding"
echo "---- 對照組:#87 修之前(55fc8eb)"
python "$ROOT/scripts/qa/87-drive-sweep.py" "$ROOT" --await-shapes --prev87
set -e

echo "==== STEP 14  尺二的證據:把 DRIVEN_BY 收成只認 Name.id,那十格翻回 RED、母體 12 掉四格 ===="
cp "$ROOT/scripts/validate.py" "$CP/scripts/validate.py"
python "$ROOT/scripts/qa/87-mutate.py" "$CP" driven_attr_id_only
set +e
python "$ROOT/scripts/qa/87-drive-sweep.py" "$CP" --driven-attr
python "$ROOT/scripts/qa/86-async-sweep.py" "$CP" --async-defer
set -e
cp "$ROOT/scripts/validate.py" "$CP/scripts/validate.py"

echo "==== STEP 15  對照組不是模擬:--prev87 是 git show 55fc8eb:scripts/validate.py 真的 import 舊版 ===="
sed -n '/^def guard_module/,/return __import__/p' "$ROOT/scripts/qa/60-mention-sweep.py"
git -C "$ROOT" log --oneline -1 55fc8eb

echo "==== STEP 16  repo 本體沒被動過 ===="
python "$ROOT/scripts/validate.py"
git -C "$ROOT" status --short
