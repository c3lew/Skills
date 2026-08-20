#!/usr/bin/env bash
# #98 QA walkthrough —— 新判準的入口缺口:守門到底看到了哪些檔。
# 範圍 = 票上「覆蓋驗收項」三條 + 既有 regression suite + 全域修前對照
#        + 一把刻意寫寬、不套受測規則的第二把尺 + mutation 台(含基準線控制組)。
# 全程 xtrace,指令與輸出同一份。
#
# 用法:bash scripts/qa/98-walkthrough.sh "$(mktemp -d)/qa98"
# 這支不碰 repo 本體 —— 每個情境都跑在拋棄式暫存目錄的 repo 副本上。
set -e
PS4='+ '
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
QA="$1"
rm -rf "$QA"; mkdir -p "$QA"
PRISTINE="$QA/pristine"
mkdir -p "$PRISTINE"
cp -r "$ROOT/scripts" "$ROOT/skills" "$ROOT/docs" "$PRISTINE/"

fresh() { rm -rf "$QA/case"; cp -r "$PRISTINE" "$QA/case"; }
gate()  { set +e; python "$QA/case/scripts/validate.py"; echo "exit $?"; set -e; }
probe() { set +e; python "$ROOT/scripts/qa/96-newrule-probe.py" "$QA/case"; set -e; }

set -x

echo "==== STEP 1  regression suite(validate + 五支 self-check)===="
python "$ROOT/scripts/validate.py"
python "$ROOT/scripts/validate.py" --self-check
python "$ROOT/scripts/batch.py" --self-check
python "$ROOT/skills/build-batch/batch.py" --self-check
python "$ROOT/scripts/install.py" --self-check
python "$ROOT/scripts/hooks/triage-to-maintain.py" --self-check

echo "==== STEP 2  覆蓋驗收項 1:一個檔有幾個 __main__ 就檢查幾個(#69)===="

echo "---- 2a  兩個 __main__,只釘第一個 → 吵"
fresh
cat > "$QA/case/scripts/qa/zz-case-two-mains.py" <<'PY'
import sys
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print("一")
if __name__ == "__main__":
    print("二")
PY
cat "$QA"/case/scripts/qa/zz-case-*.py
gate

echo "---- 2b  對照組:同一份 fixture 改成只釘**第二個** → 一樣吵"
echo "         沒有這格,2a 的紅分不出是「每個都檢查」還是「只看最後一個」"
fresh
cat > "$QA/case/scripts/qa/zz-case-two-mains-second.py" <<'PY'
import sys
if __name__ == "__main__":
    print("一")
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print("二")
PY
cat "$QA"/case/scripts/qa/zz-case-*.py
gate

echo "---- 2c  兩個都釘 → 綠(2a/2b 的反面)"
fresh
cat > "$QA/case/scripts/qa/zz-case-two-mains-ok.py" <<'PY'
import sys
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print("一")
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print("二")
PY
cat "$QA"/case/scripts/qa/zz-case-*.py
gate

echo "---- 2d  第二把尺(96-newrule-probe)對同一格要給**一樣**的答案"
echo "         #69 這條的實體就是兩把尺原本相反:validate 是 all、probe 是 any"
fresh
cat > "$QA/case/scripts/qa/zz-case-two-mains.py" <<'PY'
import sys
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print("一")
if __name__ == "__main__":
    print("二")
PY
probe
echo "---- 2d2  同一格拿修前的 probe(91b6b98,寫的是 any)跑 —— 應該放行"
git -C "$ROOT" show 91b6b98:scripts/qa/96-newrule-probe.py > "$QA/probe_old.py"
set +e; python "$QA/probe_old.py" "$QA/case"; set -e

echo "==== STEP 3  覆蓋驗收項 2:檔案 parse 不動要判 fail(#66)===="

echo "---- 3a  一支打錯字的 .py → 吵,訊息要帶檔名 + 原因"
fresh
printf 'def f(\n' > "$QA/case/scripts/qa/zz-case-typo.py"
cat "$QA/case/scripts/qa/zz-case-typo.py"
gate

echo "---- 3b  同一格把字打對 → 綠(3a 的反面)"
fresh
printf 'def f():\n    return 1\n' > "$QA/case/scripts/qa/zz-case-typo.py"
gate

echo "---- 3c  一支 cp950 存的 .py → 判紅,不是整支 traceback 掀掉"
fresh
python - "$QA/case/scripts/qa/zz-case-cp950.py" <<'PY'
import sys, pathlib
pathlib.Path(sys.argv[1]).write_text("x = '要開'\n", encoding="cp950")
PY
gate

echo "==== STEP 4  覆蓋驗收項 3:__main__.py 不被 __ 開頭的過濾誤傷(#68)===="

echo "---- 4a  package entry point 沒 pin → 吵"
fresh
mkdir -p "$QA/case/scripts/pkg"
cat > "$QA/case/scripts/pkg/__main__.py" <<'PY'
import sys
if __name__ == "__main__":
    print("要開")
PY
cat "$QA/case/scripts/pkg/__main__.py"
gate

echo "---- 4b  補上 pin → 綠(4a 的反面)"
fresh
mkdir -p "$QA/case/scripts/pkg"
cat > "$QA/case/scripts/pkg/__main__.py" <<'PY'
import sys
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print("要開")
PY
gate

echo "---- 4c  過濾還是擋得住它本來要擋的:__pycache__ / .venv / .hidden.py 三格都沒 pin → 仍綠"
fresh
mkdir -p "$QA/case/scripts/__pycache__" "$QA/case/.venv"
for f in "$QA/case/scripts/__pycache__/zz.py" "$QA/case/.venv/zz.py" "$QA/case/scripts/.hidden.py"; do
  printf 'import sys\nif __name__ == "__main__":\n    print("x")\n' > "$f"
done
gate

echo "==== STEP 5  修前對照:同一份母體 22 格,修前(91b6b98)vs 修後 ===="
python "$ROOT/scripts/qa/98-prevdiff.py"

echo "==== STEP 6  第二把尺:刻意寫寬、不套受測規則的入口掃描 ===="
echo "---- 6a  對 repo 本體"
python "$ROOT/scripts/qa/98-wide.py" "$ROOT"
echo "---- 6b  對一份真的有被過濾檔的母體(repo 本體剛好一格都沒過濾掉,量不到 #68 那條軸)"
fresh
mkdir -p "$QA/case/scripts/__pycache__" "$QA/case/.venv" "$QA/case/scripts/pkg"
for f in "$QA/case/scripts/__pycache__/zz.py" "$QA/case/.venv/zz.py" "$QA/case/scripts/.hidden.py"; do
  printf 'import sys\nif __name__ == "__main__":\n    print("x")\n' > "$f"
done
printf 'import sys\nif __name__ == "__main__":\n    print("x")\n' > "$QA/case/scripts/pkg/__main__.py"
python "$ROOT/scripts/qa/98-wide.py" "$QA/case" | tail -20

echo "==== STEP 7  mutation 台:15 個 knob + 基準線控制組 ===="
echo "---- 7a  repo 進 repo 的那份"
set +e; python "$ROOT/scripts/qa/97-mutate.py" --run; echo "exit $?"; set -e
echo "---- 7b  控制組:同一個 harness,knob 一個都不套 —— 應該 exit 0"
set +e; python "$ROOT/scripts/qa/98-mutate-control.py"; echo "exit $?"; set -e

echo "==== STEP 8  票上其餘 AC:原型 probe 對 repo 本體全綠 ===="
python "$ROOT/scripts/qa/96-newrule-probe.py" "$ROOT"

set +x
echo
echo "==== walkthrough 走完 ===="
