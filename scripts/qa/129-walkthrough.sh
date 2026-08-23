#!/usr/bin/env bash
# #129 QA walkthrough —— 票號寫成字串 `"47"` / 帶空白 `" 47 "` / 全形也算同一張票,
# 型別在入口就收斂:當場停,跟 `47`/`47` 同批走**逐字相同**的那條路。
#
# 判定 oracle = 票上「覆蓋驗收項」段的原句,只有一條:
#   1. 切票的時候,每張票都標了「快」或「慢」加一句理由,整批一次列給我看,
#      我可以當場改任何一張。
#
# #129 是 bug fix,所以範圍 = 該 bug 的重現 scenario + 票上的 Acceptance criteria。
# 每一格印出 client 螢幕上真的會看到的那幾行原文當證據,再用可機械重跑的 grep /
# cmp / 顯示欄寬量測判定。
#
# 用法:bash 129-walkthrough.sh <workdir>
# repo 本體只讀;要改壞真檔的格子一律跑在拋棄式副本上。exit 非 0 = 有格子不合預期。
PS4='+ '
set +e
# ROOT 從腳本自己的位置推 —— 不寫死絕對路徑,從任何地方跑都對。
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
QA="${1:?usage: 129-walkthrough.sh <workdir>}"
rm -rf "$QA"; mkdir -p "$QA"

FAILED=0
BATCH="skills/build-batch/batch.py"
export PYTHONIOENCODING=utf-8

# 拋棄式副本(改壞真檔的格子用)。glob 不展開隱藏檔,所以 .git 不會被帶走。
PRISTINE="$QA/pristine"; mkdir -p "$PRISTINE"; cp -r "$ROOT"/* "$PRISTINE/"
fresh() { rm -rf "$QA/case"; cp -r "$PRISTINE" "$QA/case"; }

# 把一份 JSON 餵進出貨的 batch.py,stdout / stderr 分開存 —— 這張票有好幾格在問
# 「這句話印在哪一邊、有沒有印兩遍、stdout 是不是空的」,混在一起就判不了。
classify() {
  printf '%s' "$1" | python "$ROOT/$BATCH" > "$QA/out.txt" 2> "$QA/err.txt"
  CL_EXIT=$?
  echo "--- stdout(client 螢幕上看到的)"; cat "$QA/out.txt"
  echo "--- stderr"; cat "$QA/err.txt"
  echo "exit $CL_EXIT"
}

# 同一支出貨 batch.py 餵兩份 payload,stdout / stderr / exit 三樣逐字比。
# 「走同一條路」這句話在這張票上就是這個意思,不是「也會停」。
same_path() {
  printf '%s' "$1" | python "$ROOT/$BATCH" > "$QA/a.out" 2> "$QA/a.err"; A_EXIT=$?
  printf '%s' "$2" | python "$ROOT/$BATCH" > "$QA/b.out" 2> "$QA/b.err"; B_EXIT=$?
  echo "--- 型別混用那批 stdout(client 螢幕)"; cat "$QA/a.out"
  echo "--- 型別混用那批 stderr"; cat "$QA/a.err"
  echo "--- 兩批的 exit:混用 $A_EXIT / 純數字 $B_EXIT"
  diff "$QA/b.out" "$QA/a.out"; D1=$?
  diff "$QA/b.err" "$QA/a.err"; D2=$?
  cmp "$QA/b.out" "$QA/a.out" && cmp "$QA/b.err" "$QA/a.err" \
    && [ "$A_EXIT" = "$B_EXIT" ] && [ "$D1" = 0 ] && [ "$D2" = 0 ]
}

# ok <上一個指令的 exit code> <說明>
ok() {
  if [ "$1" = 0 ]; then echo "RESULT PASS ($2)"; else echo "RESULT FAIL ($2)"; FAILED=1; fi
}

rows_n()  { grep -cE '^  (快|慢)(\(改不了\))? +#[0-9]+ .* — .+$' "$QA/out.txt"; }
paste_n() { grep -cE '^  #[0-9]+  分級:' "$QA/out.txt"; }

# 量 east-asian 顯示欄寬:<檔> <幾列> <抓哪一段>
#   lane  = 分級列裡「#」之前的左欄
#   paste = 貼票行裡「分級:」之前的那一段
width_check() {
  PYTHONIOENCODING=utf-8 python - "$1" "$2" "$3" <<'PY'
import io, sys, unicodedata
cols = lambda s: sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)
lines = io.open(sys.argv[1], encoding="utf-8").read().splitlines()
kind = sys.argv[3]
if kind == "lane":
    rows = [ln[:ln.index("#")] for ln in lines
            if ln.startswith("  ") and "#" in ln and " — " in ln
            and not ln.lstrip().startswith("#")]
else:
    rows = [ln[:ln.index("分級:")] for ln in lines
            if ln.startswith("  #") and "分級:" in ln]
widths = {cols(r) for r in rows}
for r in rows:
    print(f"  欄寬 {cols(r):>3}  {r!r}")
print("列數", len(rows), "不同的欄寬", sorted(widths))
sys.exit(0 if len(rows) == int(sys.argv[2]) and len(widths) == 1 else 1)
PY
}

# ---- payload -------------------------------------------------------------
# 票上重現步驟那批:同一張 #47 兩列,一列票號是數字 47、一列寫成字串 "47"。
P_ALIAS='{"mode":"classify","tickets":[
  {"number":47,"coverage":[]},
  {"number":"47","coverage":["1. 登入頁"]}],
  "titles":{"47":"登入頁"}}'
# 同一批,但兩列都寫成數字 47 —— 這是「同一條路」要比對的那份母本(#127 那批)
P_INT='{"mode":"classify","tickets":[
  {"number":47,"coverage":[]},
  {"number":47,"coverage":["1. 登入頁"]}],
  "titles":{"47":"登入頁"}}'
# 前後帶空白
P_SPACE='{"mode":"classify","tickets":[
  {"number":47,"coverage":[]},
  {"number":" 47 ","coverage":["1. 登入頁"]}],
  "titles":{"47":"登入頁"}}'
# 全形數字(輸入法沒切回半形的手滑)
P_FULL='{"mode":"classify","tickets":[
  {"number":47,"coverage":[]},
  {"number":"４７","coverage":["1. 登入頁"]}],
  "titles":{"47":"登入頁"}}'
# 沒有重複、但票號帶空白 / 字串 —— 這批走得完,貼票段會印出來(量欄寬用)
P_SPACE_OK='{"mode":"classify","tickets":[
  {"number":" 47 ","coverage":[]},
  {"number":"48","coverage":["1. 登入頁"]}],
  "titles":{"47":"登入頁","48":"算票"}}'
P_INT_OK='{"mode":"classify","tickets":[
  {"number":47,"coverage":[]},
  {"number":48,"coverage":["1. 登入頁"]}],
  "titles":{"47":"登入頁","48":"算票"}}'
# 三重複 + 型別混用(數字 / 字串 / 帶空白 各一)
P_TRIPLE='{"mode":"classify","tickets":[
  {"number":47,"coverage":[]},
  {"number":"47","coverage":["1. 登入頁"]},
  {"number":" 47 ","coverage":[]}],
  "titles":{"47":"登入頁"}}'
# 型別混用 + 同一列還打錯分級
P_STACK='{"mode":"classify","tickets":[
  {"number":9,"coverage":[],"override":"fast"},
  {"number":"9","coverage":["1. 登入頁"]}],
  "titles":{"9":"登入頁"}}'
# 型別混用 + 硬規則同批,外加一張乾淨的
P_MIX='{"mode":"classify","tickets":[
  {"number":"47","coverage":[]},
  {"number":48,"coverage":[],"judgement":true,"override":"快"},
  {"number":" 47 ","coverage":[]},
  {"number":"49","coverage":["1. 登入頁"]}],
  "titles":{"47":"骨架","48":"算票","49":"登入頁"}}'
# 轉不成整數的那幾種寫法
P_BAD_CN='{"mode":"classify","tickets":[
  {"number":47,"coverage":[]},
  {"number":"四十七","coverage":[]}]}'
P_BAD_47_0='{"mode":"classify","tickets":[{"number":47.0,"coverage":[]}]}'
P_BAD_47_9='{"mode":"classify","tickets":[{"number":47.9,"coverage":[]}]}'
P_BAD_NULL='{"mode":"classify","tickets":[{"coverage":[]}]}'
P_BAD_HASH='{"mode":"classify","tickets":[{"number":"#47","coverage":[]}]}'
P_BAD_TITLEKEY='{"mode":"classify","tickets":[{"number":47}],"titles":{"四七":"登入頁"}}'
P_BAD_BLOCKED='{"mode":"plan","tickets":[
  {"number":48,"state":"open","blocked_by":["四十七"]}],"titles":{"48":"b"}}'
# 別的 mode:split(`numbers` / `fixing`)
P_SPLIT='{"mode":"split","numbers":[47,"48"],"fixing":["48"],
  "titles":{"47":"a","48":"b"}}'
P_SPLIT_INT='{"mode":"split","numbers":[47,48],"fixing":[48],
  "titles":{"47":"a","48":"b"}}'
# 別的 mode:plan(`blocked_by`)
P_PLAN='{"mode":"plan","tickets":[
  {"number":47,"state":"open","blocked_by":[]},
  {"number":"48","state":"open","blocked_by":["47"]}],
  "titles":{"47":"a","48":"b"}}'
P_PLAN_INT='{"mode":"plan","tickets":[
  {"number":47,"state":"open","blocked_by":[]},
  {"number":48,"state":"open","blocked_by":[47]}],
  "titles":{"47":"a","48":"b"}}'
# 對照組:沒有重複、票號全是裸整數的乾淨批次(要跟修前逐字相同)
P_CLEAN='{"mode":"classify","tickets":[
  {"number":48,"coverage":[],"judgement":false},
  {"number":49,"coverage":["1. 登入頁"]}],
  "titles":{"48":"骨架","49":"登入頁"}}'
# #121 那批(有被拒、但沒有重複)—— 凍結輸出的第二個對照組
P_121='{"mode":"classify","tickets":[
  {"number":48,"coverage":[],"judgement":false},
  {"number":49,"coverage":[],"judgement":true,"override":"快"},
  {"number":50,"coverage":["1. 登入頁"],"override":"fast"}],
  "titles":{"48":"骨架","49":"算票","50":"登入頁"}}'

set -x

echo "==================================================================="
echo "==== 情境 O  修前長什麼樣 —— 票上「實際」那段,證明這個洞真的存在過"
echo "====        (對照用,不是 AC;下面每一格都跟這個對照著看)"
echo "==================================================================="

echo "---- O1  取出 #129 修法之前那版 batch.py 當母本"
git -C "$ROOT" show '643f683^:skills/build-batch/batch.py' > "$QA/prev-batch.py"
[ -s "$QA/prev-batch.py" ]
ok $? "拿到 643f683^ 的 batch.py"

echo "---- O2  修前:47 + \"47\" 同批 —— client 螢幕上兩列矛盾的分級、貼票段照印、exit 0"
printf '%s' "$P_ALIAS" | python "$QA/prev-batch.py" > "$QA/prev.out" 2> "$QA/prev.err"
PREV_EXIT=$?
echo "--- 修前 stdout"; cat "$QA/prev.out"
echo "--- 修前 stderr"; cat "$QA/prev.err"; echo "修前 exit $PREV_EXIT"
{ [ "$PREV_EXIT" = 0 ] \
  && [ "$(grep -c '^  #47  分級:' "$QA/prev.out")" = 2 ] \
  && [ ! -s "$QA/prev.err" ]; }
ok $? "修前確實是 exit 0、貼票段印兩行同一張 #47、stderr 空的(票上「實際」那段)"

echo "---- O3  修前:\" 47 \" 那版左欄與貼票行直接歪掉"
printf '%s' "$P_SPACE" | python "$QA/prev-batch.py" > "$QA/prevsp.out" 2>&1
echo "--- 修前 stdout"; cat "$QA/prevsp.out"
{ grep -q '^  慢  # 47 — ' "$QA/prevsp.out" \
  && grep -q '^  # 47   分級:慢' "$QA/prevsp.out"; }
ok $? "修前印的是 '# 47'(歪掉),票上那段原文重現得出來"

echo "==================================================================="
echo "==== 情境 A  AC1:票上重現步驟 —— 47 + \"47\" 同批,client 現在會看到什麼"
echo "==================================================================="

classify "$P_ALIAS"

echo "---- A1  AC1:當場停,非 0 退出(修前是 exit 0)"
[ "$CL_EXIT" != 0 ]
ok $? "型別混用的重複票號批次 exit 非 0"

echo "---- A2  AC1「整批照印」:兩列都印出來,而且都標得出車道"
echo "     分級列 $(rows_n) 行 / 餵進去 2 列"
{ [ "$(rows_n)" = 2 ] \
  && grep -q '^  快(改不了)  #47 登入頁 — ' "$QA/out.txt" \
  && grep -q '^  慢(改不了)  #47 登入頁 — ' "$QA/out.txt"; }
ok $? "兩列照印、各自算得出車道(一快一慢,矛盾本身看得見)"

echo "---- A3  AC1:兩列都掛「改不了」+ 講得出為什麼"
grep -nE '^  (快|慢)\(改不了\)  #47' "$QA/out.txt"
[ "$(grep -cE '^  (快|慢)\(改不了\)  #47 登入頁 — 這個票號在這批出現 2 次 —— 同一張票只能有一列,刪掉多的再重跑$' "$QA/out.txt")" = 2 ]
ok $? "兩列都指名重複的理由,不是兩條互相矛盾又沒說明的分級"

echo "---- A4  AC1「貼票段不印」"
echo "     貼票行 $(paste_n) 行"
{ [ "$(paste_n)" = 0 ] && ! grep -q '點頭之後' "$QA/out.txt" \
  && grep -q '這批還不能貼' "$QA/out.txt"; }
ok $? "一行貼票用的「分級:」都沒有,而且明講「這批還不能貼」"

echo "---- A5  AC1「stderr 指名票號與次數」"
cat "$QA/err.txt"
grep -q '^停在這裡 —— #47(重複 2 次) 的分級改不了,理由跟著各自那一列$' "$QA/err.txt"
ok $? "stderr 指名 #47、講出重複 2 次"

echo "---- A6  邊界:一張票在 stderr 只講一次(佔兩列不等於報兩次)"
[ "$(grep -o '#47' "$QA/err.txt" | wc -l)" = 1 ]
ok $? "stderr 裡 #47 只出現一次"

echo "---- A7  抬頭數的是票不是列:「1 張、2 列,其中 1 張改不了」"
grep -n '^分級(' "$QA/out.txt"
{ grep -q '^分級(1 張、2 列,其中 1 張改不了)— 標「慢」的會演給你看,標「快」的不會:$' "$QA/out.txt" \
  && ! grep -q '^分級(2 張' "$QA/out.txt"; }
ok $? "抬頭是「1 張、2 列」—— 不會讓 client 以為另外那張是好的"

echo "---- A8  邊界:還不能貼那份名單講的是票不是列 —— 同一張不列兩次"
grep -n '^  #47 登入頁$' "$QA/out.txt"
[ "$(grep -c '^  #47 登入頁$' "$QA/out.txt")" = 1 ]
ok $? "名單上 #47 只出現一行"

echo "==================================================================="
echo "==== 情境 B  AC1 的後半:跟 47 / 47 同批走**同一條路**"
echo "====        stdout + stderr + exit 三樣逐字相同,不是「也會停」"
echo "==================================================================="

echo "---- B1  47 + \"47\"  vs  47 + 47"
same_path "$P_ALIAS" "$P_INT"
ok $? "字串票號那批跟純數字那批 stdout / stderr / exit 三樣逐字相同"

echo "---- B2  47 + \" 47 \"  vs  47 + 47(AC2 的同一條路)"
same_path "$P_SPACE" "$P_INT"
ok $? "帶前後空白那批也逐字相同"

echo "---- B3  47 + \"４７\"(全形)vs  47 + 47"
same_path "$P_FULL" "$P_INT"
ok $? "全形票號那批也逐字相同"

echo "==================================================================="
echo "==== 情境 C  AC2:帶空白的票號認得出來,而且左欄與貼票行不會歪掉"
echo "====        用一批「有空白但沒有重複」的票 —— 這批走得完,貼票段會印出來"
echo "==================================================================="

classify "$P_SPACE_OK"

echo "---- C1  client 螢幕上看到的是 #47,不是 '# 47'"
{ [ "$CL_EXIT" = 0 ] && ! grep -q '# 47' "$QA/out.txt" \
  && grep -q '^  快  #47 登入頁 — 沒有覆蓋驗收項,不會有你看得到的行為$' "$QA/out.txt" \
  && grep -q '^  #47  分級:快 — 沒有覆蓋驗收項,不會有你看得到的行為$' "$QA/out.txt"; }
ok $? "分級列與貼票行印的都是 #47,整份輸出沒有一個 '# 47'"

echo "---- C2  左欄真的對齊 —— 量 east-asian 顯示欄寬,不是 grep 一個恆真的 pattern"
width_check "$QA/out.txt" 2 lane
ok $? "兩列在票號之前佔的顯示欄數完全相同"

echo "---- C3  貼票行也對齊 —— 量「分級:」之前那一段的顯示欄寬"
width_check "$QA/out.txt" 2 paste
ok $? "兩行貼票行在「分級:」之前佔的顯示欄數完全相同"

echo "---- C4  同一批全寫成裸整數 —— 逐字相同(空白根本沒留下痕跡)"
same_path "$P_SPACE_OK" "$P_INT_OK"
ok $? "帶空白那批跟裸整數那批 stdout / stderr / exit 逐字相同"

echo "---- C5  反向對照:修前同一批的貼票行欄寬不一致(歪掉的那個形狀)"
printf '%s' "$P_SPACE_OK" | python "$QA/prev-batch.py" > "$QA/prevok.out" 2>&1
cat "$QA/prevok.out"
width_check "$QA/prevok.out" 2 paste
[ "$?" != 0 ]
ok $? "修前那版量得出欄寬不一致 —— C3 量的是真的東西,不是恆真"

echo "==================================================================="
echo "==== 情境 D  AC3:票號轉不成整數時當場停,指名哪一列 + 他填了什麼"
echo "====        不是裸 traceback。同型全掃:七種填法一次列完"
echo "==================================================================="

# bad <payload> <期待的 stderr 整句> <說明>
bad() {
  printf '%s' "$1" | python "$ROOT/$BATCH" > "$QA/bad.out" 2> "$QA/bad.err"
  BAD_EXIT=$?
  echo "--- stdout(client 螢幕)"; cat "$QA/bad.out"
  echo "--- stderr"; cat "$QA/bad.err"; echo "exit $BAD_EXIT"
  { [ "$BAD_EXIT" != 0 ] \
    && ! grep -q 'Traceback' "$QA/bad.err" \
    && [ ! -s "$QA/bad.out" ] \
    && [ "$(wc -l < "$QA/bad.err")" -le 1 ] \
    && grep -qF "$2" "$QA/bad.err"; }
  ok $? "$3"
}

echo "---- D1  \"四十七\":指名是第 2 列、他填的是什麼"
bad "$P_BAD_CN" \
  "停在這裡 —— 第 2 列的票號不是數字,他填的是 '四十七' —— 改成票號那個數字(像 47 這樣)再重跑" \
  "停得有聲、指名第 2 列與他填的字,沒有 traceback,stdout 是空的"

echo "---- D2  47.0(review 宣告過的天花板:小數一律停,但要停得有聲)"
bad "$P_BAD_47_0" \
  "停在這裡 —— 第 1 列的票號不是數字,他填的是 47.0 —— 改成票號那個數字(像 47 這樣)再重跑" \
  "47.0 停下來,而且訊息講得出他填的是 47.0(不是靜靜當成 47)"

echo "---- D3  47.9(靜靜捨成 47 就是換了一張票 —— 這裡不許無聲)"
bad "$P_BAD_47_9" \
  "停在這裡 —— 第 1 列的票號不是數字,他填的是 47.9 —— 改成票號那個數字(像 47 這樣)再重跑" \
  "47.9 停下來且講得出原值"

echo "---- D4  票號那一格根本沒填(null)"
bad "$P_BAD_NULL" \
  "停在這裡 —— 第 1 列的票號不是數字,他填的是 None —— 改成票號那個數字(像 47 這樣)再重跑" \
  "沒填也停得有聲"

echo "---- D5  \"#47\"(把井字號一起抄進去 —— 票上點名的手滑射程)"
bad "$P_BAD_HASH" \
  "停在這裡 —— 第 1 列的票號不是數字,他填的是 '#47' —— 改成票號那個數字(像 47 這樣)再重跑" \
  "帶 # 的票號停得有聲、原文回貼給 client"

echo "---- D6  \`titles\` 那份標題表的 key 壞掉(review 收掉的第二個洞)"
bad "$P_BAD_TITLEKEY" \
  "停在這裡 —— \`titles\` 那份標題表裡的票號不是數字,他填的是 '四七' —— 改成票號那個數字(像 47 這樣)再重跑" \
  "標題表的壞 key 也走同一支,講得出是哪一格"

echo "---- D7  \`blocked_by\`(卡在誰後面)那份名單裡的票號壞掉"
bad "$P_BAD_BLOCKED" \
  "停在這裡 —— 第 1 列的「卡在誰後面」那份名單裡的票號不是數字,他填的是 '四十七' —— 改成票號那個數字(像 47 這樣)再重跑" \
  "卡關名單也指名得出是哪一列的哪一份名單"

echo "---- D8  全掃:七格的訊息長同一個樣子(同一支函式,不是七種寫法)"
for p in "$P_BAD_CN" "$P_BAD_47_0" "$P_BAD_47_9" "$P_BAD_NULL" "$P_BAD_HASH" \
         "$P_BAD_TITLEKEY" "$P_BAD_BLOCKED"; do
  printf '%s' "$p" | python "$ROOT/$BATCH" 2>&1 >/dev/null
done > "$QA/allbad.txt" 2>&1
cat "$QA/allbad.txt"
{ [ "$(grep -c '^停在這裡 —— .*不是數字,他填的是 .* —— 改成票號那個數字(像 47 這樣)再重跑$' "$QA/allbad.txt")" = 7 ] \
  && ! grep -q 'Traceback' "$QA/allbad.txt"; }
ok $? "七格全部同一句型、全部沒有 traceback"

echo "==================================================================="
echo "==== 情境 E  邊界:型別混用疊上別的問題,兩邊的話都要看得到"
echo "==================================================================="

echo "---- E1  三重複 + 型別混用(47 / \"47\" / \" 47 \")—— 要講 3 次"
classify "$P_TRIPLE"
{ [ "$(grep -c '這個票號在這批出現 3 次' "$QA/out.txt")" = 3 ] \
  && ! grep -q '出現 2 次' "$QA/out.txt" && ! grep -q '出現 4 次' "$QA/out.txt" \
  && grep -q '^分級(1 張、3 列,其中 1 張改不了)' "$QA/out.txt" \
  && grep -q '停在這裡 —— #47(重複 3 次) 的分級改不了' "$QA/err.txt"; }
ok $? "三種寫法算成同一張 #47、次數是 3、抬頭與 stderr 同一個來源"

echo "---- E2  型別混用 + 同一列打錯分級 —— 兩個理由一次給完"
classify "$P_STACK"
grep -n '#9 登入頁' "$QA/out.txt"
{ grep -q "^  快(改不了)  #9 登入頁 — 這個票號在這批出現 2 次 —— 同一張票只能有一列,刪掉多的再重跑;另外,你填的分級只能是「快」或「慢」,你打的是 'fast' —— 改一下再重跑$" "$QA/out.txt" \
  && grep -q '^  慢(改不了)  #9 登入頁 — 這個票號在這批出現 2 次 —— 同一張票只能有一列,刪掉多的再重跑$' "$QA/out.txt" \
  && ! grep -q '(改不了)(改不了)' "$QA/out.txt"; }
ok $? "重複講在前、打錯字接在後,另一列不會被硬接一句,左欄沒疊字"

echo "---- E3  型別混用 + 硬規則 + 一張乾淨的同批"
classify "$P_MIX"
{ [ "$(rows_n)" = 4 ] \
  && [ "$(grep -c '^  快(改不了)  #47 骨架 — 這個票號在這批出現 2 次' "$QA/out.txt")" = 2 ] \
  && grep -q '^  慢(改不了)  #48 算票 — 動到判斷邏輯或資料寫入,硬規則一律慢' "$QA/out.txt" \
  && grep -qE '^  慢 +#49 登入頁 — 覆蓋 1 條驗收項$' "$QA/out.txt" \
  && grep -q '^分級(3 張、4 列,其中 2 張改不了)' "$QA/out.txt" \
  && grep -q '停在這裡 —— #47(重複 2 次)、#48 的分級改不了' "$QA/err.txt" \
  && ! grep -q '#49' "$QA/err.txt"; }
ok $? "四列各講各的、抬頭 3 張 4 列 2 張改不了、沒被拒的 #49 沒被連坐"

echo "---- E4  這一批的左欄也真的對齊(四列,量顯示欄寬)"
width_check "$QA/out.txt" 4 lane
ok $? "四列在票號之前佔的顯示欄數完全相同"

echo "==================================================================="
echo "==== 情境 F  同一個洞換個 mode 還在不在 —— split / plan 的票號名單"
echo "==================================================================="

echo "---- F1  split:{\"numbers\":[47,\"48\"],\"fixing\":[\"48\"]} —— 兩張的標題都印得出來"
classify "$P_SPLIT"
{ [ "$CL_EXIT" = 0 ] \
  && grep -q '^  #47 a$' "$QA/out.txt" && grep -q '^  #48 b$' "$QA/out.txt" \
  && grep -q '^已收(1 張)' "$QA/out.txt" && grep -q '^還在修(1 張)' "$QA/out.txt"; }
ok $? "\"48\" 那張的標題沒有靜靜少印(修前是查不到標題就只印 #48)"

echo "---- F2  split:跟全裸整數那份逐字相同"
same_path "$P_SPLIT" "$P_SPLIT_INT"
ok $? "split 的型別混用版跟純整數版逐字相同"

echo "---- F3  plan:\"48\" 卡在 \"47\" 後面 —— 兩份名單的 key 對得起來"
classify "$P_PLAN"
{ [ "$CL_EXIT" = 0 ] && grep -q '^  #48 b — 卡在 #47$' "$QA/out.txt" \
  && ! grep -q '卡在一個' "$QA/out.txt"; }
ok $? "卡關那張講得出是卡在 #47,不是卡在一個沒見過的票號"

echo "---- F4  plan:跟全裸整數那份逐字相同"
same_path "$P_PLAN" "$P_PLAN_INT"
ok $? "plan 的型別混用版跟純整數版逐字相同"

echo "==================================================================="
echo "==== 情境 G  AC4 對照組:沒有重複的乾淨批次,輸出跟修前逐字相同"
echo "====        (證明停的是型別 alias,不是這次改動把別的路一起動到了)"
echo "==================================================================="

diff_prev() {
  printf '%s' "$1" | python "$ROOT/$BATCH"      > "$QA/now.out" 2> "$QA/now.err"; NOW=$?
  printf '%s' "$1" | python "$QA/prev-batch.py" > "$QA/pv.out"  2> "$QA/pv.err";  PV=$?
  echo "--- 現在這版 stdout(client 螢幕)"; cat "$QA/now.out"
  echo "--- 現在 exit $NOW / 修前 exit $PV"
  diff "$QA/pv.out" "$QA/now.out" && diff "$QA/pv.err" "$QA/now.err" \
    && [ "$NOW" = "$PV" ]
}

echo "---- G1  乾淨批次(全綠那條路)逐字相同"
diff_prev "$P_CLEAN"
ok $? "stdout / stderr / exit 三者都跟 #129 修前一樣"

echo "---- G2  抬頭那句尤其要咬:沒有重複就不多印「N 列」"
grep -n '^分級(' "$QA/now.out"
{ grep -q '^分級(2 張)— 標「慢」的會演給你看,標「快」的不會:$' "$QA/now.out" \
  && ! grep -q '列' "$QA/now.out"; }
ok $? "抬頭是「分級(2 張)」,整份輸出沒有多出來的「列」字"

echo "---- G3  #121 那批(有被拒、但沒有重複)也逐字相同"
diff_prev "$P_121"
ok $? "被拒那條路沒被這次改動動到"

echo "---- G4  #127 那批(真的有重複、票號全是整數)也逐字相同"
diff_prev "$P_INT"
ok $? "#127 擋下來的那條路一個字都沒變"

echo "==================================================================="
echo "==== 情境 H  AC5 / AC6 的使用者面:守門拆掉,client 螢幕會退回什麼"
echo "==================================================================="

echo "---- H1  出貨版 --self-check 綠"
python "$ROOT/$BATCH" --self-check
ok $? "batch.py --self-check exit 0"

echo "---- H2  self-check 真的有一段跑型別混用,而且斷言咬整句"
grep -n '票號寫成字串' "$ROOT/$BATCH" | head -3
{ grep -q 'assert aliased == dup, aliased' "$ROOT/$BATCH" \
  && grep -q 'assert format_classify(aliased, {47: "登入頁"}) == dupshown, aliased' "$ROOT/$BATCH" \
  && grep -q '停在這裡 —— 第 2 列的票號不是數字,他填的是 .四十七. —— ' "$ROOT/$BATCH"; }
ok $? "斷言直接咬「跟純整數那批逐字相同」與那整句錯誤訊息"

echo "---- H3  把正規化整條拆掉(97-mutate 的 ticket_number_not_normalized)"
echo "        —— client 螢幕要退回 #129 出廠的形狀,而 self-check 要轉紅"
fresh
python "$ROOT/scripts/qa/97-mutate.py" "$QA/case" ticket_number_not_normalized
ok $? "副本上套用 knob"
printf '%s' "$P_ALIAS" | python "$QA/case/$BATCH" > "$QA/h.out" 2> "$QA/h.err"
H_EXIT=$?
echo "--- 守門拆掉之後 client 螢幕"; cat "$QA/h.out"
echo "--- stderr"; cat "$QA/h.err"; echo "exit $H_EXIT"
{ [ "$H_EXIT" = 0 ] && [ "$(grep -c '^  #47  分級:' "$QA/h.out")" = 2 ]; }
ok $? "拆掉之後真的退回「兩列矛盾的分級、貼票段照印、exit 0」—— 這格量的是活的東西"
python "$QA/case/$BATCH" --self-check > "$QA/h-self.txt" 2>&1
HS=$?
tail -4 "$QA/h-self.txt"
{ [ "$HS" != 0 ] && grep -q 'AssertionError' "$QA/h-self.txt"; }
ok $? "同一個 knob 讓 --self-check 紅在 AssertionError"

echo "---- H4  #129 這批 knob 逐個改壞 -> --self-check 都要轉紅"
K129='ticket_number_not_normalized|ticket_number_int_truncates'
K129="$K129"'|ticket_number_bare_traceback|blocked_by_not_normalized'
K129="$K129"'|number_lists_not_normalized|titles_key_bare_int'
python "$ROOT/scripts/qa/97-mutate.py" --list | grep -E "^($K129)\$"
KNOBS="$(python "$ROOT/scripts/qa/97-mutate.py" --list | grep -E "^($K129)\$")"
[ "$(echo "$KNOBS" | wc -l)" = 6 ]
ok $? "6 個型別/空白 alias 那一類的 knob 都在表上(票上說出廠時一格都沒有)"
MISSED=""
for knob in $KNOBS; do
  fresh
  python "$ROOT/scripts/qa/97-mutate.py" "$QA/case" "$knob" > /dev/null 2>&1 || {
    echo "  套用失敗 $knob"; MISSED="$MISSED $knob"; continue; }
  python "$QA/case/$BATCH" --self-check > "$QA/k.txt" 2>&1
  KC=$?
  if [ "$KC" = 0 ]; then echo "  沒咬住  $knob"; MISSED="$MISSED $knob";
  else echo "  咬住    $knob (exit=$KC)"; fi
done
[ -z "$MISSED" ]
ok $? "每個 #129 knob 都被 batch.py 自己的 --self-check 咬住"

echo "---- H5  工作區沒被弄髒(所有改壞都跑在拋棄式副本上)"
# 只看被追蹤的檔有沒有被動到 —— 未追蹤的新檔(這支腳本自己進 repo 之前)不算髒
git -C "$ROOT" status --porcelain -- skills scripts | grep -v '^?? '
[ -z "$(git -C "$ROOT" status --porcelain -- skills scripts | grep -v '^?? ')" ]
ok $? "skills / scripts 底下被追蹤的檔一個都沒被動到"

set +x
echo
if [ "$FAILED" = 0 ]; then echo "全部格子符合預期"; else
  echo "有格子不合預期 —— 見上面的 RESULT FAIL"; fi
exit $FAILED
