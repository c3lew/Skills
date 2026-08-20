#!/usr/bin/env bash
# #91 QA walkthrough — 認 event loop 驅動改看名字綁到什麼。
# 範圍 = #91 的重現 scenario + 既有 regression suite + 全域修前對照 + 獨立實跑 oracle
#        + 拿修法自己的三把尺做的同型全掃 + 產出宣稱的九個 knob 逐一咬合。
# 全程 xtrace,指令與輸出同一份。
#
# 用法:bash scripts/qa/91-walkthrough.sh "$(mktemp -d)/qa91"
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

echo "==== STEP 2  #91 的重現 scenario 原樣重跑(票上兩面母體各 12,要 0)===="
python "$ROOT/scripts/qa/87-drive-sweep.py" "$ROOT" --driven-attr
python "$ROOT/scripts/qa/87-drive-sweep.py" "$ROOT" --driven-shadow

echo "==== STEP 3  對照組:#91 修之前(fa9d0c3)兩面各 10 誤 ===="
set +e
python "$ROOT/scripts/qa/87-drive-sweep.py" "$ROOT" --driven-attr --prev91
echo "exit $?  <- 非 0 是要的:對照組該紅"
python "$ROOT/scripts/qa/87-drive-sweep.py" "$ROOT" --driven-shadow --prev91
echo "exit $?  <- 非 0 是要的:對照組該紅"
set -e

echo "==== STEP 4  對照組不是模擬:--prev91 是 git show fa9d0c3:scripts/validate.py 真的 import 舊版 ===="
sed -n '/^def guard_module/,/return __import__/p' "$ROOT/scripts/qa/60-mention-sweep.py"
git -C "$ROOT" log --oneline -1 fa9d0c3
sed -n '/^BASELINES/,/prev91/p' "$ROOT/scripts/qa/87-drive-sweep.py"

echo "==== STEP 5  票上「不得放掉的天花板」逐條複驗 ===="
echo "---- 5a  --async-defer(#87,12/0)"
python "$ROOT/scripts/qa/86-async-sweep.py" "$ROOT" --async-defer
echo "---- 5b  --generator(#86,12/0)"
python "$ROOT/scripts/qa/84-generator-sweep.py" "$ROOT" --generator
echo "---- 5c  --deferred(#84,11/1,第七格是宣告過的天花板)"
set +e
python "$ROOT/scripts/qa/83-deferred-sweep.py" "$ROOT" --deferred
set -e
echo "---- 5d  --lambda-scope(#83,9/0)"
python "$ROOT/scripts/qa/81-lambda-sweep.py" "$ROOT" --lambda-scope
echo "---- 5e  --own-names(#81,13/0)"
python "$ROOT/scripts/qa/79-return-sweep.py" "$ROOT" --own-names
echo "---- 5f  --return-carry / --callgraph / --live-overapprox / --bypass-position"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --return-carry
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --callgraph
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --live-overapprox
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --bypass-position
echo "---- 5g  --mention(13/0)與 --positional(#58 原病,4/0)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --positional
echo "---- 5h  #73 的三把尺(6/0 ×3)"
python "$ROOT/scripts/qa/73-reach-sweep.py" "$ROOT" --reach-shapes
python "$ROOT/scripts/qa/73-reach-sweep.py" "$ROOT" --call-position
python "$ROOT/scripts/qa/73-reach-sweep.py" "$ROOT" --alias
echo "---- 5i  #75 的 --bind-quiet(11/0)"
python "$ROOT/scripts/qa/75-binding-sweep.py" "$ROOT" --bind-quiet

echo "==== STEP 6  已開票的天花板複驗(known issues,紅字數一格不得動)===="
set +e
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --pin-position
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --print-detect
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --skips
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --name-collision
python "$ROOT/scripts/qa/73-reach-sweep.py" "$ROOT" --arg-widen
python "$ROOT/scripts/qa/75-binding-sweep.py" "$ROOT" --binding-shapes
python "$ROOT/scripts/qa/75-binding-sweep.py" "$ROOT" --header
python "$ROOT/scripts/qa/79-return-sweep.py" "$ROOT" --result-called
python "$ROOT/scripts/qa/86-async-sweep.py" "$ROOT" --shadow-scope
python "$ROOT/scripts/qa/86-async-sweep.py" "$ROOT" --attr-consumer
python "$ROOT/scripts/qa/87-drive-sweep.py" "$ROOT" --await-shapes
set -e

echo "==== STEP 7  全域修前對照 a:222 格 fixture 逐格比 fa9d0c3 vs 14f69f2(本輪)===="
set +e
python "$ROOT/scripts/qa/87-prevdiff.py" "$ROOT" --prev=fa9d0c3
echo "exit $?  <- 非 0 是本輪引入的誤判"
set -e

echo "==== STEP 8  全域修前對照 b:對 55fc8eb(票上宣稱本輪引入的誤判 14 -> 4)===="
set +e
python "$ROOT/scripts/qa/87-prevdiff.py" "$ROOT"
echo "exit $?  <- 剩下的 4 格全在 AWAIT_SHAPES(#92 範圍)"
set -e

echo "==== STEP 9  獨立 oracle:不讀 validate.py 一行,把 fixture 真的跑起來看 bypass 有沒有執行 ===="
set +e
python "$ROOT/scripts/qa/87-oracle.py" "$ROOT" --91
echo "exit $?  <- 非 0 = 有 fixture 的期望值跟實跑對不上"
set -e

echo "==== STEP 10  同型全掃 尺一(誤放):asyncio_graph 收綁定不看位置、綁走了不追 ===="
set +e
python "$ROOT/scripts/qa/91-graph-sweep.py" "$ROOT" --graph-scope
echo "exit $?  <- 非 0 是本輪 finding"
echo "---- 對照組:#91 修之前(fa9d0c3)"
python "$ROOT/scripts/qa/91-graph-sweep.py" "$ROOT" --graph-scope --prev91
set -e

echo "==== STEP 11  同型全掃 尺二(誤紅):loop 的綁定只從 Assign / withitem 讀 ===="
set +e
python "$ROOT/scripts/qa/91-graph-sweep.py" "$ROOT" --loop-binding
echo "exit $?  <- 非 0 是本輪 finding"
echo "---- 對照組:#91 修之前(fa9d0c3)—— 0 不合,這七格全部是本輪引入"
python "$ROOT/scripts/qa/91-graph-sweep.py" "$ROOT" --loop-binding --prev91
set -e

echo "==== STEP 12  同型全掃 尺三(誤紅):LOOP_FROM 是四個名字的清單,不是型別判讀 ===="
set +e
python "$ROOT/scripts/qa/91-graph-sweep.py" "$ROOT" --loop-source
echo "exit $?  <- 非 0 是本輪 finding"
echo "---- 對照組:#91 修之前(fa9d0c3)"
python "$ROOT/scripts/qa/91-graph-sweep.py" "$ROOT" --loop-source --prev91
set -e

echo "==== STEP 13  產出宣稱的九個 knob:repo 裡找不到(grep 全空)===="
set +e
grep -rn "drives_always_true\|drives_name_only\|drives_no_from_import\|graph_no_alias\|graph_no_fixpoint\|graph_no_withitem\|loop_from_anything\|loop_from_bare_name\|revert_to_name_list" \
    "$ROOT/scripts" "$ROOT/skills" --include=*.py | grep -v "91-mutate.py"
echo "exit $?  <- 非 0 = 除了 QA 這輪自己補的 91-mutate.py,一個都沒有"
set -e

echo "==== STEP 14  QA 重建的九個 knob 逐一改壞 -> --self-check 要轉紅 ===="
for M in $(python "$ROOT/scripts/qa/91-mutate.py" --list | tr -d '\r'); do
  echo "---- 14.$M"
  cp "$ROOT/scripts/validate.py" "$CP/scripts/validate.py"
  python "$ROOT/scripts/qa/91-mutate.py" "$CP" "$M"
  set +e
  python "$CP/scripts/validate.py" --self-check 2>&1 | tail -3
  echo "exit ${PIPESTATUS[0]}  <- 非 0 是要的;0 = 這條判準沒有證據住在預設會跑的地方"
  echo "---- 同一個 mutation 下,三把尺各掉幾格:"
  python "$ROOT/scripts/qa/91-graph-sweep.py" "$CP" --graph-scope | tail -1
  python "$ROOT/scripts/qa/91-graph-sweep.py" "$CP" --loop-binding | tail -1
  python "$ROOT/scripts/qa/91-graph-sweep.py" "$CP" --loop-source | tail -1
  set -e
done

echo "==== STEP 15  副本還原後 -> 綠(證明上面判紅的是 mutation,不是副本壞了)===="
cp "$ROOT/scripts/validate.py" "$CP/scripts/validate.py"
python "$CP/scripts/validate.py" --self-check

echo "==== STEP 16  87-mutate.py 的 17 個 knob 逐一改壞(產出宣稱「全部咬得住」)===="
python - "$ROOT" > "$QA/k87.txt" <<'PY'
import importlib.util
import sys
spec = importlib.util.spec_from_file_location(
    "m", sys.argv[1] + "/scripts/qa/87-mutate.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
print(" ".join(sorted(m.KNOBS)))
PY
cat "$QA/k87.txt"
set +e
for M in $(cat "$QA/k87.txt"); do
  cp "$ROOT/scripts/validate.py" "$CP/scripts/validate.py"
  python "$ROOT/scripts/qa/87-mutate.py" "$CP" "$M" >/dev/null 2>&1 || { echo "$M ANCHOR-FAIL"; continue; }
  python "$CP/scripts/validate.py" --self-check >/dev/null 2>&1
  echo "$M self-check exit=$?"
done
set -e
cp "$ROOT/scripts/validate.py" "$CP/scripts/validate.py"

echo "==== STEP 16b  consumes_no_await 沒紅,但它不是 no-op ===="
cp "$ROOT/scripts/validate.py" "$CP/scripts/validate.py"
python "$ROOT/scripts/qa/87-mutate.py" "$CP" consumes_no_await
set +e
python "$CP/scripts/validate.py" --self-check
echo "exit $?  <- 0 = self-check 沒咬住"
python "$ROOT/scripts/qa/86-async-sweep.py" "$CP" --async-defer | tail -1
echo "^ #87 的母體 12 從 0 掉到 1 —— 判準真的被拆掉了,只是沒有人會知道"
python "$ROOT/scripts/qa/87-drive-sweep.py" "$CP" --await-shapes | tail -1
set -e
cp "$ROOT/scripts/validate.py" "$CP/scripts/validate.py"

echo "==== STEP 17  repo 本體沒被動過 ===="
python "$ROOT/scripts/validate.py"
git -C "$ROOT" status --short
