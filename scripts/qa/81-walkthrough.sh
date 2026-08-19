#!/usr/bin/env bash
# #81 QA walkthrough — live def 的「自己產生的名字」從兩種 node 擴成整面 binding(bug fix)。
# 範圍 = #81 的重現 scenario + 既有 regression suite + 拿新判準當尺的同型全掃。
# 全程 xtrace,指令與輸出同一份。
#
# 用法:bash scripts/qa/81-walkthrough.sh "$(mktemp -d)/qa81"
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

echo "==== STEP 2  #81 的重現 scenario 原樣重跑(票上的母體 13,修前 6 不合)===="
python "$ROOT/scripts/qa/79-return-sweep.py" "$ROOT" --own-names

echo "==== STEP 3  對照組:#79 修之前(8beebc5)同一組 13 條裡 11 條誤放 ===="
set +e
python "$ROOT/scripts/qa/79-return-sweep.py" "$ROOT" --own-names --prev | tail -2
echo "exit $?  <- 非 0 是要的:對照組該紅"
set -e

echo "==== STEP 4  票上宣稱的 mutation 咬合:binds 的 branch 逐一拿掉 -> self-check 要轉紅 ===="
for M in alias funcclass excepthandler matchmapping typevar; do
  echo "---- 4.$M"
  cp "$ROOT/scripts/validate.py" "$CP/scripts/validate.py"
  python - "$CP" "$M" <<'PY'
import pathlib, sys
sys.stdout.reconfigure(encoding="utf-8")
p = pathlib.Path(sys.argv[1]) / "scripts" / "validate.py"
s = p.read_text(encoding="utf-8")
M = {
  # 每格都是「把 #81 補的一個 branch 拿掉」 —— 拿掉就該有 self_check 的 pin 咬住
  "alias": '''    if isinstance(node, ast.alias):  # `import os as dump`, `import dump.sub`
        return {node.asname or node.name.split(".")[0]}
''',
  "funcclass": '''    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return {node.name}
''',
  "excepthandler": '''    if isinstance(node, (ast.ExceptHandler, ast.MatchAs, ast.MatchStar)):
        return {node.name} if node.name else set()
''',
  "matchmapping": '''    if isinstance(node, ast.MatchMapping):
        return {node.rest} if node.rest else set()
''',
  "typevar": '''    if isinstance(node, (ast.TypeVar, ast.ParamSpec, ast.TypeVarTuple)):
        return {node.name}  # PEP 695 `def get[dump]()`
''',
}
old = M[sys.argv[2]]
assert old in s, "mutation 目標不在 — 判準被改過了"
p.write_text(s.replace(old, ""), encoding="utf-8")
print("mutation 已套用:", sys.argv[2])
PY
  set +e
  python "$CP/scripts/validate.py" --self-check 2>&1 | tail -3
  echo "exit ${PIPESTATUS[0]}  <- 非 0 是要的:branch 一拿掉,self-check 就該紅"
  set -e
done

echo "==== STEP 5  副本還原後 -> 綠(證明上面判紅的是 mutation,不是副本壞了)===="
cp "$ROOT/scripts/validate.py" "$CP/scripts/validate.py"
python "$CP/scripts/validate.py" --self-check

echo "==== STEP 6  票上「不得放掉的天花板」逐條複驗 ===="
echo "---- 6a  --return-carry(#79,6/0)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --return-carry | tail -2
echo "---- 6b  --callgraph(4/0)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --callgraph | tail -2
echo "---- 6c  --live-overapprox(5/0)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --live-overapprox | tail -2
echo "---- 6d  --bypass-position(6/0)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --bypass-position | tail -2
echo "---- 6e  --mention(13/0)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" | tail -2
echo "---- 6f  --positional(#58 原病,4/0)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --positional | tail -2
echo "---- 6g  #73 的三把尺(6/0 ×3)"
python "$ROOT/scripts/qa/73-reach-sweep.py" "$ROOT" --reach-shapes | tail -2
python "$ROOT/scripts/qa/73-reach-sweep.py" "$ROOT" --call-position | tail -2
python "$ROOT/scripts/qa/73-reach-sweep.py" "$ROOT" --alias | tail -2
echo "---- 6h  #75 的 --bind-quiet(11/0)"
python "$ROOT/scripts/qa/75-binding-sweep.py" "$ROOT" --bind-quiet | tail -2

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
echo "---- 7f  #79 的 --result-called(#82,未修)"
python "$ROOT/scripts/qa/79-return-sweep.py" "$ROOT" --result-called | tail -2
set -e

echo "==== STEP 8  本輪同型全掃:own_scope 停在 Lambda,names_in 沒停 ===="
set +e
python "$ROOT/scripts/qa/81-lambda-sweep.py" "$ROOT" --lambda-scope
echo "exit $?  <- 非 0 是本輪 finding"
echo "---- 對照組:#81 修之前(b43137f)—— 同樣 7 條,證明不是 regression"
python "$ROOT/scripts/qa/81-lambda-sweep.py" "$ROOT" --lambda-scope --prev81 | tail -2
set -e

echo "==== STEP 9  repo 本體沒被動過 ===="
python "$ROOT/scripts/validate.py"
git -C "$ROOT" status --short
