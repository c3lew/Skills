#!/usr/bin/env bash
# #97 QA walkthrough —— 判準從推論換成約定:pin 要在 `__main__` 第一層。
# 範圍 = 票上「覆蓋驗收項」六條 + 既有 regression suite + 全域修前對照
#        + 一把刻意寫寬、不套受測規則的第二把尺 + repo 進 repo 的 mutation 台。
# 全程 xtrace,指令與輸出同一份。
#
# 用法:bash scripts/qa/97-walkthrough.sh "$(mktemp -d)/qa97"
# 這支不碰 repo 本體 —— 每個情境都跑在拋棄式暫存目錄的 repo 副本上。
set -e
PS4='+ '
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
QA="$1"
rm -rf "$QA"; mkdir -p "$QA"
PRISTINE="$QA/pristine"
mkdir -p "$PRISTINE"
cp -r "$ROOT/scripts" "$ROOT/skills" "$ROOT/docs" "$PRISTINE/"

# 每個情境從 pristine 重開一份副本,回傳 validate 的 exit code(0=綠,1=吵)
fresh() { rm -rf "$QA/case"; cp -r "$PRISTINE" "$QA/case"; }
gate()  { set +e; python "$QA/case/scripts/validate.py"; echo "exit $?"; set -e; }

set -x

echo "==== STEP 1  regression suite(validate + 五支 self-check)===="
python "$ROOT/scripts/validate.py"
python "$ROOT/scripts/validate.py" --self-check
python "$ROOT/scripts/batch.py" --self-check
python "$ROOT/skills/build-batch/batch.py" --self-check
python "$ROOT/scripts/install.py" --self-check
python "$ROOT/scripts/hooks/triage-to-maintain.py" --self-check

echo "==== STEP 2  client 看得到的那張表,逐格真的跑一次 ===="

echo "---- 2a  pin 在 __main__ 第一層 → 綠(現況,不動任何東西)"
fresh; gate

echo "---- 2b  把 pin 從 __main__ 搬進 main() → 吵(#97 驗收項 2)"
fresh
python - "$QA/case/scripts/hooks/triage-to-maintain.py" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); s = p.read_text(encoding="utf-8")
pins = '    sys.stdout.reconfigure(encoding="utf-8")\n    sys.stdin.reconfigure(encoding="utf-8")\n'
assert pins in s
s = s.replace(pins, "")                        # 從 __main__ 第一層拿掉
s = s.replace("def main():\n", "def main():\n" + pins, 1)   # 搬進 main()
p.write_text(s, encoding="utf-8")
PY
sed -n '/^def main/,+3p;/^if __name__/,+8p' "$QA/case/scripts/hooks/triage-to-maintain.py"
gate

echo "---- 2b2  pin 只寫在模組層 → 吵(驗收原句列的第三種,#97 驗收項 2)"
fresh
cat > "$QA/case/scripts/qa/zz-case-module-level.py" <<'PY'
import sys
sys.stdout.reconfigure(encoding="utf-8")
if __name__ == "__main__":
    print("中文")
PY
cat "$QA"/case/scripts/qa/zz-case-*.py
gate

echo "---- 2c  pin 巢狀進 __main__ 裡的 if → 吵(死碼裡的 pin 不算數)"
fresh
python - "$QA/case/scripts/hooks/triage-to-maintain.py" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); s = p.read_text(encoding="utf-8")
pins = '    sys.stdout.reconfigure(encoding="utf-8")\n    sys.stdin.reconfigure(encoding="utf-8")\n'
assert pins in s
s = s.replace(pins, "    if True:\n    " + pins.replace("\n    ", "\n        ").rstrip() + "\n")
p.write_text(s, encoding="utf-8")
PY
sed -n '/^if __name__/,+8p' "$QA/case/scripts/hooks/triage-to-maintain.py"
gate

echo "---- 2d  一支只寫 bytes、沒有 pin 的腳本 → 吵(.buffer 不再是免死金牌)"
fresh
cat > "$QA/case/scripts/qa/zz-case-buffer.py" <<'PY'
import sys
if __name__ == "__main__":
    sys.stdout.buffer.write("中文".encode("utf-8"))
PY
cat "$QA"/case/scripts/qa/zz-case-*.py
gate

echo "---- 2e  有 __main__、一行 print 都沒有 → 吵(print 豁免下架)"
fresh
cat > "$QA/case/scripts/qa/zz-case-noprint.py" <<'PY'
import sys
if __name__ == "__main__":
    pass
PY
cat "$QA"/case/scripts/qa/zz-case-*.py
gate

echo "---- 2f  碰了 stdin 但只 pin stdout → 吵(碰 stdin 看 AST,不看字串)"
fresh
cat > "$QA/case/scripts/qa/zz-case-stdin.py" <<'PY'
import sys
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(sys.stdin.read())
PY
cat "$QA"/case/scripts/qa/zz-case-*.py
gate

echo "---- 2g  只在字串裡「提到」sys.stdin 的檔,不欠 stdin pin → 綠(2f 的反面)"
fresh
cat > "$QA/case/scripts/qa/zz-case-stdin-prose.py" <<'PY'
import sys
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print("記得寫 sys.stdin.reconfigure(encoding='utf-8')")
PY
cat "$QA"/case/scripts/qa/zz-case-*.py
gate

echo "---- 2h  兩個 __main__ 只釘一個 → 吵"
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

echo "---- 2i  宣告過的天花板(#67):反著寫 __name__ 不認 → 綠,不吵"
fresh
cat > "$QA/case/scripts/qa/zz-case-reversed.py" <<'PY'
import sys
if "__main__" == __name__:
    print("要開")
PY
cat "$QA"/case/scripts/qa/zz-case-*.py
gate

echo "---- 2i2  天花板的對照組:同一份 fixture 只把寫法換成正規的 → 吵"
echo "         沒有這格,2i 的綠分不出「不認這種寫法」還是「認了但剛好有 pin」"
fresh
cat > "$QA/case/scripts/qa/zz-case-canonical.py" <<'PY'
import sys
if __name__ == "__main__":
    print("要開")
PY
cat "$QA"/case/scripts/qa/zz-case-*.py
gate

echo "---- 2i3  天花板的另一半:in (...) 這種等價寫法也不認 → 綠"
fresh
cat > "$QA/case/scripts/qa/zz-case-in-tuple.py" <<'PY'
import sys
if __name__ in ("__main__",):
    print("要開")
PY
cat "$QA"/case/scripts/qa/zz-case-*.py
gate

echo "==== STEP 3  修前對照:同一份母體,舊判準(5e3646c)vs 新判準 ===="
git -C "$ROOT" show 5e3646c:scripts/validate.py > "$QA/validate_old.py"
python - "$ROOT" "$QA" <<'PY'
import sys, pathlib, importlib.util, subprocess, tempfile
sys.stdout.reconfigure(encoding="utf-8")
ROOT, QA = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
def load(n, p):
    s = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m); return m
new = load("v_new", ROOT / "scripts" / "validate.py")
old = load("v_old", QA / "validate_old.py")
for c in ["5e3646c", "39109fe", "5675b1a"]:
    t = QA / f"tree-{c}"; t.mkdir(parents=True, exist_ok=True)
    subprocess.run(f'git -C "{ROOT.as_posix()}" archive {c} | tar -x -C "{t.as_posix()}"',
                   shell=True, check=True)
    for name, mod in (("舊判準", old), ("新判準", new)):
        errs = mod.stream_encoding_issues(t)
        print(f"{c}  {name}: {len(errs)} 紅")
        for e in errs:
            print("      " + e.split(" — ")[0])
PY

echo "==== STEP 3b  修前對照:QA 照驗收原句寫的兩面母體 18 格,新舊判準各跑一次 ===="
python "$ROOT/scripts/qa/97-prevdiff.py"

echo "==== STEP 4  第二把尺:刻意寫寬、不套受測規則的獨立掃描 ===="
python "$ROOT/scripts/qa/97-wide.py" "$ROOT"

echo "==== STEP 5  mutation 台(進 repo 的那份):11 個 knob 逐一改壞 ===="
python "$ROOT/scripts/qa/97-mutate.py" --run

echo "==== STEP 6  票上其餘 AC:原型 probe + 12 個 function 真的不在了 ===="
python "$ROOT/scripts/qa/96-newrule-probe.py" "$ROOT"
set +e
grep -nE "^def (live_nodes|consumes|asyncio_graph|binds|nodes_in|runs|free_in|names_in|bindings_in|from_asyncio|own_scope|drives)\b" "$ROOT/scripts/validate.py"
echo "exit $?  <- 1 是要的:12 個 function 一個都不在了"
set -e
wc -l "$ROOT/scripts/validate.py"

set +x
echo
echo "==== walkthrough 走完 ===="
