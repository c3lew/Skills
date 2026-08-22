#!/usr/bin/env bash
# #107 QA walkthrough —— 票內平行化:regression / walkthrough / code-review 同時開,
# judge 釘在 walkthrough 之後。
# 範圍 = 票上「覆蓋驗收項」第 7 條 + #107 的五條 acceptance criteria 原句。
# 這片的交付物是散文(SKILL.md)+ 守門(scripts/validate.py),沒有 web UI,
# 所以「a11y snapshot」的等價物 = 每條 AC 一段可重跑的實測 transcript
# (指令 + 真實輸出 + 引用到的散文原文行號)。
#
# 用法:bash scripts/qa/107-walkthrough.sh "$(mktemp -d)/qa107"
# 這支不碰 repo 本體 —— 每個情境都跑在拋棄式暫存目錄的 repo 副本上。
# exit 非 0 = 有格子不合預期。
PS4='+ '
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
QA="${1:?usage: 107-walkthrough.sh <workdir>}"
rm -rf "$QA"; mkdir -p "$QA"
PRISTINE="$QA/pristine"
mkdir -p "$PRISTINE"
cp -r "$ROOT"/* "$PRISTINE/"   # .git 是隱藏檔,* 不會帶進來

FAILED=0
QASKILL="skills/qa/SKILL.md"

fresh() { rm -rf "$QA/case"; cp -r "$PRISTINE" "$QA/case"; }

# gate:在副本上跑守門,完整輸出留在 transcript,exit code 與 judge 相關錯誤各存一份
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

set -x

echo "==== AC1  regression / walkthrough / code-review 三者同時開始,不互相等待 ===="
echo "---- 1a  出貨的 skills/qa/SKILL.md §2 原文(下一個 agent 照著做的那份)"
sed -n '24,47p' "$ROOT/$QASKILL" | cat -n
echo "---- 1b  三支 lane 的宣告(表格第一欄)"
grep -n '^| \*\*' "$ROOT/$QASKILL"
echo "---- 1c 「同一則訊息一次發出去」有沒有寫下來"
grep -n '同一則訊息' "$ROOT/$QASKILL" "$ROOT/skills/build/SKILL.md"
echo "---- 1d  §2 有沒有殘留序列語(「跑完才」「先跑」「再走」)"
set +e
grep -n -e '先跑' -e '跑完才' -e '再走' "$ROOT/$QASKILL"
echo "序列語命中數: $?(1 = 一條都沒有)"
echo "---- 1e  /build §2 的 code-review 並行位置,以及兩份文件的母體有沒有互相矛盾"
sed -n '14,26p' "$ROOT/skills/build/SKILL.md" | cat -n
grep -n -e 'commit 前的工作區' -e '最終 diff' "$ROOT/$QASKILL" "$ROOT/skills/build/SKILL.md"

echo "==== AC2(a) 散文面:排序約束與它的理由 ===="
sed -n '73,81p' "$ROOT/$QASKILL" | cat -n

echo "==== AC2(b) 可執行面:六格 mutation,拿真的 skills/qa/SKILL.md 改壞 ===="

echo "---- 2b-1  把 | **judge** | 判定 | 插進並行池 lane 表 → 該紅"
fresh
python - "$QA/case/$QASKILL" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1])
t = p.read_text(encoding="utf-8")
old = "| **code-review** | 對本票的最終 diff 跑 `/code-review` | findings 清單與處置 |"
assert old in t
p.write_text(t.replace(old, old + "\n| **judge** | 判定 pass / fail | 逐條判定 |", 1), encoding="utf-8")
PY
grep -n '^| \*\*' "$QA/case/$QASKILL"
gate
expect red "judge 混進並行池"

echo "---- 2b-2  刪掉 | **code-review** … 那列 → 該紅"
fresh
python - "$QA/case/$QASKILL" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1])
t = p.read_text(encoding="utf-8")
old = "| **code-review** | 對本票的最終 diff 跑 `/code-review` | findings 清單與處置 |\n"
assert old in t
p.write_text(t.replace(old, "", 1), encoding="utf-8")
PY
grep -n '^| \*\*' "$QA/case/$QASKILL"
gate
expect red "少一支 lane"

echo "---- 2b-3  lane 表三列上下順序對調 → 該綠(順序自由,主張是同時開始)"
fresh
python - "$QA/case/$QASKILL" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1])
t = p.read_text(encoding="utf-8")
rows = [l for l in t.splitlines() if l.startswith("| **")]
assert len(rows) == 3, rows
block = "\n".join(rows)
p.write_text(t.replace(block, "\n".join(reversed(rows)), 1), encoding="utf-8")
PY
grep -n '^| \*\*' "$QA/case/$QASKILL"
gate
expect green "lane 順序對調"

echo "---- 2b-4 「排在 walkthrough 之後」改寫成「之前」→ 該紅"
fresh
python - "$QA/case/$QASKILL" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1])
t = p.read_text(encoding="utf-8")
assert "walkthrough 之後" in t
p.write_text(t.replace("walkthrough 之後", "walkthrough 之前"), encoding="utf-8")
PY
grep -n 'walkthrough 之前' "$QA/case/$QASKILL"
gate
expect red "排序反過來"

echo "---- 2b-5  整段 ## 2. 並行池… 拿掉 → 該紅"
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
expect red "並行池整段消失"

echo "---- 2b-6  原封不動 → 該綠"
fresh
gate
expect green "pristine"

echo "==== AC3  並行不搶資源 ===="
echo "---- 3a  散文面:lane 之間不共用資源 + 撞到就序列化"
grep -n -e '不共用資源' -e '序列化' -e '暫存目錄' "$ROOT/$QASKILL"
echo "---- 3b  實測:同時起兩個 validate.py --self-check,看會不會互相干擾"
set +e
( python "$ROOT/scripts/validate.py" --self-check > "$QA/sc-A.txt" 2>&1; echo $? > "$QA/sc-A.rc" ) &
PA=$!
( python "$ROOT/scripts/validate.py" --self-check > "$QA/sc-B.txt" 2>&1; echo $? > "$QA/sc-B.rc" ) &
PB=$!
wait $PA; wait $PB
echo "--- lane A"; cat "$QA/sc-A.txt"; echo "exit $(cat "$QA/sc-A.rc")"
echo "--- lane B"; cat "$QA/sc-B.txt"; echo "exit $(cat "$QA/sc-B.rc")"
if [ "$(cat "$QA/sc-A.rc")" = "0" ] && [ "$(cat "$QA/sc-B.rc")" = "0" ]; then
  echo "RESULT PASS (並行 self-check):兩支同時跑都綠,沒有互相干擾"
else
  echo "RESULT FAIL (並行 self-check):有一支非 0"
  FAILED=1
fi

echo "==== AC4  任一支 lane 紅,報告要指名道姓,不被其他支綠蓋過 ===="
echo "---- 4a  散文面:指名道姓 / AND 不是多數決 / lane 自己爆掉同級"
grep -n -e '指名道姓' -e '多數決' -e '爆掉' -e '三線各自的結果' "$ROOT/$QASKILL"
echo "---- 4b  演練:三支 lane 同時跑,其中 regression 這支必定紅(排序句被改壞)"
fresh
python - "$QA/case/$QASKILL" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1])
t = p.read_text(encoding="utf-8")
p.write_text(t.replace("walkthrough 之後", "walkthrough 之前"), encoding="utf-8")
PY
set +e
( python "$QA/case/scripts/validate.py" > "$QA/lane-regression.txt" 2>&1; echo $? > "$QA/lane-regression.rc" ) &
L1=$!
( python "$ROOT/scripts/qa/107-mutate.py" --list > "$QA/lane-walkthrough.txt" 2>&1; echo $? > "$QA/lane-walkthrough.rc" ) &
L2=$!
( git -C "$ROOT" diff --stat 84ab07d..HEAD -- skills/ > "$QA/lane-codereview.txt" 2>&1; echo $? > "$QA/lane-codereview.rc" ) &
L3=$!
wait $L1; wait $L2; wait $L3
for lane in regression walkthrough codereview; do
  echo "--- lane $lane  exit $(cat "$QA/lane-$lane.rc")"
  cat "$QA/lane-$lane.txt"
done
echo "---- 4c  收斂:三支是 AND,不是多數決"
AND_RC=0
REDS=""
for lane in regression walkthrough codereview; do
  rc="$(cat "$QA/lane-$lane.rc")"
  if [ "$rc" != "0" ]; then AND_RC=1; REDS="$REDS $lane"; fi
done
echo "紅的 lane:${REDS:- 無}"
echo "彙總 exit(AND):$AND_RC"
if [ "$AND_RC" = "1" ] && [ "$REDS" = " regression" ] && grep -q -e 'judge' -e '並行池' "$QA/lane-regression.txt"; then
  echo "RESULT PASS (失敗指名道姓):只有 regression 紅,兩支綠沒有蓋過它,錯誤原文指得出是哪一條判準"
else
  echo "RESULT FAIL (失敗指名道姓):REDS='$REDS' AND_RC=$AND_RC"
  FAILED=1
fi

echo "==== AC5  本輪改動到的 SKILL.md 段落(交給 /writing-for-agents 判準逐條審)===="
git -C "$ROOT" diff --stat 84ab07d..HEAD -- skills/
wc -l "$ROOT/$QASKILL" "$ROOT/skills/build/SKILL.md"
grep -c . "$ROOT/$QASKILL"

set +x
echo
echo "==== walkthrough 走完 ===="
if [ "$FAILED" -ne 0 ]; then
  echo "有格子不合預期 —— 見上面的 RESULT FAIL"
  exit 1
fi
echo "所有格子符合預期"
