#!/usr/bin/env bash
# #84 QA walkthrough — lambda 邊界的第三面(live 語句的 walk 停在 Lambda)。
# 範圍 = #84 的重現 scenario + 既有 regression suite + 拿修法自己的尺做的同型全掃。
# 全程 xtrace,指令與輸出同一份。
#
# 用法:bash scripts/qa/84-walkthrough.sh "$(mktemp -d)/qa84"
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

echo "==== STEP 2  #84 的重現 scenario 原樣重跑(票上的母體 11,修前 7 誤放)===="
set +e
python "$ROOT/scripts/qa/83-deferred-sweep.py" "$ROOT" --deferred
echo "exit $?  <- 非 0 是要的:第七格是票上寫死的天花板,不改成 GREEN"
set -e

echo "==== STEP 3  對照組:#84 修之前(4c58eab)同一組 11 條裡 7 條誤放 ===="
set +e
python "$ROOT/scripts/qa/83-deferred-sweep.py" "$ROOT" --deferred --prev83 | tail -2
echo "exit ${PIPESTATUS[0]}  <- 非 0 是要的:對照組該紅"
set -e

echo "==== STEP 4  票上宣稱的 mutation 咬合:七個 knob 逐一改壞 -> self-check 要轉紅 ===="
for M in nodes_in_no_lambda_stop nodes_in_no_defaults live_nodes_walk_invoked live_nodes_walk_return no_through no_callback_arg no_bound_lambda; do
  echo "---- 4.$M"
  cp "$ROOT/scripts/validate.py" "$CP/scripts/validate.py"
  python - "$CP" "$M" <<'PY'
import pathlib, sys
sys.stdout.reconfigure(encoding="utf-8")
p = pathlib.Path(sys.argv[1]) / "scripts" / "validate.py"
s = p.read_text(encoding="utf-8")
M = {
  # nodes_in 不再停在 Lambda —— #84 的原病,退回 ast.walk 的行為
  "nodes_in_no_lambda_stop": ("""        if isinstance(n, ast.Lambda) and n not in through:
            stack += [d for d in n.args.defaults + n.args.kw_defaults if d]
            continue
""", ""),
  # 停了但 parameter default 不推回去 —— default 在 literal 位置就 evaluate,會誤紅
  "nodes_in_no_defaults": ("""            stack += [d for d in n.args.defaults + n.args.kw_defaults if d]
""", ""),
  # 決定「誰被 invoke」那半退回 ast.walk
  "live_nodes_walk_invoked": ("""            for n in nodes_in(stmt):""",
                              """            for n in ast.walk(stmt):"""),
  # 回傳的 node list(bypass 位置查表用的那份)退回 ast.walk
  "live_nodes_walk_return": ("""            return [n for stmt in body for n in nodes_in(stmt, through)]""",
                             """            return [n for stmt in body for n in ast.walk(stmt)]"""),
  # through 不再帶進去 —— 真的被呼叫的 lambda body 裡的 bypass 查不到
  "no_through": ("""for n in nodes_in(stmt, through)]""", """for n in nodes_in(stmt)]"""),
  # callback 引數位置(`sorted(key=lambda…)`)不再算成被呼叫
  "no_callback_arg": ("""                        if isinstance(arg, ast.Lambda):  # `sorted(key=…)` — #84
                            invoked |= free_in(arg)
                            called.add(arg)
""", ""),
  # 綁到名字之後被呼叫的 lambda 不再進 through
  "no_bound_lambda": ("""                    for name, src in binding_pairs(n):
                        if isinstance(src, ast.Lambda):
                            lam_of[name].add(src)
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
echo "---- 6a  --lambda-scope(#83,9/0)"
python "$ROOT/scripts/qa/81-lambda-sweep.py" "$ROOT" --lambda-scope | tail -2
echo "---- 6b  --own-names(#81,13/0)"
python "$ROOT/scripts/qa/79-return-sweep.py" "$ROOT" --own-names | tail -2
echo "---- 6c  --return-carry(#79,6/0)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --return-carry | tail -2
echo "---- 6d  --callgraph(4/0)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --callgraph | tail -2
echo "---- 6e  --live-overapprox(5/0)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --live-overapprox | tail -2
echo "---- 6f  --bypass-position(6/0)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --bypass-position | tail -2
echo "---- 6g  --mention(13/0)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" | tail -2
echo "---- 6h  --positional(#58 原病,4/0)"
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --positional | tail -2
echo "---- 6i  #73 的三把尺(6/0 ×3)"
python "$ROOT/scripts/qa/73-reach-sweep.py" "$ROOT" --reach-shapes | tail -2
python "$ROOT/scripts/qa/73-reach-sweep.py" "$ROOT" --call-position | tail -2
python "$ROOT/scripts/qa/73-reach-sweep.py" "$ROOT" --alias | tail -2
echo "---- 6j  #75 的 --bind-quiet(11/0)"
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
echo "---- 7e  --arg-widen(未修)"
python "$ROOT/scripts/qa/73-reach-sweep.py" "$ROOT" --arg-widen | tail -2
echo "---- 7f  #75 的另兩把尺(#77 / #78,未修)"
python "$ROOT/scripts/qa/75-binding-sweep.py" "$ROOT" --binding-shapes | tail -2
python "$ROOT/scripts/qa/75-binding-sweep.py" "$ROOT" --header | tail -2
echo "---- 7g  #79 的 --result-called(#82,未修)"
python "$ROOT/scripts/qa/79-return-sweep.py" "$ROOT" --result-called | tail -2
set -e

echo "==== STEP 8  本輪同型全掃:generator body 也是 deferred code,nodes_in 只停在 Lambda ===="
set +e
python "$ROOT/scripts/qa/84-generator-sweep.py" "$ROOT" --generator
echo "exit $?  <- 非 0 是本輪 finding"
echo "---- 對照組:#84 修之前(4c58eab)—— 同樣 6 條,證明不是 regression"
python "$ROOT/scripts/qa/84-generator-sweep.py" "$ROOT" --generator --prev84 | tail -2
set -e

echo "==== STEP 9  repo 本體沒被動過 ===="
python "$ROOT/scripts/validate.py"
git -C "$ROOT" status --short
