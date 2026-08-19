#!/usr/bin/env bash
# #79 QA walkthrough — live def 的回傳值改成「結果被呼叫才算 live」(bug fix)。
# 範圍 = #79 的重現 scenario + 既有 regression suite + 拿新判準當尺的同型全掃。
# 全程 xtrace,指令與輸出同一份。
#
# 用法:bash scripts/qa/79-walkthrough.sh "$(mktemp -d)/qa79"
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

echo "==== STEP 2  #79 的重現 scenario 原樣重跑(票上的母體,現在 6 條)===="
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --return-carry

echo "==== STEP 3  對照組:#79 修之前(8beebc5)那三條誤放,再往前(39003a3)是兩條誤紅 ===="
set +e
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --return-carry --prev79
echo "exit $?  <- 非 0 是要的:對照組該紅"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --return-carry --prev75
echo "exit $?  <- 非 0 是要的:對照組該紅"
set -e

echo "==== STEP 4  票上宣稱的 mutation 咬合:兩個旋鈕逐一還原 -> self-check 要轉紅 ===="
for M in ret_carry local_excl; do
  echo "---- 4.$M"
  cp "$ROOT/scripts/validate.py" "$CP/scripts/validate.py"
  python - "$CP" "$M" <<'PY'
import pathlib, sys
sys.stdout.reconfigure(encoding="utf-8")
p = pathlib.Path(sys.argv[1]) / "scripts" / "validate.py"
s = p.read_text(encoding="utf-8")
M = {
  # #79:回傳值縮回「無條件 carry」—— RET key 拆掉,`get()` 一行就豁免
  "ret_carry": ("""                returned[RET + name] |= names_in(n.value) - local""",
   """                returned[name] |= names_in(n.value) - local"""),
  # #79:def 內部自己產生的名字不再排掉 —— `def get(): dump = 1` 撞名就豁免
  "local_excl": ("""                returned[RET + name] |= names_in(n.value) - local""",
   """                returned[RET + name] |= names_in(n.value)"""),
}
old, new = M[sys.argv[2]]
assert old in s, "mutation 目標不在 — 判準被改過了"
p.write_text(s.replace(old, new), encoding="utf-8")
print("mutation 已套用:", sys.argv[2])
PY
  set +e
  python "$CP/scripts/validate.py" --self-check 2>&1 | tail -3
  echo "exit ${PIPESTATUS[0]}  <- 非 0 是要的:旋鈕一還原,self-check 就該紅"
  set -e
done

echo "==== STEP 5  副本還原後 -> 綠(證明上面判紅的是 mutation,不是副本壞了)===="
cp "$ROOT/scripts/validate.py" "$CP/scripts/validate.py"
python "$CP/scripts/validate.py" --self-check

echo "==== STEP 6  票上「不得放掉的天花板」逐條複驗 ===="
echo "---- 6a  --callgraph(alias / handler dict / callback 不得誤紅)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --callgraph
echo "---- 6b  --live-overapprox(#73 立的:死碼 bypass 不得因撞名豁免)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --live-overapprox
echo "---- 6c  --bypass-position(#70 的死碼四條維持 RED)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --bypass-position
echo "---- 6d  --mention 預設全表"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT"
echo "---- 6e  --positional(#58 原病)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --positional
echo "---- 6f  #73 的三把尺"
python "$ROOT/scripts/qa/73-reach-sweep.py" "$ROOT" --reach-shapes
python "$ROOT/scripts/qa/73-reach-sweep.py" "$ROOT" --call-position
python "$ROOT/scripts/qa/73-reach-sweep.py" "$ROOT" --alias
echo "---- 6g  #75 的 --bind-quiet(build 宣稱 11/0)"
python "$ROOT/scripts/qa/75-binding-sweep.py" "$ROOT" --bind-quiet

echo "==== STEP 7  已開票的天花板複驗(known issues,期望維持不變)===="
set +e
echo "---- 7a  --pin-position(#72)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --pin-position | tail -2
echo "---- 7b  --print-detect(#74)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --print-detect | tail -2
echo "---- 7c  --skips(#66)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --skips | tail -2
echo "---- 7d  --name-collision(#80,未修)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --name-collision | tail -2
echo "---- 7e  #75 的另兩把尺(#77 / #78,未修)"
python "$ROOT/scripts/qa/75-binding-sweep.py" "$ROOT" --binding-shapes | tail -2
python "$ROOT/scripts/qa/75-binding-sweep.py" "$ROOT" --header | tail -2
set -e

echo "==== STEP 8  本輪同型全掃(一):def 交出去的是不是外面那個名字(誤放那邊)===="
set +e
python "$ROOT/scripts/qa/79-return-sweep.py" "$ROOT" --own-names
echo "exit $?  <- 非 0 是本輪 finding"
echo "---- 對照組:#79 修之前(8beebc5)"
python "$ROOT/scripts/qa/79-return-sweep.py" "$ROOT" --own-names --prev | tail -2
set -e

echo "==== STEP 9  本輪同型全掃(二):把結果送到呼叫位置的每一種寫法(誤紅那邊)===="
set +e
python "$ROOT/scripts/qa/79-return-sweep.py" "$ROOT" --result-called
echo "exit $?  <- 非 0 是本輪 finding"
echo "---- 對照組:#79 修之前(8beebc5)"
python "$ROOT/scripts/qa/79-return-sweep.py" "$ROOT" --result-called --prev | tail -2
set -e

echo "==== STEP 10  repo 本體沒被動過 ===="
python "$ROOT/scripts/validate.py"
git -C "$ROOT" status --short
