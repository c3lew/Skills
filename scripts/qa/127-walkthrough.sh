#!/usr/bin/env bash
# #127 QA walkthrough —— 同一個票號在一批裡出現兩次,當場停、不靜靜印兩條矛盾的分級。
#
# 判定 oracle = 票上「覆蓋驗收項」段的原句,只有一條:
#   1. 切票的時候,每張票都標了「快」或「慢」加一句理由,整批一次列給我看,
#      我可以當場改任何一張。
#
# #127 是 bug fix,所以範圍 = 該 bug 的重現 scenario + 票上的 Acceptance criteria。
# 每一格印出 client 螢幕上真的會看到的那幾行原文當證據,再用可機械重跑的 grep 判定。
#
# 用法:bash 127-walkthrough.sh <workdir>
# repo 本體只讀;要改壞真檔的格子一律跑在拋棄式副本上。exit 非 0 = 有格子不合預期。
PS4='+ '
set +e
ROOT="D:/Self Project/Skills"
QA="${1:?usage: 127-walkthrough.sh <workdir>}"
rm -rf "$QA"; mkdir -p "$QA"

FAILED=0
BATCH="skills/build-batch/batch.py"
export PYTHONIOENCODING=utf-8

# 拋棄式副本(改壞真檔的格子用)。glob 不展開隱藏檔,所以 .git 不會被帶走。
PRISTINE="$QA/pristine"; mkdir -p "$PRISTINE"; cp -r "$ROOT"/* "$PRISTINE/"
fresh() { rm -rf "$QA/case"; cp -r "$PRISTINE" "$QA/case"; }

# classify:把一份 JSON 餵進出貨的 batch.py,stdout / stderr 分開存 —— 這張票有
# 好幾格在問「這句話印在哪一邊、有沒有印兩遍」,混在一起就判不了。
classify() {
  printf '%s' "$1" | python "$ROOT/$BATCH" > "$QA/out.txt" 2> "$QA/err.txt"
  CL_EXIT=$?
  echo "--- stdout(client 螢幕上看到的)"; cat "$QA/out.txt"
  echo "--- stderr"; cat "$QA/err.txt"
  echo "exit $CL_EXIT"
}

# ok <上一個指令的 exit code> <說明>
ok() {
  if [ "$1" = 0 ]; then echo "RESULT PASS ($2)"; else echo "RESULT FAIL ($2)"; FAILED=1; fi
}

rows_n()  { grep -cE '^  (快|慢)(\(改不了\))? +#[0-9]+ .* — .+$' "$QA/out.txt"; }
paste_n() { grep -cE '^  #[0-9]+  分級:' "$QA/out.txt"; }

# 票上重現步驟那批:同一個 #47 兩列,一列沒覆蓋驗收項(算快)、一列有(算慢)。
P_DUP='{"mode":"classify","tickets":[
  {"number":47,"coverage":[]},
  {"number":47,"coverage":["1. 登入頁"]}],
  "titles":{"47":"登入頁"}}'
# 三重複
P_TRIPLE='{"mode":"classify","tickets":[
  {"number":47,"coverage":[]},
  {"number":47,"coverage":["1. 登入頁"]},
  {"number":47,"coverage":[]}],
  "titles":{"47":"登入頁"}}'
# 重複 + 同一列還打錯分級
P_STACK='{"mode":"classify","tickets":[
  {"number":9,"coverage":[],"override":"fast"},
  {"number":9,"coverage":["1. 登入頁"]}],
  "titles":{"9":"登入頁"}}'
# 重複 + 硬規則(judgement true)同一批,外加一張完全乾淨的
P_MIX='{"mode":"classify","tickets":[
  {"number":47,"coverage":[]},
  {"number":48,"coverage":[],"judgement":true,"override":"快"},
  {"number":47,"coverage":[]},
  {"number":49,"coverage":["1. 登入頁"]}],
  "titles":{"47":"骨架","48":"算票","49":"登入頁"}}'
# 沒有重複的乾淨批次(對照組)
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
echo "==== 情境 A  票上的重現步驟:同一張 #47 在一批裡列了兩次"
echo "====        client 會看到什麼 —— 這就是 AC1~AC4 的共同證據"
echo "==================================================================="

classify "$P_DUP"

echo "---- A1  AC1:當場停,非 0 退出(出廠時是 exit 0 靜靜印兩列)"
[ "$CL_EXIT" != 0 ]
ok $? "重複票號的批次 exit 非 0"

echo "---- A2  AC1 的另一半:不是靜靜印出兩列 —— 兩列都標著改不了、講得出為什麼"
grep -nE '^  (快|慢)\(改不了\)  #47' "$QA/out.txt"
[ "$(grep -cE '^  (快|慢)\(改不了\)  #47 登入頁 — 這個票號在這批出現 2 次' "$QA/out.txt")" = 2 ]
ok $? "兩列都掛「改不了」+ 指名重複的理由,不是兩條互相矛盾又沒說明的分級"

echo "---- A3  AC2:訊息指名是哪個票號、重複幾次"
cat "$QA/err.txt"
grep -q '停在這裡 —— #47(重複 2 次) 的分級改不了' "$QA/err.txt"
ok $? "stderr 指名 #47、講出重複 2 次"

echo "---- A4  AC2 的邊界:一張票在 stderr 只講一次(不是佔兩列就報兩次)"
[ "$(grep -o '#47' "$QA/err.txt" | wc -l)" = 1 ]
ok $? "stderr 裡 #47 只出現一次"

echo "---- A5  AC3(#118 不變):停之前整批照印 —— 這一輪的分級長什麼樣看得到"
echo "     分級列 $(rows_n) 行 / 餵進去 2 列"
{ [ "$(rows_n)" = 2 ] \
  && grep -q '^  快(改不了)  #47 登入頁 — ' "$QA/out.txt" \
  && grep -q '^  慢(改不了)  #47 登入頁 — ' "$QA/out.txt"; }
ok $? "兩列都印出來,而且車道照各自那一列的內容算(一快一慢,矛盾本身看得見)"

echo "---- A6  AC4:貼票那段整段不印(跟被拒的那張同一個處置)"
echo "     貼票行 $(paste_n) 行"
{ [ "$(paste_n)" = 0 ] && ! grep -q '點頭之後' "$QA/out.txt" \
  && grep -q '這批還不能貼' "$QA/out.txt"; }
ok $? "一行貼票用的「分級:」都沒有,而且明講「這批還不能貼」"

echo "---- A7  AC4 邊界:還不能貼那份名單講的是票不是列 —— 同一張不列兩次"
grep -n '^  #47 登入頁$' "$QA/out.txt"
[ "$(grep -c '^  #47 登入頁$' "$QA/out.txt")" = 1 ]
ok $? "名單上 #47 只出現一行"

echo "==================================================================="
echo "==== 情境 B  抬頭那句:client 讀到的「N 張 / N 列」數的到底是票還是列"
echo "==================================================================="

echo "---- B1  重現步驟那批的抬頭原文"
grep -n '^分級(' "$QA/out.txt"
grep -q '^分級(1 張、2 列,其中 1 張改不了)— 標「慢」的會演給你看,標「快」的不會:' "$QA/out.txt"
ok $? "抬頭是「1 張、2 列,其中 1 張改不了」"

echo "---- B2  反向:不能讀成「2 張,其中 1 張改不了」"
# 那樣 client 會合理推論另外那張是好的 —— 而那張不存在(票上點名的誤讀)。
! grep -q '^分級(2 張,其中 1 張改不了)' "$QA/out.txt"
ok $? "抬頭沒有讓 client 以為另外那張是好的那個數字"

echo "==================================================================="
echo "==== 情境 C  三重複 —— 要講「3 次」,不是 2 也不是 4"
echo "==================================================================="

classify "$P_TRIPLE"

echo "---- C1  三列都印,每列都說 3 次"
[ "$(grep -c '這個票號在這批出現 3 次' "$QA/out.txt")" = 3 ]
ok $? "三列各講一次「出現 3 次」"

echo "---- C2  不會數成 2 或 4(列數差一的那兩種錯法)"
{ ! grep -q '出現 2 次' "$QA/out.txt" && ! grep -q '出現 4 次' "$QA/out.txt" \
  && ! grep -q '重複 2 次' "$QA/err.txt" && ! grep -q '重複 4 次' "$QA/err.txt"; }
ok $? "整份輸出沒有 2 次 / 4 次"

echo "---- C3  抬頭跟著變成 1 張、3 列;stderr 說重複 3 次"
{ grep -q '^分級(1 張、3 列,其中 1 張改不了)' "$QA/out.txt" \
  && grep -q '停在這裡 —— #47(重複 3 次) 的分級改不了' "$QA/err.txt"; }
ok $? "抬頭 3 列、stderr 重複 3 次,兩個數字同一個來源"

echo "==================================================================="
echo "==== 情境 D  重複 + 打錯字同一列 —— 兩個理由都要看得到"
echo "====        (不然 client 刪完重跑才撞到第二個問題,一輪修一個)"
echo "==================================================================="

classify "$P_STACK"

echo "---- D1  那一列的原文"
grep -n '#9 登入頁' "$QA/out.txt"

echo "---- D2  同一列同時看得到「重複」跟「打錯字」兩句"
grep -q "^  快(改不了)  #9 登入頁 — 這個票號在這批出現 2 次 —— 同一張票只能有一列,刪掉多的再重跑;另外,你填的分級只能是「快」或「慢」,你打的是 'fast' —— 改一下再重跑$" "$QA/out.txt"
ok $? "重複講在前、原本那個理由接在後面,一次給完"

echo "---- D3  沒打錯字的那一列不會被硬接一句(它本來就沒有第二個問題)"
grep -q '^  慢(改不了)  #9 登入頁 — 這個票號在這批出現 2 次 —— 同一張票只能有一列,刪掉多的再重跑$' "$QA/out.txt"
ok $? "另一列只有重複那句,沒有多接「;另外,」"

echo "---- D4  邊界:「改不了」不會疊成兩層"
# 這一列本來就因為打錯字被拒(已經是「快(改不了)」),重複再蓋一次的話會疊。
! grep -q '(改不了)(改不了)' "$QA/out.txt"
ok $? "左欄沒有疊字"

echo "==================================================================="
echo "==== 情境 E  重複 + 硬規則同一批,外加一張乾淨的票"
echo "==================================================================="

classify "$P_MIX"

echo "---- E1  四列照印,三種情況各自講各自的話"
{ [ "$(rows_n)" = 4 ] \
  && [ "$(grep -c '^  快(改不了)  #47 骨架 — 這個票號在這批出現 2 次' "$QA/out.txt")" = 2 ] \
  && grep -q '^  慢(改不了)  #48 算票 — 動到判斷邏輯或資料寫入,硬規則一律慢' "$QA/out.txt" \
  && grep -qE '^  慢 +#49 登入頁 — 覆蓋 1 條驗收項$' "$QA/out.txt"; }
ok $? "重複兩列 + 硬規則一列 + 乾淨一列都在,理由各自不同"

echo "---- E2  抬頭:3 張、4 列,其中 2 張改不了"
grep -q '^分級(3 張、4 列,其中 2 張改不了)' "$QA/out.txt"
ok $? "張數數票(3)、列數數列(4)、改不了數票(2)"

echo "---- E3  stderr:重複那張帶次數,硬規則那張不帶(它不是重複)"
cat "$QA/err.txt"
grep -q '停在這裡 —— #47(重複 2 次)、#48 的分級改不了,理由跟著各自那一列' "$QA/err.txt"
ok $? "兩張都指名,只有重複的那張講次數"

echo "---- E4  沒被拒的 #49 沒有被連坐(它照樣有車道跟理由)"
{ ! grep -q '#49.*改不了' "$QA/out.txt" && ! grep -q '#49' "$QA/err.txt"; }
ok $? "#49 不在改不了名單、也不在 stderr"

echo "---- E5  左欄真的對齊 —— 量 east-asian 顯示欄寬,不是數字數"
PYTHONIOENCODING=utf-8 python - "$QA/out.txt" 4 <<'PY'
import io, sys, unicodedata
cols = lambda s: sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)
rows = [ln[:ln.index("#")] for ln in
        io.open(sys.argv[1], encoding="utf-8").read().splitlines()
        if ln.startswith("  ") and "#" in ln and " — " in ln]
widths = {cols(r) for r in rows}
for r in rows:
    print(f"  欄寬 {cols(r):>3}  {r!r}")
print("列數", len(rows), "不同的欄寬", sorted(widths))
sys.exit(0 if len(rows) == int(sys.argv[2]) and len(widths) == 1 else 1)
PY
ok $? "四列在票號之前佔的欄數完全相同"

echo "==================================================================="
echo "==== 情境 F  沒有重複的批次:輸出跟 #127 之前那版逐字相同"
echo "====        (#108 / #118 / #121 凍結的那份不能被這次改動動到)"
echo "==================================================================="

echo "---- F1  取出 #127 之前那版 batch.py 當母本"
git -C "$ROOT" show '7c4754a^:skills/build-batch/batch.py' > "$QA/prev-batch.py"
[ -s "$QA/prev-batch.py" ]
ok $? "拿到 7c4754a^ 的 batch.py"

diff_prev() {
  printf '%s' "$1" | python "$ROOT/$BATCH"      > "$QA/now.out" 2> "$QA/now.err"; NOW=$?
  printf '%s' "$1" | python "$QA/prev-batch.py" > "$QA/prev.out" 2> "$QA/prev.err"; PREV=$?
  echo "--- 現在這版 stdout"; cat "$QA/now.out"
  echo "--- 現在 exit $NOW / 之前 exit $PREV"
  diff "$QA/prev.out" "$QA/now.out" && diff "$QA/prev.err" "$QA/now.err" \
    && [ "$NOW" = "$PREV" ]
}

echo "---- F2  乾淨批次(全綠那條路)逐字相同"
diff_prev "$P_CLEAN"
ok $? "stdout / stderr / exit 三者都跟 #127 之前一樣"

echo "---- F3  抬頭那句尤其要咬:沒有重複就不多印「N 列」"
grep -n '^分級(' "$QA/now.out"
{ grep -q '^分級(2 張)— 標「慢」的會演給你看,標「快」的不會:' "$QA/now.out" \
  && ! grep -q '列' "$QA/now.out"; }
ok $? "抬頭是「分級(2 張)」,整份輸出沒有多出來的「列」字"

echo "---- F4  #121 那批(有被拒、但沒有重複)也逐字相同"
diff_prev "$P_121"
ok $? "被拒那條路沒被這次改動動到"

echo "---- F5  #121 那批的抬頭:是「3 張,其中 2 張改不了」,沒有列數"
grep -q '^分級(3 張,其中 2 張改不了)' "$QA/now.out"
ok $? "沒有重複的批次抬頭跟凍結的那份一樣"

echo "==================================================================="
echo "==== 情境 G  AC5:batch.py --self-check 涵蓋重複票號,而且咬整句"
echo "==================================================================="

echo "---- G1  出貨版 --self-check 綠"
python "$ROOT/$BATCH" --self-check
ok $? "batch.py --self-check exit 0"

echo "---- G2  self-check 裡真的有一段跑重複票號的批次"
grep -n '同一個票號在一批裡出現兩次' "$ROOT/$BATCH" | head -3
grep -q 'assert dupshown.startswith("分級(1 張、2 列,其中 1 張改不了)")' "$ROOT/$BATCH"
ok $? "斷言直接咬 client 看到的那句抬頭"

echo "---- G3  把理由的措辭改掉(語意不變)-> self-check 要紅在 AssertionError"
# 咬整句而不是關鍵字的話,換一種說法就要紅。跑在拋棄式副本上。
fresh
python - "$QA/case/$BATCH" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
old = '    return f"這個票號在這批出現 {count} 次 —— 同一張票只能有一列,刪掉多的再重跑"'
assert old in t, "改壞目標不在 —— 判準被改過了"
p.write_text(t.replace(old, '    return f"票號重複 {count} 次,請刪掉多的"', 1),
             encoding="utf-8")
PY
ok $? "副本上換掉措辭"
python "$QA/case/$BATCH" --self-check > "$QA/g1.txt" 2>&1
G1=$?
tail -5 "$QA/g1.txt"
[ "$G1" != 0 ]
ok $? "換掉措辭 -> self-check 紅"
grep -q 'AssertionError' "$QA/g1.txt"
ok $? "紅在斷言上 —— 咬的是整句,不是放寬成關鍵字"

echo "---- G4  抬頭的「1 張、2 列」也咬整句:改成數列 -> self-check 紅"
fresh
python - "$QA/case/$BATCH" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
old = "    seats = len({n for n, _, _ in rows})"
assert old in t, "改壞目標不在"
p.write_text(t.replace(old, "    seats = len(rows)", 1), encoding="utf-8")
PY
python "$QA/case/$BATCH" --self-check > "$QA/g2.txt" 2>&1
G2=$?
tail -3 "$QA/g2.txt"
{ [ "$G2" != 0 ] && grep -q 'AssertionError' "$QA/g2.txt"; }
ok $? "抬頭退回數列 -> self-check 紅在斷言"

echo "==================================================================="
echo "==== 情境 H  AC6:進 97-mutate.py 的 mutation 台,守門拆掉要轉紅"
echo "==================================================================="

echo "---- H1  #127 這批 knob 都在表上"
# `classify_head_counts_rows`(抬頭退回數列)名字裡沒有 dupe,但它是 #127 加的
# 第 10 格 —— 只用 dupe 撈會少一格,所以名單寫死在這裡。
K127='classify_dupe_count_hidden|classify_dupe_lane_dropped'
K127="$K127"'|classify_dupe_reason_swallowed|classify_dupe_stderr_plain'
K127="$K127"'|classify_dupes_always|classify_dupes_never_found'
K127="$K127"'|classify_dupes_not_marked|classify_rejected_not_deduped'
K127="$K127"'|classify_head_counts_rows|dupe_pin_dropped'
python "$ROOT/scripts/qa/97-mutate.py" --list | grep -E "^($K127)\$"
DUPE_KNOBS="$(python "$ROOT/scripts/qa/97-mutate.py" --list | grep -E "^($K127)\$")"
[ "$(echo "$DUPE_KNOBS" | wc -l)" -ge 10 ]
ok $? "至少 10 個 #127 相關的 knob"

echo "---- H2  逐個 knob 改壞 -> batch.py --self-check 要轉紅"
MISSED=""
for knob in $DUPE_KNOBS; do
  fresh
  python "$ROOT/scripts/qa/97-mutate.py" "$QA/case" "$knob" > /dev/null 2>&1 || {
    echo "  套用失敗 $knob"; MISSED="$MISSED $knob"; continue; }
  python "$QA/case/$BATCH" --self-check > "$QA/k.txt" 2>&1
  KC=$?
  if [ "$KC" = 0 ]; then echo "  沒咬住  $knob"; MISSED="$MISSED $knob";
  else echo "  咬住    $knob (exit=$KC)"; fi
done
[ -z "$MISSED" ]
ok $? "每個 #127 knob 都被 batch.py 自己的 --self-check 咬住"

echo "==================================================================="
echo "==== 情境 I  AC7:slice-tickets/SKILL.md 補了這個情況怎麼辦"
echo "==================================================================="

echo "---- I1  那句散文的原文"
grep -n '同一個票號在同一批裡只能出現一次' "$ROOT/skills/slice-tickets/SKILL.md"
grep -q '同一個票號在同一批裡只能出現一次' "$ROOT/skills/slice-tickets/SKILL.md"
ok $? "SKILL.md 有這句"

echo "---- I2  講得出「怎麼修」,不是只說不行"
grep -q '刪掉多的那幾列(不是挑一列留著改分級)' "$ROOT/skills/slice-tickets/SKILL.md"
ok $? "修法寫出來了:刪多的,不是挑一列留著"

echo "---- I3  那句被 batch.py 的 CLASSIFY_LINES pin 住 —— 刪掉會轉紅"
fresh
python - "$QA/case/skills/slice-tickets/SKILL.md" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
line = [l for l in t.splitlines() if "同一個票號在同一批裡只能出現一次" in l]
assert line, "SKILL.md 裡找不到那句"
p.write_text(t.replace(line[0] + "\n", "", 1), encoding="utf-8")
PY
python "$QA/case/$BATCH" --self-check > "$QA/i.txt" 2>&1
IC=$?
tail -3 "$QA/i.txt"
[ "$IC" != 0 ]
ok $? "SKILL.md 那句刪掉 -> batch.py --self-check 紅"

set +x
echo
if [ "$FAILED" = 0 ]; then echo "全部格子符合預期"; else
  echo "有格子不合預期 —— 見上面的 RESULT FAIL"; fi
exit $FAILED
