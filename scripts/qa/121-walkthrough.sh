#!/usr/bin/env bash
# #121 QA walkthrough —— 被擋下來時那幾句話,client 讀不讀得懂「所以我該做什麼」。
# 判定 oracle = 票上「覆蓋驗收項」的原句,只有一條:
#   1. 切票的時候,每張票都標了「快」或「慢」加一句理由,整批一次列給我看,
#      我可以當場改任何一張。
#
# #118 已經把「整批照印、指名票號、非 0 退出」做完了,這張只管**措辭**:同一份
# 輸出,client 讀完知不知道下一步按什麼。所以每一格都是「印出那份清單的原文,
# 再問一句 client 讀得懂嗎」,判定寫成可機械重跑的 grep。
#
# 用法:bash scripts/qa/121-walkthrough.sh "$(mktemp -d)/qa121"
# 改壞真檔的格子一律跑在拋棄式副本上,repo 本體只讀。exit 非 0 = 有格子不合預期。
PS4='+ '
set +e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
QA="${1:?usage: 121-walkthrough.sh <workdir>}"
rm -rf "$QA"; mkdir -p "$QA"

FAILED=0
BATCH="skills/build-batch/batch.py"

# classify:把一份 JSON 餵進出貨的 batch.py,stdout / stderr 分開存 —— 這張票有
# 一格就是在問「同一句話是不是兩邊各印一次」,混在一起就判不了。
classify() {
  printf '%s' "$1" | python "$ROOT/$BATCH" > "$QA/out.txt" 2> "$QA/err.txt"
  CL_EXIT=$?
  echo "--- stdout"; cat "$QA/out.txt"
  echo "--- stderr"; cat "$QA/err.txt"
  echo "exit $CL_EXIT"
}

# ok <上一個指令的 exit code> <說明>
ok() {
  if [ "$1" = 0 ]; then echo "RESULT PASS ($2)"; else echo "RESULT FAIL ($2)"; FAILED=1; fi
}

# 重現步驟那批:#48 是 client 同一輪改的,#49 撞硬規則,#50 分級打錯字。
P_TWO='{"mode":"classify","tickets":[
  {"number":48,"coverage":[],"judgement":false},
  {"number":49,"coverage":[],"judgement":true,"override":"快"},
  {"number":50,"coverage":["1. 登入頁"],"override":"fast"}],
  "titles":{"48":"骨架","49":"算票","50":"登入頁"}}'
P_OK='{"mode":"classify","tickets":[
  {"number":48,"coverage":[],"judgement":false},
  {"number":49,"coverage":["1. 登入頁"]}],
  "titles":{"48":"骨架","49":"登入頁"}}'

set -x

echo "==================================================================="
echo "==== AC1  硬規則被拒那句:講的是 client 做得到的下一步,不是工程師指路"
echo "==================================================================="

classify "$P_TWO"

echo "---- 1a  那一列的原文(client 螢幕上實際會看到的那一行)"
grep -n '#49 算票' "$QA/out.txt"

echo "---- 1b  不出現 judgement 旗標 —— 那不是 client 填的欄位,他做不到"
{ ! grep -q 'judgement' "$QA/out.txt" && ! grep -q '旗標' "$QA/out.txt" \
  && ! grep -q 'judgement' "$QA/err.txt" && ! grep -q '旗標' "$QA/err.txt"; }
ok $? "整份輸出(stdout + stderr)沒有 judgement / 旗標"

echo "---- 1c  有一條 client 真的走得到的路:回去改票的內容"
grep -q '要改快只有一條路:回去改票的內容' "$QA/out.txt"
ok $? "講得出下一步是什麼,不是只說「不行」"

echo "---- 1d  說話對象是 client 自己 —— 不用第三人稱叫他 client"
{ ! grep -q 'client' "$QA/out.txt" && ! grep -q 'client' "$QA/err.txt"; }
ok $? "印給 client 的字裡沒有「client」這個第三人稱"

echo "==================================================================="
echo "==== AC2  分級打錯字被拒那句:沒有 override,也不解釋設計取捨"
echo "==================================================================="

echo "---- 2a  那一列的原文"
grep -n '#50 登入頁' "$QA/out.txt"

echo "---- 2b  不出現英文詞 override"
{ ! grep -q 'override' "$QA/out.txt" && ! grep -q 'override' "$QA/err.txt"; }
ok $? "整份輸出沒有 override"

echo "---- 2c  講的是他填錯什麼 + 該怎麼修"
grep -q "你填的分級只能是「快」或「慢」,你打的是 'fast' —— 改一下再重跑" "$QA/out.txt"
ok $? "指名他打的是什麼、要改成什麼"

echo "---- 2d  解釋設計取捨的那半句拿掉了(對 client 是雜訊)"
{ ! grep -q '靜靜照原判寫進票' "$QA/out.txt" && ! grep -q '不猜' "$QA/out.txt"; }
ok $? "沒有「打錯一個字就靜靜照原判寫進票,不猜」那半句"

echo "==================================================================="
echo "==== AC3  被拒那張也標得出車道 —— 原句是「每張票都標了快或慢」"
echo "==================================================================="

echo "---- 3a  硬規則那張:系統自己算得出是慢,就印出來"
grep -q '^  慢(改不了)  #49 算票 — ' "$QA/out.txt"
ok $? "#49 左欄是「慢(改不了)」,不是只有第三種標籤"

echo "---- 3b  打錯字那張:車道算不出來就不猜(#108「不猜」那條)"
{ grep -q '^  改不了 *#50 登入頁 — ' "$QA/out.txt" \
  && ! grep -qE '^  (快|慢) *#50' "$QA/out.txt"; }
ok $? "#50 沒有被替他填一個快/慢"

echo "---- 3c  左欄還是對齊的(補到同寬,沒被最長那格弄歪)"
grep -nE '^  \S+ +#[0-9]+ ' "$QA/out.txt"
[ "$(grep -cE '^  .{2,}#[0-9]+ [^ ]+ — .+$' "$QA/out.txt")" = 3 ]
ok $? "三列都是「左欄 + 票號 + 標題 — 理由」的同一個形狀"

echo "==================================================================="
echo "==== AC4  同一句話不要 stdout / stderr 各印一次"
echo "==================================================================="

echo "---- 4a  stderr 只講「停在哪、是哪幾張」"
cat "$QA/err.txt"
{ grep -q '停在這裡 —— #49、#50 的分級改不了' "$QA/err.txt" \
  && [ "$(wc -l < "$QA/err.txt")" -le 1 ]; }
ok $? "stderr 一行,指名兩個票號"

echo "---- 4b  理由只在 stdout 那份清單上出現一次,stderr 不重講"
{ ! grep -q '硬規則' "$QA/err.txt" && ! grep -q '你填的分級' "$QA/err.txt"; }
ok $? "stderr 沒有把 stdout 的理由再抄一遍"

echo "---- 4c  「還不能貼」那件事也只說一次"
[ "$(grep -c '還不能貼' "$QA/out.txt")" = 1 ]
ok $? "stdout 裡「還不能貼」只出現一次"

echo "==================================================================="
echo "==== AC5  綠色路徑那份清單不夾給 agent 看的內部術語"
echo "==================================================================="

classify "$P_OK"

echo "---- 5a  沒有被拒 -> 正常印完貼票那段"
{ [ "$CL_EXIT" = 0 ] && grep -q '點頭之後,每張票上會多這一行:' "$QA/out.txt"; }
ok $? "綠色路徑照印,而且那句是講給 client 聽的"

echo "---- 5b  票 body / 覆蓋驗收項段 這些內部術語不出現在 client 清單上"
{ ! grep -q '票 body' "$QA/out.txt" && ! grep -q '覆蓋驗收項」段' "$QA/out.txt"; }
ok $? "client 清單上沒有票 body /「覆蓋驗收項」段"

echo "---- 5c  貼進票裡的那幾行本身沒變(#108 凍結的格式)"
grep -nE '^  #[0-9]+  分級:(快|慢) — ' "$QA/out.txt"
[ "$(grep -cE '^  #[0-9]+  分級:(快|慢) — .+$' "$QA/out.txt")" = 2 ]
ok $? "兩張票兩行,格式照舊"

echo "---- 5d  agent 那邊的操作指示還在 —— 搬到 SKILL.md,不是消失"
grep -n '覆蓋驗收項」段下方' "$ROOT/skills/slice-tickets/SKILL.md"
grep -q '覆蓋驗收項」段下方' "$ROOT/skills/slice-tickets/SKILL.md"
ok $? "貼哪裡這件事還寫在 agent 讀的那份文件上"

echo "==================================================================="
echo "==== AC6  守門跟著改 —— 咬的是新措辭,不是放寬成關鍵字"
echo "==================================================================="

echo "---- 6a  batch.py --self-check 綠"
python "$ROOT/$BATCH" --self-check
ok $? "batch.py --self-check exit 0"

echo "---- 6b  措辭改回舊版 -> self-check 要紅(在拋棄式副本上)"
# 整份 repo 複製一份 —— self-check 會去讀隔壁的 SKILL.md,只搬一支檔的話它會
# 紅在「檔不見了」而不是紅在斷言上,那就量不到「守門真的咬著這句措辭」。
rm -rf "$QA/case"; cp -r "$ROOT" "$QA/case"   # .git 是隱藏檔,cp -r 不會帶進來
python - "$QA/case/$BATCH" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
old = '你填的分級只能是「快」或「慢」,你打的是 {override!r} —— 改一下再重跑'
assert old in t
p.write_text(t.replace(old, 'override 只能是「快」或「慢」,拿到 {override!r}', 1),
             encoding="utf-8")
PY
python "$QA/case/$BATCH" --self-check > "$QA/g.txt" 2>&1
[ $? != 0 ]
ok $? "換回 override 那個字 -> self-check 紅"
grep -q 'AssertionError' "$QA/g.txt"
ok $? "紅在斷言上(咬的是整句,不是放寬成關鍵字)"

set +x
echo
if [ "$FAILED" = 0 ]; then echo "全部格子符合預期"; else
  echo "有格子不合預期 —— 見上面的 RESULT FAIL"; fi
exit $FAILED
