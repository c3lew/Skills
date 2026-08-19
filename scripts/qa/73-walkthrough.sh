#!/usr/bin/env bash
# #73 QA walkthrough — live_nodes 的可達性從「名字被提到」收回「名字在呼叫位置」(bug fix)。
# 範圍 = #73 的重現 scenario + 既有 regression suite + 拿新判準當尺的同型全掃。
# 全程 xtrace,指令與輸出同一份。
#
# 用法:bash scripts/qa/73-walkthrough.sh "$(mktemp -d)/qa73"
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

echo "==== STEP 2  票上宣稱的 mutation 咬合:把可達性放寬回「名字被提到」-> self-check 要轉紅 ===="
grep -n 'invoked |= names_in(n.func)' "$CP/scripts/validate.py"
python - "$CP" <<'PY'
import pathlib, sys
sys.stdout.reconfigure(encoding="utf-8")
p = pathlib.Path(sys.argv[1]) / "scripts" / "validate.py"
s = p.read_text(encoding="utf-8")
old = """                if isinstance(n, ast.Call):
                    invoked |= names_in(n.func)
                    for arg in list(n.args) + [k.value for k in n.keywords]:
                        invoked |= names_in(arg)
                elif isinstance(n, ast.Assign):"""
new = """                if isinstance(n, (ast.Name, ast.Attribute)):
                    invoked |= names_in(n)
                if isinstance(n, ast.Assign):"""
assert old in s, "mutation 目標不在 — 判準被改過了"
p.write_text(s.replace(old, new), encoding="utf-8")
print("mutation 已套用:可達性放寬回「名字被提到」")
PY
set +e
python "$CP/scripts/validate.py" --self-check
echo "exit $?  <- 非 0 是要的:#73 的病一還原,self-check 就該紅"
set -e
cp "$ROOT/scripts/validate.py" "$CP/scripts/validate.py"

echo "==== STEP 3  副本還原後 -> 綠(證明上面判紅的是 mutation,不是副本壞了)===="
python "$CP/scripts/validate.py" --self-check

echo "==== STEP 4  #73 的重現 scenario 原樣重跑(票上的母體 5)===="
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --live-overapprox

echo "==== STEP 5  對照組:同一組 case 在 #73 修之前(e56789c)3 條誤放 -> 這輪真的修好了 ===="
set +e
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --live-overapprox --prev73
echo "exit $?  <- 非 0 是要的:對照組該紅"
set -e

echo "==== STEP 6  票上「不得放掉的天花板」逐條複驗 ===="
echo "---- 6a  --callgraph(alias / handler dict / callback 不得誤紅)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --callgraph
echo "---- 6b  --bypass-position(#70 的死碼四條維持 RED)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --bypass-position
echo "---- 6c  --positional(#58 原病)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --positional
echo "---- 6d  mention 預設全表"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT"
echo "---- 6e  triage-to-maintain.py 的 error 數要 = 0"
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
echo "---- 7a  --pin-position(#72:可達性只裝在 bypass 那半)"
set +e
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --pin-position
echo "exit $?  <- 非 0 是預期的:#72 已開票"
echo "---- 7b  --print-detect(#74:沒-print 豁免是 name-only)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --print-detect
echo "exit $?  <- 非 0 是預期的:#74 已開票"
echo "---- 7c  --skips(#66:SyntaxError 靜默跳過)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --skips
echo "exit $?  <- 非 0 是預期的:#66 已開票"
set -e

echo "==== STEP 8  本輪同型全掃(一):綁定形狀 — callable 真的跑,但名字不在呼叫位置 ===="
# #73 的綁定規則只認 `t = <expr>` 且 t 是裸 Name。同一把尺量過其他綁定寫法。
set +e
python "$ROOT/scripts/qa/73-reach-sweep.py" "$ROOT" --binding
echo "exit $?  <- 非 0 是本輪 finding"
set -e

echo "==== STEP 9  對照組:同一組 case 在 #73 修之前(e56789c)只有 2 條不合 ===="
set +e
python "$ROOT/scripts/qa/73-reach-sweep.py" "$ROOT" --binding --prev
echo "exit $?  <- 差額 = #73 引入的誤紅"
set -e

echo "==== STEP 10  本輪同型全掃(二):引數即呼叫 — 名字交給任何 call 就算 live ===="
set +e
python "$ROOT/scripts/qa/73-reach-sweep.py" "$ROOT" --arg-widen
echo "exit $?  <- 非 0 是本輪 finding"
set -e

echo "==== STEP 11  對照組:同一組 case 在 e56789c 同樣 5 條不合 -> 不是 #73 引入的 ===="
set +e
python "$ROOT/scripts/qa/73-reach-sweep.py" "$ROOT" --arg-widen --prev
echo "exit $?"
set -e

echo "==== STEP 12  repo 本體沒被動過 ===="
python "$ROOT/scripts/validate.py"
git -C "$ROOT" status --short
