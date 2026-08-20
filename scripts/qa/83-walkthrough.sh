#!/usr/bin/env bash
# #83 QA walkthrough — lambda 那面兩半用同一個 scope 邊界(bug fix)。
# 範圍 = #83 的重現 scenario + 既有 regression suite + 拿修法自己的尺做的同型全掃。
# 全程 xtrace,指令與輸出同一份。
#
# 用法:bash scripts/qa/83-walkthrough.sh "$(mktemp -d)/qa83"
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

echo "==== STEP 2  #83 的重現 scenario 原樣重跑(票上的母體 9,修前 7 誤放)===="
python "$ROOT/scripts/qa/81-lambda-sweep.py" "$ROOT" --lambda-scope

echo "==== STEP 3  對照組:#83 修之前(d192aa9)同一組 9 條裡 7 條誤放 ===="
set +e
python "$ROOT/scripts/qa/81-lambda-sweep.py" "$ROOT" --lambda-scope --prev81 | tail -2
echo "exit $?  <- 非 0 是要的:對照組該紅"
set -e

echo "==== STEP 4  票上宣稱的 mutation 咬合:六個 knob 逐一改壞 -> self-check 要轉紅 ===="
for M in names_in_walks_lambda free_in_no_shadow free_in_no_default free_in_all_defaults bindings_in_branch live_nodes_branch; do
  echo "---- 4.$M"
  cp "$ROOT/scripts/validate.py" "$CP/scripts/validate.py"
  python - "$CP" "$M" <<'PY'
import pathlib, sys
sys.stdout.reconfigure(encoding="utf-8")
p = pathlib.Path(sys.argv[1]) / "scripts" / "validate.py"
s = p.read_text(encoding="utf-8")
M = {
  # names_in 走回 lambda 裡 —— #83 的原病
  "names_in_walks_lambda": ("""        if isinstance(n, ast.Lambda):
            continue
""", ""),
  # free_in 的 args 不再遮蔽 —— lambda 參數又被當成外面那個死碼
  "free_in_no_shadow": ("""    bound = {p.arg for p in ast.walk(a) if isinstance(p, ast.arg)}""",
                        """    bound = set()"""),
  # free_in 不帶 default —— `lambda x=dump: x()` 會被誤紅
  "free_in_no_default": ("""    return (reads - bound).union(*[names_in(d) for n, d in pairs if n in reads]
                                 or [set()])""",
                         """    return reads - bound"""),
  # free_in 帶所有 default(放太寬)—— body 根本沒讀到的參數也把 default 算成跑過
  "free_in_all_defaults": ("""if n in reads]""", """if pairs]"""),
  # `f = lambda…` 之後 `f()` 那個位置不再展開
  "bindings_in_branch": ("""            if isinstance(src, ast.Lambda):  # calling the name runs the body
                out[name] |= free_in(src)
""", ""),
  # `(lambda…)()` 就地呼叫那個位置不再展開
  "live_nodes_branch": ("""                    if isinstance(n.func, ast.Lambda):  # `(lambda: x)()` — #83
                        invoked |= free_in(n.func)
""", ""),
}
old, new = M[sys.argv[2]]
assert old in s, "mutation 目標不在 — 判準被改過了"
p.write_text(s.replace(old, new), encoding="utf-8")
print("mutation 已套用:", sys.argv[2])
PY
  set +e
  python "$CP/scripts/validate.py" --self-check 2>&1 | tail -3
  echo "exit ${PIPESTATUS[0]}  <- 非 0 是要的:knob 一改壞,self-check 就該紅"
  set -e
done

echo "==== STEP 5  副本還原後 -> 綠(證明上面判紅的是 mutation,不是副本壞了)===="
cp "$ROOT/scripts/validate.py" "$CP/scripts/validate.py"
python "$CP/scripts/validate.py" --self-check

echo "==== STEP 6  票上「不得放掉的天花板」逐條複驗 ===="
echo "---- 6a  --own-names(#81,13/0)"
python "$ROOT/scripts/qa/79-return-sweep.py" "$ROOT" --own-names | tail -2
echo "---- 6b  --return-carry(#79,6/0)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --return-carry | tail -2
echo "---- 6c  --callgraph(4/0)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --callgraph | tail -2
echo "---- 6d  --live-overapprox(5/0)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --live-overapprox | tail -2
echo "---- 6e  --bypass-position(6/0)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --bypass-position | tail -2
echo "---- 6f  --mention(13/0)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" | tail -2
echo "---- 6g  --positional(#58 原病,4/0)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --positional | tail -2
echo "---- 6h  #73 的三把尺(6/0 ×3)"
python "$ROOT/scripts/qa/73-reach-sweep.py" "$ROOT" --reach-shapes | tail -2
python "$ROOT/scripts/qa/73-reach-sweep.py" "$ROOT" --call-position | tail -2
python "$ROOT/scripts/qa/73-reach-sweep.py" "$ROOT" --alias | tail -2
echo "---- 6i  #75 的 --bind-quiet(11/0)"
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

echo "==== STEP 8  本輪同型全掃:lambda body 是 deferred code,live_nodes 那面沒停在 Lambda ===="
set +e
python "$ROOT/scripts/qa/83-deferred-sweep.py" "$ROOT" --deferred
echo "exit $?  <- 非 0 是本輪 finding"
echo "---- 對照組:#83 修之前(d192aa9)—— 同樣 7 條,證明不是 regression"
python "$ROOT/scripts/qa/83-deferred-sweep.py" "$ROOT" --deferred --prev83 | tail -2
set -e

echo "==== STEP 9  repo 本體沒被動過 ===="
python "$ROOT/scripts/validate.py"
git -C "$ROOT" status --short
