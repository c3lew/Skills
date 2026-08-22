#!/usr/bin/env bash
# #114 QA walkthrough —— 給人照抄的指令代換完照字面貼進 shell 要跑得動,
# 以及新守門 `pasteable_command_issues` 的紅綠兩面。
# 範圍 = #114 完工定義四條(bug fix 票:重現 scenario + regression suite)。
#
# 這片的交付物是散文(SKILL.md)+ 守門(scripts/validate.py),沒有 web UI,
# 所以「a11y snapshot」的等價物 = 每條完工定義一段可重跑的實測 transcript
# (指令 + 真實輸出 + 引用到的散文原文行號)。
#
# 用法:bash scripts/qa/114-walkthrough.sh "$(mktemp -d)/qa114"
# 不碰 repo 本體 —— 修前對照跑在拋棄式暫存目錄的 `git archive` 副本上。
# exit 非 0 = 有格子不合預期。
PS4='+ '
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
QA="${1:?usage: 114-walkthrough.sh <workdir>}"
rm -rf "$QA"; mkdir -p "$QA"
cd "$ROOT" || exit 1

FAILED=0
BUILD="skills/build/SKILL.md"
PREFIX_COMMIT="0de51ec"   # #114 修之前那個 commit(交付版的直接前一手)

ok()   { echo "OK   $*"; }
bad()  { echo "FAIL $*"; FAILED=1; }
check(){ if [ "$2" = "$3" ]; then ok "$1 ($2)"; else bad "$1 —— 期望 $3,實得 $2"; fi; }

# winpath: Python 在 Windows 上不認 MSYS 的 /tmp —— 會解成 C:\tmp,對照組整個
# 讀不到檔卻回「0 筆」,看起來就跟全綠一樣。這裡強制轉成原生路徑。
winpath() { if command -v cygpath >/dev/null 2>&1; then cygpath -w "$1"; else printf '%s' "$1"; fi; }

echo "==== A1  交付版 $BUILD:37 的指令,代換後照字面貼進 bash ===="
# 指令從檔案原地抽出來,不是手打 —— 手打的話測的是我打了什麼,不是檔案寫了什麼
CMD=$(python - "$BUILD" <<'PY'
import re, sys
line = open(sys.argv[1], encoding='utf-8').read().split('\n')[36]
print([c for c in re.findall(r'`([^`]+)`', line) if 'gh ' in c][0].replace('<N>', '113'))
PY
)
echo "抽出的指令(代換 <N> -> 113):$CMD"
bash -c "$CMD" > "$QA/a1.txt" 2>&1
check "A1 貼進 bash 跑得動" "$?" "0"
head -2 "$QA/a1.txt"

echo
echo "==== A2  對照組:修前那版同一行,照同一條路貼進 bash ===="
# 先落檔再讀 —— `git show ... | python - <<EOF` 會讓 heredoc 蓋掉 pipe 的 stdin,
# python 讀到的是 script 本身,拿不到檔案內容。
git show "$PREFIX_COMMIT:$BUILD" > "$QA/pre-build.md"
PRE_CMD=$(python - "$QA/pre-build.md" <<'PY'
import re, sys
line = open(sys.argv[1], encoding='utf-8').read().split('\n')[36]
print([c for c in re.findall(r'`([^`]+)`', line) if 'gh ' in c][0].replace('N', '113'))
PY
)
echo "抽出的指令:$PRE_CMD"
bash -c "$PRE_CMD" > "$QA/a2.txt" 2>&1
if grep -q 'accepts 1 arg' "$QA/a2.txt"; then
  ok 'A2 修前那版參數被 # 吃掉(accepts 1 arg(s), received 0)—— 這就是 #114 的 bug'
  cat "$QA/a2.txt"
else
  bad "A2 對照組沒重現 —— 修前那版應該要因為 # 而丟參數"
fi

echo
echo "==== A3  完工定義 3:regression suite ===="
python scripts/validate.py            > "$QA/v.txt"  2>&1; check "validate"            "$?" "0"
python scripts/validate.py --self-check > "$QA/sc.txt" 2>&1; check "validate --self-check" "$?" "0"
python scripts/qa/97-mutate.py  --run > "$QA/m97.txt" 2>&1; check "97-mutate"          "$?" "0"
python scripts/qa/107-mutate.py --run > "$QA/m107.txt" 2>&1; check "107-mutate"        "$?" "0"
python scripts/qa/96-newrule-probe.py . > "$QA/p96.txt" 2>&1; check "96-newrule-probe" "$?" "0"

echo
echo "==== A4  修前對照:新守門對修之前那份母體咬不咬得到 ===="
PRE="$QA/prefix"; mkdir -p "$PRE"
git archive "$PREFIX_COMMIT" | tar -x -C "$PRE"
python - "$(winpath "$PRE")" "$ROOT" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[2]) / 'scripts'))
sys.stdout.reconfigure(encoding='utf-8')
import validate as v
for label, root in (('修前', sys.argv[1]), ('交付版', sys.argv[2])):
    p = Path(root).resolve()
    assert (p / 'skills' / 'build' / 'SKILL.md').is_file(), f'{label} 對照組沒讀到檔'
    errs = v.pasteable_command_issues(p)
    print(f'{label}: {len(errs)} 筆')
    for e in errs:
        print('   ', e)
PY
check "A4 修前對照跑完" "$?" "0"

echo
echo "==== A5  第二把尺(不讀守門判準,問 bash 自己)===="
python scripts/qa/114-paste.py . > "$QA/wide-now.txt" 2>&1
python scripts/qa/114-paste.py "$(winpath "$PRE")" > "$QA/wide-pre.txt" 2>&1
PRE_HIT=$(grep -c "^$BUILD:37: .gh issue view #N" "$QA/wide-pre.txt")
NOW_HIT=$(grep -c "^$BUILD:37: .gh issue view" "$QA/wide-now.txt")
check "A5 寬尺在修前樹撈到 :37" "$PRE_HIT" "1"
check "A5 寬尺在交付版沒撈到 :37" "$NOW_HIT" "0"
grep '吃掉 token' "$QA/wide-now.txt"

echo
echo "==== A6  完工定義 4:#113 的三條 finding 還在修好的狀態 ===="
python scripts/qa/113-wide.py . > "$QA/w113.txt" 2>&1
BUILD_HITS=$(grep -c "^  $BUILD —— " "$QA/w113.txt")
check "A6 113-wide 對 $BUILD 零筆" "$BUILD_HITS" "0"

echo
if [ "$FAILED" = 0 ]; then echo "ALL GREEN"; else echo "有格子不合預期"; fi
exit "$FAILED"
