#!/usr/bin/env bash
# #118 QA walkthrough —— 一張 override 被拒,整批分級清單不再消失、訊息指名票號。
# 判定 oracle = 票上「覆蓋驗收項」的原句,只有一條:
#   1. 切票的時候,每張票都標了「快」或「慢」加一句理由,整批一次列給我看,
#      我可以當場改任何一張。
#
# 這片沒有 web UI(CLI + 散文),所以走查的形狀 = 可重跑的 shell transcript:
# 每個 AC 一段,指令 + 真實輸出 + 判定,照 scripts/qa/108-walkthrough.sh 的體例。
#
# 用法:bash scripts/qa/118-walkthrough.sh "$(mktemp -d)/qa118"
# 改壞真檔的格子一律跑在拋棄式副本上,repo 本體只讀。exit 非 0 = 有格子不合預期。
PS4='+ '
set +e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
QA="${1:?usage: 118-walkthrough.sh <workdir>}"
rm -rf "$QA"; mkdir -p "$QA"
PRISTINE="$QA/pristine"
mkdir -p "$PRISTINE"
cp -r "$ROOT"/* "$PRISTINE/"   # .git 是隱藏檔,* 不會帶進來

FAILED=0
BATCH="skills/build-batch/batch.py"
MUTATE="scripts/qa/97-mutate.py"

fresh() { rm -rf "$QA/case"; cp -r "$PRISTINE" "$QA/case"; }

# classify:把一份 JSON 餵進出貨的 batch.py。stdout / stderr 分開存 —— #118 的兩
# 條 AC 一條在 stdout(整批照印)一條在 stderr(訊息指名票號),混在一起就判不了。
classify() {
  printf '%s' "$1" | python "$ROOT/$BATCH" > "$QA/out.txt" 2> "$QA/err.txt"
  CL_EXIT=$?
  echo "--- stdout"; cat "$QA/out.txt"
  echo "--- stderr"; cat "$QA/err.txt"
  echo "exit $CL_EXIT"
}

# rows / paste:兩段各自的行數。分級列 = client 點頭看的那幾行;
# 貼票行 = agent 會照著貼進票 body 的那幾行(`#NN  分級:…`)。
rows_n()  { grep -cE '^  (快|慢|改不了) +#[0-9]+ .* — .+$' "$QA/out.txt"; }
paste_n() { grep -cE '^  #[0-9]+  分級:' "$QA/out.txt"; }

# selfcheck:在副本上跑 batch.py 自己的 --self-check(判準住在哪支檔,證據就要在
# 那支檔預設會跑的地方轉紅 —— 拿 validate.py 量它是在量別支檔)。
selfcheck() {
  python "$QA/case/$BATCH" --self-check > "$QA/g-batch.txt" 2>&1
  G_BATCH=$?
  echo "--- $BATCH --self-check"; tail -3 "$QA/g-batch.txt"; echo "exit $G_BATCH"
}

# expect_gate <red|green> <說明>
expect_gate() {
  local want="$1" what="$2"
  if [ "$want" = red ] && [ "$G_BATCH" != 0 ]; then
    echo "RESULT PASS ($what):預期守門紅、實際紅(batch=$G_BATCH)"
  elif [ "$want" = green ] && [ "$G_BATCH" = 0 ]; then
    echo "RESULT PASS ($what):預期守門綠、實際綠"
  else
    echo "RESULT FAIL ($what):預期 $want,實際 batch=$G_BATCH"
    FAILED=1
  fi
}

# ok <上一個指令的 exit code> <說明>
ok() {
  if [ "$1" = 0 ]; then echo "RESULT PASS ($2)"; else echo "RESULT FAIL ($2)"; FAILED=1; fi
}

# 票上重現步驟那批:#47 有 coverage、#48 override 慢、#49 judgement true + override 快
P_TAIL='{"mode":"classify","tickets":[{"number":47,"coverage":["1. x"],"judgement":false},{"number":48,"coverage":[],"judgement":false,"override":"慢"},{"number":49,"coverage":[],"judgement":true,"override":"快"}],"titles":{"47":"a","48":"b","49":"c"}}'
P_HEAD='{"mode":"classify","tickets":[{"number":49,"coverage":[],"judgement":true,"override":"快"},{"number":47,"coverage":["1. x"],"judgement":false},{"number":48,"coverage":[],"judgement":false,"override":"慢"}],"titles":{"47":"a","48":"b","49":"c"}}'
P_MID='{"mode":"classify","tickets":[{"number":47,"coverage":["1. x"],"judgement":false},{"number":49,"coverage":[],"judgement":true,"override":"快"},{"number":48,"coverage":[],"judgement":false,"override":"慢"}],"titles":{"47":"a","48":"b","49":"c"}}'
# 一批全部合法、而且**快慢兩種標籤同時出現**的批次:
# #51 沒有覆蓋驗收項 -> 快;#52 寫「無 —…」的那種寫法 -> 也是快;#47 有覆蓋 -> 慢
P_BOTH='{"mode":"classify","tickets":[{"number":47,"coverage":["1. x"],"judgement":false},{"number":51,"coverage":[],"judgement":false},{"number":52,"coverage":["無 — 由後續票的驗收項間接驗證"],"judgement":false}],"titles":{"47":"a","51":"e","52":"f"}}'
P_CLEAN='{"mode":"classify","tickets":[{"number":47,"coverage":["1. x"],"judgement":false},{"number":48,"coverage":[],"judgement":false,"override":"慢"},{"number":49,"coverage":[],"judgement":true}],"titles":{"47":"a","48":"b","49":"c"}}'
P_TWO='{"mode":"classify","tickets":[{"number":47,"coverage":["1. x"],"judgement":false},{"number":49,"coverage":[],"judgement":true,"override":"快"},{"number":50,"coverage":[],"override":"fast"}],"titles":{"47":"a","49":"c","50":"d"}}'

set -x

echo "==================================================================="
echo "==== AC1  整批先算完再決定退出:被拒的那張標出來,其餘各張的分級照印"
echo "==================================================================="

echo "---- 1a  票上重現步驟那批(被拒的 #49 在最後一張)"
classify "$P_TAIL"
echo "     分級列 $(rows_n) 行 / 票數 3;貼票行 $(paste_n) 行"
{ [ "$(rows_n)" = 3 ] && grep -q '^  慢 *#47 a — 覆蓋 1 條驗收項$' "$QA/out.txt" \
  && grep -q '^  慢 *#48 b — 你當場改成「慢」$' "$QA/out.txt"; }
ok $? "三行分級都印出來,client 同一輪改的 #48 沒有跟著消失"

echo "---- 1b  被拒的那張自己標出來:是哪一張 + 為什麼拒"
grep -nE '^  改不了 +#[0-9]+' "$QA/out.txt"
{ grep -q '^  改不了 *#49 c — 動到判斷邏輯或資料寫入,硬規則一律慢' "$QA/out.txt" \
  && grep -q '改不成快' "$QA/out.txt"; }
ok $? "被拒那列標成「改不了」、指名 #49、帶著理由"

echo "---- 1c  標題自己報張數,而且報得出「其中幾張改不了」"
grep -nE '^分級\(' "$QA/out.txt"
grep -q '^分級(3 張,其中 1 張改不了)' "$QA/out.txt"
ok $? "一份清單、標題自己數 3 張其中 1 張改不了"

echo "---- 1d  被拒的那張在最前面 —— 後面兩張照印"
classify "$P_HEAD"
{ [ "$(rows_n)" = 3 ] && [ "$(grep -cE '^  慢 +#(47|48)' "$QA/out.txt")" = 2 ] \
  && grep -q '^  改不了 *#49' "$QA/out.txt"; }
ok $? "被拒在頭:3 行照印,其餘兩張都在"

echo "---- 1e  被拒的那張夾在中間 —— 前後兩張照印"
classify "$P_MID"
{ [ "$(rows_n)" = 3 ] && [ "$(grep -cE '^  慢 +#(47|48)' "$QA/out.txt")" = 2 ] \
  && grep -q '^  改不了 *#49' "$QA/out.txt"; }
ok $? "被拒在中間:3 行照印,其餘兩張都在"

echo "---- 1f  兩張同時被拒(#49 硬規則、#50 override 打錯字)—— 兩張都要看得見"
classify "$P_TWO"
{ [ "$(rows_n)" = 3 ] && grep -q '^分級(3 張,其中 2 張改不了)' "$QA/out.txt" \
  && grep -q '^  改不了 *#49' "$QA/out.txt" && grep -q '^  改不了 *#50' "$QA/out.txt" \
  && grep -q '^  慢 *#47' "$QA/out.txt"; }
ok $? "兩張被拒都各自標出來,沒被拒的 #47 照印"

echo "---- 1g  每一行分級都帶一句非空的理由(不是只有快/慢)"
classify "$P_TAIL"
grep -nE '^  (快|慢|改不了) +#[0-9]+' "$QA/out.txt"
[ "$(grep -cE '^  (快|慢|改不了) +#[0-9]+ .* — .+$' "$QA/out.txt")" = 3 ]
ok $? "3 行分級,每行都帶一句理由"

echo "==================================================================="
echo "==== AC2  錯誤訊息指名票號(不能只有「這張」)"
echo "==================================================================="

echo "---- 2a  stderr 裡有 #49"
cat "$QA/err.txt"
{ grep -q '#49' "$QA/err.txt" && ! grep -q '這張' "$QA/err.txt"; }
ok $? "stderr 指名 #49,沒有出廠時那句沒有票號的「這張」"

echo "---- 2b  兩張被拒時兩個票號都在 stderr"
classify "$P_TWO"
{ grep -q '#49' "$QA/err.txt" && grep -q '#50' "$QA/err.txt" \
  && grep -q '這批有 2 張的分級改不了' "$QA/err.txt"; }
ok $? "兩張被拒,兩個票號都指名,張數也對"

echo "==================================================================="
echo "==== AC3  非 0 退出保留 —— 當場停、不靜靜忽略"
echo "==================================================================="

echo "---- 3a  有被拒 → exit 非 0"
classify "$P_TAIL"
[ "$CL_EXIT" != 0 ]
ok $? "有被拒的批次 exit=$CL_EXIT(非 0)"

echo "---- 3b  沒有被拒 → exit 0(對照組,證明停的是被拒不是別的東西)"
classify "$P_CLEAN"
[ "$CL_EXIT" = 0 ]
ok $? "同一批把那張的 override 拿掉,exit=0"

echo "==================================================================="
echo "==== AC4  貼票那段:有被拒時整段不印,而且明講「這批還不能貼」"
echo "==================================================================="

echo "---- 4a  有被拒 → stdout 一行 `#NN  分級:` 都沒有"
classify "$P_TAIL"
echo "     貼票行 $(paste_n) 行"
{ [ "$(paste_n)" = 0 ] && ! grep -q '點頭之後' "$QA/out.txt"; }
ok $? "貼票那段整段不印,agent 沒有東西可以照著貼"

echo "---- 4b  而且明確印出「這批還不能貼」+ 是哪一張"
grep -n -e '這批還不能貼' -e '^  #49 c$' "$QA/out.txt"
{ grep -q '這批還不能貼' "$QA/out.txt" && grep -q '^  #49 c$' "$QA/out.txt"; }
ok $? "印了「這批還不能貼」,並列出是哪一張"

echo "---- 4c  沒有被拒 → 貼票那段照印,行數 = 票數"
classify "$P_CLEAN"
echo "     貼票行 $(paste_n) 行 / 票數 3"
{ [ "$(paste_n)" = 3 ] && grep -q '點頭之後' "$QA/out.txt" \
  && grep -q '^  #49  分級:慢 — 動到判斷邏輯或資料寫入,硬規則一律慢$' "$QA/out.txt"; }
ok $? "沒被拒的批次貼票段照印,3 張 3 行"

echo "---- 4d  「快」那條路也要演得出來 —— 原句是「標了『快』或『慢』」,不是只有慢"
classify "$P_BOTH"
{ [ "$CL_EXIT" = 0 ] && [ "$(rows_n)" = 3 ] \
  && grep -q '^  快 *#51 e — ' "$QA/out.txt" \
  && grep -q '^  快 *#52 f — ' "$QA/out.txt" \
  && grep -q '^  慢 *#47 a — ' "$QA/out.txt" \
  && grep -q '^  #51  分級:快 — ' "$QA/out.txt"; }
ok $? "同一批裡快、慢兩種標籤都印得出來,貼票行也跟著是「分級:快」"

echo "==================================================================="
echo "==== AC5/AC6  反向:mutation 台有這幾個 knob,改壞後 --self-check 轉紅"
echo "==================================================================="

echo "---- 5a  97-mutate.py --list 列得出 classify_* knob"
python "$ROOT/$MUTATE" --list
CLASSIFY_KNOBS="$(python "$ROOT/$MUTATE" --list | grep '^classify_')"
echo "$CLASSIFY_KNOBS" | cat -n
[ "$(echo "$CLASSIFY_KNOBS" | wc -l)" -ge 4 ]
ok $? "mutation 台上有 $(echo "$CLASSIFY_KNOBS" | wc -l) 個 classify_* knob"

echo "---- 5b  隨機挑 2 個 knob,套到 repo 副本上,batch.py --self-check 要轉紅"
PICKED="$(echo "$CLASSIFY_KNOBS" | shuf -n 2)"
echo "本輪抽到:"; echo "$PICKED"
echo "     控制組:副本原封不動 → 該綠"
fresh; selfcheck; expect_gate green "pristine 副本"
for KNOB in $PICKED; do
  fresh
  python "$ROOT/$MUTATE" "$QA/case" "$KNOB"
  selfcheck; expect_gate red "隨機 knob $KNOB"
done

echo "==================================================================="
echo "==== 改壞真檔的繞過方向(全在副本上,repo 本體只讀)"
echo "==================================================================="

echo "---- 6a  classify_tickets 退回 list comprehension(第一張被拒就打死整批)→ 該紅"
fresh
python "$ROOT/$MUTATE" "$QA/case" classify_batch_dies_on_first
selfcheck; expect_gate red "整批被第一張打死"
echo "     繞過之後這批長什麼樣(#118 出廠時的畫面):"
printf '%s' "$P_TAIL" | python "$QA/case/$BATCH" > "$QA/m-out.txt" 2> "$QA/m-err.txt"
echo "exit $?"; echo "--- stdout"; cat "$QA/m-out.txt"; echo "--- stderr"; cat "$QA/m-err.txt"

echo "---- 6b  被拒那列從清單藏掉(其餘照印,但不知道少了誰)→ 該紅"
fresh
python "$ROOT/$MUTATE" "$QA/case" classify_rejected_row_hidden
selfcheck; expect_gate red "被拒那列被藏"

echo "---- 6c  有被拒還是把貼票那段印出來 → 該紅"
fresh
python "$ROOT/$MUTATE" "$QA/case" classify_paste_anyway
selfcheck; expect_gate red "沒點頭的清單照樣可貼"

echo "---- 6d  退出碼變 0(印歸印,「當場停」沒了)→ 該紅"
fresh
python "$ROOT/$MUTATE" "$QA/case" classify_reject_exit_zero
selfcheck; expect_gate red "被拒卻 exit 0"

echo "---- 6e  訊息退回沒有票號的「這張」→ 該紅(AC2 的反向)"
fresh
python "$ROOT/$MUTATE" "$QA/case" classify_reject_unnamed
selfcheck; expect_gate red "訊息不指名票號"

echo "==================================================================="
echo "==== 收尾:repo 本體一個字沒動"
echo "==================================================================="

echo "---- 7a  git status 只剩本輪新增的那兩支未追蹤檔"
git -C "$ROOT" status --porcelain -- skills scripts
DIRTY="$(git -C "$ROOT" status --porcelain -- skills scripts \
         | grep -v '^?? scripts/qa/118-walkthrough.sh$' \
         | grep -v '^?? scripts/qa/118-wide.py$')"
echo "扣掉那兩支之後剩:[$DIRTY]"
[ -z "$DIRTY" ]
ok $? "skills/ 與 scripts/ 除了新增的兩支 QA 檔以外一個字都沒動"

set +x
echo
echo "==== walkthrough 走完 ===="
if [ "$FAILED" -ne 0 ]; then
  echo "有格子不合預期 —— 見上面的 RESULT FAIL"
  exit 1
fi
echo "所有格子符合預期"
