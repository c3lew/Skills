#!/usr/bin/env bash
# #60 QA walkthrough — stream_encoding_issues 的豁免從全檔 substring 改成 AST 判準(bug fix)。
# 全程 xtrace,指令與輸出同一份。
#
# 用法:bash scripts/qa/60-walkthrough.sh "$(mktemp -d)/qa60"
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

echo "==== STEP 1b  self-check 真的咬得到「散文當 code」:副本裡把豁免改回 substring -> self-check 轉紅 ===="
grep -n 'norm(bypass) in live' "$CP/scripts/validate.py"
sed -i 's|if norm(bypass) in live or|if bypass in py.read_text(encoding="utf-8") or|' "$CP/scripts/validate.py"
grep -n 'bypass in py.read_text' "$CP/scripts/validate.py"
set +e
python "$CP/scripts/validate.py" --self-check
echo "exit $?  <- 非 0 是要的:#60 的病一還原,self-check 就該紅"
set -e
# 還原副本,後面幾步要用乾淨的它
cp "$ROOT/scripts/validate.py" "$CP/scripts/validate.py"

echo "==== STEP 2  副本未動過 -> 綠(證明後面判紅的是 mutation,不是副本壞了)===="
python "$CP/scripts/validate.py"

echo "==== STEP 3  票上的重現 scenario 原樣重跑:裸 print + 一行「沒走 sys.stdout.buffer」註解 ===="
cat > "$CP/scripts/_repro60.py" <<'PY'
if __name__ == "__main__":
    print("要開的票")
    # 這裡沒走 sys.stdout.buffer
PY
set +e
python "$CP/scripts/validate.py"
echo "exit $?"
set -e
rm "$CP/scripts/_repro60.py"

echo "==== STEP 4  同型全掃:「提到」的所有寫法 vs 「用到」的所有寫法 ===="
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT"

echo "==== STEP 5  不得誤紅:真的走 buffer 的 triage-to-maintain.py 仍被豁免 ===="
grep -n 'sys.stdout.buffer' "$ROOT/scripts/hooks/triage-to-maintain.py"
python - "$ROOT" <<'PY'
import sys, pathlib
sys.path.insert(0, sys.argv[1] + "/scripts")
sys.stdout.reconfigure(encoding="utf-8")
import validate as V
repo = pathlib.Path(sys.argv[1])
errs = [e for e in V.stream_encoding_issues(repo) if "triage-to-maintain" in e]
print("triage-to-maintain.py 的 error 數 ->", len(errs))
assert errs == []
PY

echo "==== STEP 6  #58 的原病沒退步:pin 放在 main() 而不是 __main__ block -> 仍判紅 ===="
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --positional

echo "==== STEP 6b  上一輪的 blocking(#65)已修:靜默跳過三條路只剩 SyntaxError(#66,known issue)===="
set +e
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --skips
echo "exit $?  <- 非 0 是預期的:剩下那條是 #66,已開票排期"
set -e

echo "==== STEP 6c  對照組:同樣三個 case 在改之前(d3cc9ed^)是判紅的 ===="
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --skips --old

echo "==== STEP 6d  上一輪的 blocking(#70)已修:豁免的位置判準(AC1 原句的「會執行的位置」)全綠 ===="
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --bypass-position

echo "==== STEP 6e  對照組:同一組 case 在改之前(d3cc9ed^)4 條不合 -> 這輪真的抬了天花板 ===="
set +e
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --bypass-position --old
echo "exit $?  <- 非 0 是要的:對照組該紅"
set -e

echo "==== STEP 6f  AC1 括號裡的第二支路(「或檔案裡沒有裸 print(」)有沒有實作 — 純證據,不是 finding ===="
# AC1 是「或」:兩支實作路擇一即可。這一步證明守門走的是第一支(bypass 語意判準),
# 第二支完全沒實作 — 沒有裸 print( 的檔案照樣要求 pin。所以 AC1 只能拿第一支來判。
python - "$ROOT" <<'PY'
import sys, tempfile, pathlib
sys.path.insert(0, sys.argv[1] + "/scripts")
sys.stdout.reconfigure(encoding="utf-8")
import validate as V

CASES = {
    "整檔沒有裸 print(,也沒 pin/bypass": 'import sys\nif __name__ == "__main__":\n    x = 1\n',
    "print 只出現在 comment 裡,不是真的呼叫": 'import sys\nif __name__ == "__main__":\n    # 這裡不用 print(\n    x = 1\n',
    "只寫檔案、完全不印到 console": 'import sys\nimport pathlib\nif __name__ == "__main__":\n    pathlib.Path("o.txt").write_text("要開的票", encoding="utf-8")\n',
}
tmp = pathlib.Path(tempfile.mkdtemp())
for name, src in CASES.items():
    (tmp / "probe.py").write_text(src, encoding="utf-8")
    got = "RED" if V.stream_encoding_issues(tmp) else "GREEN"
    print(f"{name.ljust(34)}  第二支路會判 GREEN  實際 {got}")
print("\n三條都 RED -> 第二支路沒實作(守門不看 print,只看 pin/bypass)")
PY

echo "==== STEP 6g  本輪同型全掃(一):可達性判準只裝在 bypass 那半,pin 那半沒有 ===="
# #70 拿「死碼裡的 bypass 不算數」當尺。同一把尺量 pin:__main__ block 裡跑不到的
# reconfigure 算不算 pin 到了?判準同型,實作只做了一半。
set +e
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --pin-position
echo "exit $?  <- 非 0 是本輪 finding"
set -e

echo "==== STEP 6h  對照組:同一組 case 在 d3cc9ed^ 也 4 條不合 -> 天花板沒抬,不是 regression ===="
set +e
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --pin-position --old
echo "exit $?"
set -e

echo "==== STEP 6i  本輪同型全掃(二):拿 live_exprs docstring 的字面重新推導 ===="
# docstring 逐字:「透過 alias / handler dict / callback 才走到的 bypass 仍算 live」。
# written-evidence:第二個人拿字面重推,要推得出同一個結果。
set +e
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --callgraph
echo "exit $?  <- 非 0 是本輪 finding"
set -e

echo "==== STEP 6j  對照組:同一組 case 在 d3cc9ed^ 全綠 -> 這 3 條誤紅是 #70 修法引入的 ===="
python "$ROOT/scripts/qa/60-mention-sweep.py" "$ROOT" --callgraph --old

echo "==== STEP 7  repo 本體沒被動過 ===="
python "$ROOT/scripts/validate.py"
git -C "$ROOT" status --short
