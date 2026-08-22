#!/usr/bin/env bash
# #112 QA walkthrough —— 守門錨點從「排版/關鍵字」改成「宣告本身」。
# 範圍 = #112 票上「重現與現況」表的 A1–A4 四格原句 + 完工定義的「順手一併修」那條。
# 這片的交付物是散文(skills/qa/SKILL.md、AGENTS.md)+ 守門(scripts/validate.py),
# 沒有 web UI,所以「a11y snapshot」的等價物 = 每條驗收原句一段可重跑的 transcript
# (指令 + 真實輸出 + 判定所倚賴的散文原文行號)。
#
# 用法:bash scripts/qa/112-walkthrough.sh "$(mktemp -d)/qa112"
# 這支不碰 repo 本體 —— 每個情境都跑在拋棄式暫存目錄的 repo 副本上。
# exit 非 0 = 有格子不合預期。
PS4='+ '
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
QA="${1:?usage: 112-walkthrough.sh <workdir>}"
rm -rf "$QA"; mkdir -p "$QA"
PRISTINE="$QA/pristine"
mkdir -p "$PRISTINE"
cp -r "$ROOT"/* "$PRISTINE/"   # .git 是隱藏檔,* 不會帶進來

FAILED=0
QASKILL="skills/qa/SKILL.md"

fresh() { rm -rf "$QA/case"; cp -r "$PRISTINE" "$QA/case"; }

# gate:在副本上跑守門,完整輸出留在 transcript
gate() {
  set +e
  python "$QA/case/scripts/validate.py" > "$QA/out.txt" 2>&1
  GATE_EXIT=$?
  cat "$QA/out.txt"
  echo "exit $GATE_EXIT"
  GATE_JUDGE="$(grep -c -e 'judge' -e '並行池' "$QA/out.txt" || true)"
  echo "judge/並行池 錯誤行數: $GATE_JUDGE"
}

# expect <red|green> <格子說明>
expect() {
  local want="$1" what="$2"
  if [ "$want" = "red" ]; then
    if [ "$GATE_EXIT" -ne 0 ] && [ "$GATE_JUDGE" -gt 0 ]; then
      echo "RESULT PASS ($what):預期紅、實際紅,且錯誤指名 judge/並行池"
    else
      echo "RESULT FAIL ($what):預期紅 exit!=0 且有 judge 錯誤,實際 exit=$GATE_EXIT judge行數=$GATE_JUDGE"
      FAILED=1
    fi
  else
    if [ "$GATE_EXIT" -eq 0 ]; then
      echo "RESULT PASS ($what):預期綠、實際綠"
    else
      echo "RESULT FAIL ($what):預期綠,實際 exit=$GATE_EXIT"
      FAILED=1
    fi
  fi
}

# expect_msg <want-substr> <must-not-substr> <格子說明> —— 訊息要指到對的地方
expect_msg() {
  local want="$1" nope="$2" what="$3"
  if grep -q -- "$want" "$QA/out.txt" && ! grep -q -- "$nope" "$QA/out.txt"; then
    echo "RESULT PASS ($what):訊息含「$want」、不含「$nope」"
  else
    echo "RESULT FAIL ($what):期望訊息含「$want」且不含「$nope」,實際 ——"
    cat "$QA/out.txt"
    FAILED=1
  fi
}

# assert_grep <pattern> <file> <格子說明> / refute_grep 同理但要求沒有
assert_grep() {
  set +e
  if grep -n -- "$1" "$2"; then
    echo "RESULT PASS ($3):$2 找得到「$1」"
  else
    echo "RESULT FAIL ($3):$2 找不到「$1」"
    FAILED=1
  fi
}
refute_grep() {
  set +e
  # 檔案路徑一定要引號 —— 這個 repo 的路徑含空白,沒引號 grep 會去找不存在的檔然後
  # 「找不到」,斷言就變成永遠 PASS(#112 QA judge 抓到的空斷言)
  if [ ! -f "$2" ]; then
    echo "RESULT FAIL ($3):$2 不存在 —— 斷言會是空的"
    FAILED=1
    return
  fi
  grep -n -- "$1" "$2"
  if grep -q -- "$1" "$2"; then
    echo "RESULT FAIL ($3):$2 還在引「$1」"
    FAILED=1
  else
    echo "RESULT PASS ($3):$2 已經不引「$1」"
  fi
}

# 儀器自檢:refute_grep 對一個「確定在檔案裡」的字串必須 FAIL。不自檢的話,
# 上面那種空斷言會長得跟真的通過一模一樣。
selfcheck_refute() {
  local before="$FAILED"
  FAILED=0
  refute_grep "$1" "$2" "儀器自檢(預期 FAIL)" > /dev/null 2>&1
  if [ "$FAILED" -eq 1 ]; then
    echo "RESULT PASS (儀器自檢):refute_grep 對確實存在的「$1」有判 FAIL,斷言不是空的"
    FAILED="$before"
  else
    echo "RESULT FAIL (儀器自檢):refute_grep 對確實存在的「$1」沒判 FAIL —— 斷言是空的"
    FAILED=1
  fi
}

set -x

echo "==== 出貨版散文原文(所有判定倚賴的行號)===="
echo "---- §2 並行池:三線同時開(含 lane 表與『這張表就是池的宣告』)"
sed -n '24,50p' "$ROOT/$QASKILL" | cat -n
echo "---- §3 標題自己就含 judge 與『walkthrough 之後』,正文那句才是 load-bearing 的約束"
sed -n '77,86p' "$ROOT/$QASKILL" | cat -n
echo "---- 絕對行號版"
grep -n -e '^## 2\.' -e '^| lane' -e '^## 3\.' -e '排序約束' "$ROOT/$QASKILL"

echo '==== A1  票上原句:「並行池 lane 表插一列 `| judge | 逐條判定 | pass/fail |`(第一欄不粗體)」現況 OK validate green exit 0 → 應該 red ===='
fresh
python - "$QA/case/$QASKILL" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1])
t = p.read_text(encoding="utf-8")
old = "| **code-review** | 對本票的最終 diff 跑 `/code-review` | findings 清單與處置 |"
assert old in t
p.write_text(t.replace(old, old + "\n| judge | 逐條判定 | pass/fail |", 1), encoding="utf-8")
PY
sed -n '29,35p' "$QA/case/$QASKILL" | cat -n
gate
expect red "A1 不粗體的 judge lane"
expect_msg "並行池 lanes are" "no 並行池 section" "A1 訊息指到 lane 集合不對"

echo '==== A2  票上原句:「正文 `**排序約束**:獨立 judge 排在 walkthrough 之後才開,不進 §2 的並行池。` 整句刪掉,只留 §3 標題」現況 OK validate green exit 0 → 應該 red ===='
fresh
python - "$QA/case/$QASKILL" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1])
t = p.read_text(encoding="utf-8")
old = "**排序約束**:獨立 judge 排在 walkthrough 之後才開,不進 §2 的並行池。\n"
assert old in t
p.write_text(t.replace(old, "", 1), encoding="utf-8")
PY
echo "--- §3 標題還在(它自己就含 judge 與 walkthrough 之後),正文那句沒了"
sed -n '77,82p' "$QA/case/$QASKILL" | cat -n
set +e; grep -n '排序約束' "$QA/case/$QASKILL"; set -e
gate
expect red "A2 刪正文、留標題"
expect_msg "never states that the 獨立 judge runs walkthrough" "並行池 lanes are" "A2 訊息指到排序約束沒寫在正文"

echo '==== A3  票上原句:「整段 `## 2. 並行池` 拿掉」現況 red 但訊息是 `並行池 lanes are []` → 應該 `runs an 獨立 judge but declares no 並行池 section` ===='
fresh
python - "$QA/case/$QASKILL" <<'PY'
import re, sys, pathlib
p = pathlib.Path(sys.argv[1])
t = p.read_text(encoding="utf-8")
new, n = re.subn(r"^## 2\. 並行池.*?(?=^## 3\. )", "", t, flags=re.M | re.S)
assert n == 1, n
p.write_text(new, encoding="utf-8")
PY
set +e; grep -n '並行池' "$QA/case/$QASKILL"; set -e
gate
expect red "A3 並行池整段消失"
expect_msg "no 並行池 section declares its lane" "lanes are \[\]" "A3 訊息指到宣告整個不見,不是 lanes are []"

echo '==== A4  票上原句:「§2 的 `###` 子段裡加一張非 lane 表(第一欄粗體,例如資源分配表)」現況 red(`lanes are [...,port]`)→ 應該 green,這是要消失的假陽性 ===='
fresh
python - "$QA/case/$QASKILL" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1])
t = p.read_text(encoding="utf-8")
old = "### regression lane\n"
assert old in t
table = old + """
資源分配(不是 lane 宣告,只是同一段裡的另一張表):

| 資源 | 誰用 | 備註 |
| --- | --- | --- |
| **port** | regression | 5173 |
| **暫存目錄** | walkthrough | mktemp -d |
"""
p.write_text(t.replace(old, table, 1), encoding="utf-8")
PY
sed -n '52,64p' "$QA/case/$QASKILL" | cat -n
gate
expect green "A4 §2 子段多一張非 lane 表"

echo "==== pristine  出貨檔原封不動 → 該綠 ===="
fresh
gate
expect green "pristine"

echo '==== 完工定義:「順手一併修 —— scripts/validate.py:201 與 AGENTS.md:72 舉的假陽性例子(client-demo / next 的散文)repo 裡根本不存在,真正的例子是 skills/build-batch/SKILL.md:243「QA 第 6 輪 judge 實測」」 ===='
echo "---- 真的例子要在 repo 裡存在"
assert_grep 'QA 第 6 輪 judge 實測' "$ROOT/skills/build-batch/SKILL.md" "真例子存在"
echo "---- 守門與 AGENTS.md 現在引的就是這個例子"
assert_grep 'QA 第 6 輪 judge' "$ROOT/scripts/validate.py" "validate.py 引真例子"
assert_grep 'QA 第 6 輪 judge' "$ROOT/AGENTS.md" "AGENTS.md 引真例子"
echo "---- 舊的假例子(client-demo / next)不能再被引"
selfcheck_refute 'QA 第 6 輪 judge' "$ROOT/AGENTS.md"
refute_grep 'client-demo' "$ROOT/scripts/validate.py" "validate.py 不再引假例子"
refute_grep 'client-demo' "$ROOT/AGENTS.md" "AGENTS.md 不再引假例子"
refute_grep '/next 的路由' "$ROOT/scripts/validate.py" "validate.py 不再引 /next 假例子"
refute_grep '路由表的一列' "$ROOT/AGENTS.md" "AGENTS.md 不再引 /next 假例子"


# show_mutation <pattern> <格子說明> —— 把改完的地方連行號印出來。judge 讀 transcript
# 時要能分辨「這句被搬進 fence / comment」和「這句整句被刪掉」,兩者的守門訊息一樣。
show_mutation() {
  set +e
  echo "---- 改完的樣子($2):"
  grep -n -- "$1" "$QA/case/$QASKILL"
  if grep -q -- "$1" "$QA/case/$QASKILL"; then
    echo "RESULT PASS ($2 mutation 有生效):檔案裡看得到「$1」"
  else
    echo "RESULT FAIL ($2 mutation 沒生效):檔案裡找不到「$1」—— 這格測到的是別的東西"
    FAILED=1
  fi
}

# still_there <pattern> <格子說明> —— 那句話/那張表還在檔案裡,只是搬到讀不到的地方。
# 沒有這條,「搬走」跟「刪掉」在 transcript 上長得一模一樣。
still_there() {
  set +e
  local n
  n="$(grep -c -- "$1" "$QA/case/$QASKILL")"
  echo "---- 「$1」在檔案裡還有 $n 處($2)"
  if [ "$n" -gt 0 ]; then
    echo "RESULT PASS ($2 是搬走不是刪掉):「$1」還在檔案裡,只是搬到讀不到的地方"
  else
    echo "RESULT FAIL ($2):「$1」不在檔案裡 —— 這格變成「刪掉」,測不到繞過"
    FAILED=1
  fi
}

echo "==== QA 第 2 輪:五個繞過方向(code-review lane 打穿過出貨檔的形狀)===="
echo "同一種病 —— 主張換一種寫法就繞過去。改壞的方向 A1–A4 在上面,這五格守的是繞過。"

# mutate <說明> —— 讀 stdin 的 python 改壞副本;改壞腳本自己爆掉要當紅,不准當沒事
mutate() {
  set +e
  python - "$QA/case/$QASKILL"
  if [ "$?" -ne 0 ]; then
    echo "RESULT FAIL ($1):mutation 腳本自己爆掉 —— 這格沒測到"
    FAILED=1
  fi
}

echo "---- B1  judge lane 那一列縮排 3 個空白(GFM 照樣算同一張表的一列)→ 該紅"
fresh
mutate "B1" <<'PY_B1'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
row = [l for l in t.splitlines() if l.startswith("| **code-review** |")][0]
new = t.replace(row, row + "\n   | **judge** | 逐條判定 | pass/fail |", 1)
assert new != t
p.write_text(new, encoding="utf-8")
PY_B1
grep -n '逐條判定' "$QA/case/$QASKILL"
gate
expect red "B1 縮排的 judge lane"
expect_msg 'lanes are' 'declares no' "B1 訊息指 lane 集合"

echo "---- B2  排序約束只寫在 fence 裡 → 該紅"
fresh
mutate "B2" <<'PY_B2'
import sys, pathlib, re
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
after = re.compile("walkthrough[^。\n]{0,6}之後")
line = [l for l in t.splitlines() if not l.startswith("#") and after.search(l)][0]
new = t.replace(line, "```bash\n# " + line + "\n```", 1)
assert new != t
p.write_text(new, encoding="utf-8")
PY_B2
show_mutation '```bash' "B2"
still_there 'walkthrough 之後' "B2"
gate
expect red "B2 排序約束只在 fence 裡"

echo "---- B3  排序約束只寫在 HTML comment 裡 → 該紅"
fresh
mutate "B3" <<'PY_B3'
import sys, pathlib, re
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
after = re.compile("walkthrough[^。\n]{0,6}之後")
line = [l for l in t.splitlines() if not l.startswith("#") and after.search(l)][0]
new = t.replace(line, "<!-- " + line + " -->", 1)
assert new != t
p.write_text(new, encoding="utf-8")
PY_B3
show_mutation '<!--' "B3"
still_there 'walkthrough 之後' "B3"
gate
expect red "B3 排序約束只在 HTML comment 裡"

echo "---- B4  刪正文 + §3 標題改寫成 setext(底下一行 ---)→ 該紅"
fresh
mutate "B4" <<'PY_B4'
import sys, pathlib, re
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
after = re.compile("walkthrough[^。\n]{0,6}之後")
body = [l for l in t.splitlines() if not l.startswith("#") and after.search(l)][0]
head = [l for l in t.splitlines() if l.startswith("#") and after.search(l)][0]
new = t.replace(body + "\n", "", 1)
new = new.replace(head, head.split(" ", 1)[1] + "\n---", 1)
assert new != t
p.write_text(new, encoding="utf-8")
PY_B4
echo "---- 改完的 §3 標題(setext:文字一行 + --- 一行)"
grep -n -A 1 '獨立 judge(排在 walkthrough' "$QA/case/$QASKILL"
still_there 'walkthrough 之後' "B4"
gate
expect red "B4 setext 標題"

echo "---- B5  整張 lane 表包進 fence → 該紅,且訊息指到宣告不見"
fresh
mutate "B5" <<'PY_B5'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
hdr = [l for l in t.splitlines() if l.strip().startswith("| lane ")][0]
last = [l for l in t.splitlines() if l.startswith("| **code-review** |")][0]
new = t.replace(hdr, "```markdown\n" + hdr, 1)
new = new.replace(last, last + "\n```", 1)
assert new != t
p.write_text(new, encoding="utf-8")
PY_B5
show_mutation '```markdown' "B5"
still_there '| lane | 做什麼' "B5"
echo "---- 三支 lane 的資料列還在檔案裡(所以不是「表被刪掉」)"
grep -c '^| \*\*' "$QA/case/$QASKILL"
gate
expect red "B5 lane 表包進 fence"
expect_msg 'declares its lane table' 'lanes are' "B5 訊息指宣告不見"

echo "==== 完工定義:四格斷言住在 --self-check 的 real-skill layer ===="
echo "---- 出貨檔改壞的那幾格,連行號印出來(斷言不是散文宣稱的,是這幾行)"
grep -n -e '# A1:' -e '# A2:' -e '# A3:' -e '# A4:' -e '# B1:' -e '# B2:' -e '# B3:' -e '# B4:' -e '# B5:' "$ROOT/scripts/validate.py"
ASSERT_N="$(grep -c -e '# A[1-4]:' -e '# B[1-5]:' "$ROOT/scripts/validate.py")"
echo "斷言格數: $ASSERT_N"
if [ "$ASSERT_N" -ge 9 ]; then
  echo "RESULT PASS (四格 + 五格斷言在 self-check 裡):$ASSERT_N 格"
else
  echo "RESULT FAIL (斷言格數不足):$ASSERT_N,預期 >= 9"
  FAILED=1
fi

echo "==== 完工定義的四條指令 —— 證據跟驗收項放同一份 transcript ===="
run_gate() {
  set +e
  echo "---- $*"
  "$@" 2>&1 | tail -20
  local rc="${PIPESTATUS[0]}"
  echo "exit $rc"
  if [ "$rc" -eq 0 ]; then
    echo "RESULT PASS (完工定義:$1 $2):exit 0"
  else
    echo "RESULT FAIL (完工定義:$1 $2):exit $rc"
    FAILED=1
  fi
}
run_gate python "$ROOT/scripts/validate.py"
run_gate python "$ROOT/scripts/validate.py" --self-check
run_gate python "$ROOT/scripts/qa/107-mutate.py" --run
run_gate python "$ROOT/scripts/qa/107-prevdiff.py"
run_gate python "$ROOT/scripts/qa/112-prevdiff.py"
run_gate bash "$ROOT/scripts/qa/107-walkthrough.sh" "$QA/nested107"

set +x
echo
echo "==== walkthrough 走完 ===="
if [ "$FAILED" -ne 0 ]; then
  echo "有格子不合預期 —— 見上面的 RESULT FAIL"
  echo "EXIT=1"
  exit 1
fi
echo "所有格子符合預期"
echo "EXIT=0"
