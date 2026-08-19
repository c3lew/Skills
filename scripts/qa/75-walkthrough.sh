#!/usr/bin/env bash
# #75 QA walkthrough — 可達性的綁定採集從「只認 Assign」擴到同型的其他寫法(bug fix)。
# 範圍 = #75 的重現 scenario + 既有 regression suite + 拿新判準當尺的同型全掃。
# 全程 xtrace,指令與輸出同一份。
#
# 用法:bash scripts/qa/75-walkthrough.sh "$(mktemp -d)/qa75"
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

echo "==== STEP 2  #75 的重現 scenario 原樣重跑(票上的母體 6)===="
python "$ROOT/scripts/qa/73-reach-sweep.py" "$ROOT" --binding

echo "==== STEP 3  對照組:同一組 case 在 #75 修之前(39003a3)5 條誤紅 ===="
set +e
python "$ROOT/scripts/qa/73-reach-sweep.py" "$ROOT" --binding --prev75
echo "exit $?  <- 非 0 是要的:對照組該紅"
set -e

echo "==== STEP 4  票上宣稱的 mutation 咬合:四個旋鈕逐一還原 -> self-check 要轉紅 ===="
for M in bindings_in classbody own_scope mention; do
  echo "---- 4.$M"
  cp "$ROOT/scripts/validate.py" "$CP/scripts/validate.py"
  python - "$CP" "$M" <<'PY'
import pathlib, sys
sys.stdout.reconfigure(encoding="utf-8")
p = pathlib.Path(sys.argv[1]) / "scripts" / "validate.py"
s = p.read_text(encoding="utf-8")
M = {
  # #75:綁定採集縮回 #73 那版 —— 只認 `Assign` 且 target 是裸 `Name`
  "bindings_in": ("""    if isinstance(node, ast.Assign):
        pairs = [(t, node.value) for t in node.targets]
    elif isinstance(node, ast.AnnAssign) and node.value is not None:
        pairs = [(node.target, node.value)]
    elif isinstance(node, (ast.For, ast.AsyncFor)):
        pairs = [(node.target, node.iter)]
    else:
        return {}""",
   """    if isinstance(node, ast.Assign):
        pairs = [(t, node.value) for t in node.targets
                 if isinstance(t, ast.Name)]
    else:
        return {}"""),
  # #75:class body 又被當成 def body 砍掉
  "classbody": ("""        elif isinstance(stmt, ast.ClassDef):
            out += runs(stmt.body)
        elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue""",
   """        elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef,
                               ast.ClassDef)):
            continue"""),
  # #75:`Return` 的採集跨回巢狀 scope
  "own_scope": ("        for n in own_scope(node):", "        for n in ast.walk(node):"),
  # #73:可達性放寬回「名字被提到」
  "mention": ("""                if isinstance(n, ast.Call):
                    invoked |= names_in(n.func)
                    for arg in list(n.args) + [k.value for k in n.keywords]:
                        invoked |= names_in(arg)
                else:""",
   """                if isinstance(n, (ast.Name, ast.Attribute)):
                    invoked |= names_in(n)
                if True:"""),
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
echo "---- 6a  --live-overapprox(#73 立的:死碼 bypass 不得因撞名豁免)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --live-overapprox
echo "---- 6b  --bypass-position(#70 的死碼四條維持 RED)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --bypass-position
echo "---- 6c  --callgraph(alias / handler dict / callback 不得誤紅)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --callgraph
echo "---- 6d  --positional(#58 原病)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --positional
echo "---- 6e  mention 預設全表"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT"
echo "---- 6f  triage-to-maintain.py 的 error 數要 = 0"
python - "$ROOT" <<'PY'
import sys, pathlib
sys.path.insert(0, sys.argv[1] + "/scripts")
sys.stdout.reconfigure(encoding="utf-8")
import validate as V
errs = [e for e in V.stream_encoding_issues(pathlib.Path(sys.argv[1])) if "triage-to-maintain" in e]
print("triage-to-maintain.py 的 error 數 ->", len(errs))
assert errs == []
PY

echo "==== STEP 7  已開票的天花板複驗(known issues,期望維持不變)===="
set +e
echo "---- 7a  --pin-position(#72:可達性只裝在 bypass 那半)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --pin-position | tail -2
echo "---- 7b  --print-detect(#74:沒-print 豁免是 name-only)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --print-detect | tail -2
echo "---- 7c  --skips(#66:SyntaxError 靜默跳過)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --skips | tail -2
echo "---- 7d  --arg-widen(#74:引數即呼叫,改前改後應一樣)"
python "$ROOT/scripts/qa/73-reach-sweep.py" "$ROOT" --arg-widen | tail -2
python "$ROOT/scripts/qa/73-reach-sweep.py" "$ROOT" --arg-widen --prev75 | tail -2
set -e

echo "==== STEP 8  本輪同型全掃(一):綁定的其他寫法 — 同一個 claim 換個寫法 ===="
set +e
python "$ROOT/scripts/qa/75-binding-sweep.py" "$ROOT" --binding-shapes
echo "exit $?  <- 非 0 是本輪 finding"
echo "---- 對照組:#75 修之前(39003a3)"
python "$ROOT/scripts/qa/75-binding-sweep.py" "$ROOT" --binding-shapes --prev | tail -2
set -e

echo "==== STEP 9  本輪同型全掃(二):複合敘述的 header — #75 對 For 補的那條尺 ===="
set +e
python "$ROOT/scripts/qa/75-binding-sweep.py" "$ROOT" --header
echo "exit $?  <- 非 0 是本輪 finding"
echo "---- 對照組:#75 修之前(39003a3)"
python "$ROOT/scripts/qa/75-binding-sweep.py" "$ROOT" --header --prev | tail -2
set -e

echo "==== STEP 10  本輪同型全掃(三):放寬的代價 — 綁了但沒呼叫必須維持死 ===="
set +e
python "$ROOT/scripts/qa/75-binding-sweep.py" "$ROOT" --bind-quiet
echo "exit $?  <- 非 0 是本輪 finding"
echo "---- 對照組:#75 修之前(39003a3)"
python "$ROOT/scripts/qa/75-binding-sweep.py" "$ROOT" --bind-quiet --prev | tail -2
set -e

echo "==== STEP 11  repo 本體沒被動過 ===="
python "$ROOT/scripts/validate.py"
git -C "$ROOT" status --short
