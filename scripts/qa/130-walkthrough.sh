#!/usr/bin/env bash
# #130 QA walkthrough —— `spec` 那格票號也在入口收:client 照抄貼的下一棒指令
# (`/build-batch #108`)不再帶空白、不再指到一張不存在的票。
#
# 判定 oracle = 票上「覆蓋驗收項」段的原句,只有一條:
#   1. 切票的時候,每張票都標了「快」或「慢」加一句理由,整批一次列給我看,
#      我可以當場改任何一張。
#
# #130 是 bug fix,所以範圍 = 票上的重現 scenario + 票上的 Acceptance criteria:
#   AC1  `spec` 帶前後空白時印出來的指令是 `/build-batch #108`,client 照抄貼得動
#   AC2  `spec` 轉不成整數(`108.0` / `"一〇八"` / null)當場停,訊息指名是 `spec`
#        那格、他填的是什麼,不要裸 traceback
#   AC3  四個用到 `spec` 的 mode(interrupted / merged 全綠 / merged 有人還在修 /
#        summary)各有一段咬整句的 self-check 斷言
#   AC4  `97-mutate.py` 補 knob:把 `spec` 的正規化拆掉要轉紅
#   AC5  `129-wide.py` 母體補進 `spec` 的型別混用,重跑違例 0
#
# 覆蓋驗收項那條原句本身也要有證據(不能因為「這是 bug fix」就跳過):情境 F 端到端
# 走 `classify` 那條路 —— 整批一次列出、每張都標快/慢、每張都有一句理由、client 當場
# 改任何一張;而且那批的票號刻意混型別,#130 收的就是同一個入口。
#
# 每一格印出 client 螢幕上真的會看到的那幾行原文當證據,再用可機械重跑的
# grep / cmp / shell 自己斷詞判定。stdout / stderr 分開存 —— 這張票有格子在
# 問「這句印在哪一邊、stdout 是不是空的」,混在一起就判不了。
#
# 用法:bash 130-walkthrough.sh <workdir>
# repo 本體只讀;要改壞真檔的格子一律跑在拋棄式副本上。exit 非 0 = 有格子不合預期。
PS4='+ '
set +e
# ROOT 從腳本自己的位置推 —— 不寫死絕對路徑,從任何地方跑都對。
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
QA="${1:?usage: 130-walkthrough.sh <workdir>}"
rm -rf "$QA"; mkdir -p "$QA"

FAILED=0
BATCH="skills/build-batch/batch.py"
export PYTHONIOENCODING=utf-8

# 拋棄式副本(改壞真檔的格子用)。用 `git archive HEAD` 而不是 `cp -r`:這支要量的是
# **這一版 commit** 的行為,工作區裡別條 lane 還沒進 repo 的半成品(QA 是三線並行跑的)
# 不該混進來 —— 混進來的話 `validate.py --self-check` 會紅在別人的檔上,量到的就不是 #130。
PRISTINE="$QA/pristine"; mkdir -p "$PRISTINE"
git -C "$ROOT" archive HEAD | tar -x -C "$PRISTINE"
fresh() { rm -rf "$QA/case"; cp -r "$PRISTINE" "$QA/case"; }

# ok <上一個指令的 exit code> <說明>
ok() {
  if [ "$1" = 0 ]; then echo "RESULT PASS ($2)"; else echo "RESULT FAIL ($2)"; FAILED=1; fi
}

# 餵一份 JSON 給出貨的 batch.py。stdout / stderr 分開存;Windows 的 python 會吐
# CRLF,存檔時把 \r 去掉,grep 的行尾錨點才咬得住(兩邊都同樣處理,cmp 照樣公平)。
# runp <payload> [<batch.py 路徑>]
runp() {
  BIN="${2:-$ROOT/$BATCH}"
  printf '%s' "$1" | python "$BIN" > "$QA/out.raw" 2> "$QA/err.raw"
  RC=$?
  tr -d '\r' < "$QA/out.raw" > "$QA/out.txt"
  tr -d '\r' < "$QA/err.raw" > "$QA/err.txt"
  echo "--- stdout(client 螢幕上看到的)"; cat "$QA/out.txt"
  echo "--- stderr"; cat "$QA/err.txt"
  echo "exit $RC"
}

# 同一支出貨 batch.py 餵兩份 payload,stdout / stderr / exit 三樣逐字比。
same_path() {
  printf '%s' "$1" | python "$ROOT/$BATCH" > "$QA/a.out" 2> "$QA/a.err"; A_EXIT=$?
  printf '%s' "$2" | python "$ROOT/$BATCH" > "$QA/b.out" 2> "$QA/b.err"; B_EXIT=$?
  echo "--- \` 108 \` 那批 stdout(client 螢幕)"; tr -d '\r' < "$QA/a.out"
  echo "--- 兩批的 exit:帶空白 $A_EXIT / 裸整數 $B_EXIT"
  diff "$QA/b.out" "$QA/a.out"; D1=$?
  diff "$QA/b.err" "$QA/a.err"; D2=$?
  cmp "$QA/b.out" "$QA/a.out" && cmp "$QA/b.err" "$QA/a.err" \
    && [ "$A_EXIT" = "$B_EXIT" ] && [ "$D1" = 0 ] && [ "$D2" = 0 ]
}

# 反引號裡那幾行「照抄貼進終端機」的下一棒指令,把指令連參數整段撈出來。
paste_cmds() {
  grep -oE '`[$/][a-z-]+ [^`]*`' "${1:-$QA/out.txt}" | sed 's/^`//; s/`$//'
}

# 「貼得動」不靠肉眼。量的是 shell 自己的斷詞規則:照抄貼的那一行斷成幾個 token。
# `/build-batch #108` 是 2 個(指令 + 參數 `#108`);`/build-batch # 108` 是 3 個,
# 第 2 個是**裸 `#`** —— 裸 `#` 在 bash 與 PowerShell 都是註解起頭,`108` 連同後面
# 整行被吃掉,貼上去等於什麼都沒跑。
# 這裡刻意用 shell 的 word splitting(`set -f` 關掉萬用字元展開),不是自己寫 regex
# 數空白 —— 斷詞規則由 shell 本人給。
paste_tokens() { ( set -f; set -- $1; echo "$#" ); }
paste_arg2()   { ( set -f; set -- $1; echo "$2" ); }

# 一格:餵一個印 spec 的 mode,驗 client 螢幕上那句話 + 貼得動
# spec_cell <payload> <期待的整句(原文)>
spec_cell() {
  runp "$1"
  echo "--- 反引號裡照抄貼的下一棒指令:"
  paste_cmds > "$QA/cmds.txt"; cat "$QA/cmds.txt"
  BADARG=0
  [ -s "$QA/cmds.txt" ] || BADARG=1
  while IFS= read -r c; do
    echo "    '$c' -> shell 斷成 $(paste_tokens "$c") 個 token,參數是 '$(paste_arg2 "$c")'"
    [ "$(paste_tokens "$c")" = 2 ] || BADARG=1
    paste_arg2 "$c" | grep -qE '^#[0-9]+$' || BADARG=1
  done < "$QA/cmds.txt"
  { [ "$RC" = 0 ] && [ ! -s "$QA/err.txt" ] \
    && grep -qF "$2" "$QA/out.txt" \
    && ! grep -q '# 108' "$QA/out.txt" \
    && [ "$BADARG" = 0 ]; }
}

# ---- payload ------------------------------------------------------------
# 票上重現步驟那兩份,原文照抄
R_INTERRUPTED='{"mode":"interrupted","numbers":[47],"spec":" 108 ","titles":{"47":"a"}}'
R_MERGED_BAD='{"mode":"merged","numbers":[47],"spec":108.0,"titles":{"47":"a"}}'
# 四個印 `spec` 的地方(git show 2ebbc89 -- batch.py 點名的那四處:
# format_lane_interrupted / format_batch_done 的全綠那半與有人還在修那半 /
# format_batch_summary 的交棒行),同一張 #108 寫成 `" 108 "`
P_INTR='{"mode":"interrupted","numbers":[47],"spec":" 108 ","titles":{"47":"a"}}'
P_DONE='{"mode":"merged","numbers":[47],"spec":" 108 ","titles":{"47":"a"}}'
P_FIXING='{"mode":"merged","numbers":[47,48],"spec":" 108 ","fixing":[48],"titles":{"47":"a","48":"b"}}'
P_SUMMARY='{"mode":"summary","numbers":[47],"spec":" 108 ","titles":{"47":"a"},"coverage":{"47":["1. 登入頁"]}}'
# 同樣四份,但 spec 寫成裸整數 108 —— 「逐字相同」要比對的母本
P_INTR_INT='{"mode":"interrupted","numbers":[47],"spec":108,"titles":{"47":"a"}}'
P_DONE_INT='{"mode":"merged","numbers":[47],"spec":108,"titles":{"47":"a"}}'
P_FIXING_INT='{"mode":"merged","numbers":[47,48],"spec":108,"fixing":[48],"titles":{"47":"a","48":"b"}}'
P_SUMMARY_INT='{"mode":"summary","numbers":[47],"spec":108,"titles":{"47":"a"},"coverage":{"47":["1. 登入頁"]}}'
# spec 轉不成整數的那幾種寫法
B_FLOAT='{"mode":"merged","numbers":[47],"spec":108.0,"titles":{"47":"a"}}'
B_CN='{"mode":"merged","numbers":[47],"spec":"一〇八","titles":{"47":"a"}}'
B_NULL='{"mode":"merged","numbers":[47],"spec":null,"titles":{"47":"a"}}'
B_EMPTY='{"mode":"merged","numbers":[47],"spec":"","titles":{"47":"a"}}'
B_FLOATSTR='{"mode":"merged","numbers":[47],"spec":"108.0","titles":{"47":"a"}}'
B_HASH='{"mode":"merged","numbers":[47],"spec":"#108","titles":{"47":"a"}}'
B_TAIL='{"mode":"merged","numbers":[47],"spec":"108a","titles":{"47":"a"}}'
B_URL='{"mode":"merged","numbers":[47],"spec":"https://example.invalid/1","titles":{"47":"a"}}'

set -x

echo "==================================================================="
echo "==== 情境 O  修前長什麼樣 —— 證明這個洞真的存在過(對照組,不是 AC)"
echo "==================================================================="

echo "---- O1  取出 #130 修法之前那版 batch.py 當母本"
git -C "$ROOT" show '2ebbc89^:skills/build-batch/batch.py' > "$QA/prev-batch.py"
[ -s "$QA/prev-batch.py" ]
ok $? "拿到 2ebbc89^ 的 batch.py"

echo "---- O2  票上重現步驟①(修前):spec 帶空白 -> 印出 \`/build-batch # 108 \`"
runp "$R_INTERRUPTED" "$QA/prev-batch.py"
PREV_INTR_RC="$RC"
{ [ "$PREV_INTR_RC" = 0 ] && [ ! -s "$QA/err.txt" ] \
  && grep -q '重跑 `/build-batch # 108 `' "$QA/out.txt"; }
ok $? "修前確實印出帶空白的 \`# 108 \`、exit 0、stderr 空的(票上「實際」那段)"

echo "---- O3  票上重現步驟②(修前):spec=108.0 -> 印出 \`#108.0\`,exit 0 無聲"
runp "$R_MERGED_BAD" "$QA/prev-batch.py"
{ [ "$RC" = 0 ] && [ ! -s "$QA/err.txt" ] \
  && grep -q '`/client-demo #108.0`' "$QA/out.txt"; }
ok $? "修前指到一張不存在的 #108.0、完全沒有聲音"

echo "---- O4  「貼不動」是量得出來的 —— 讓 shell 自己斷詞"
echo "     修後  '/build-batch #108'   -> $(paste_tokens '/build-batch #108') 個 token,參數 '$(paste_arg2 '/build-batch #108')'"
echo "     修前  '/build-batch # 108 ' -> $(paste_tokens '/build-batch # 108 ') 個 token,參數 '$(paste_arg2 '/build-batch # 108 ')'"
echo "     (修前那個第 2 個 token 是裸 \`#\` —— bash 與 PowerShell 都當註解起頭,"
echo "      後面的 108 整段被吃掉;實際示範:)"
bash -c 'f() { echo "拿到 $# 個參數"; }; f 108'
bash -c 'f() { echo "拿到 $# 個參數"; }; f # 108'
{ [ "$(paste_tokens '/build-batch #108')" = 2 ] \
  && [ "$(paste_arg2 '/build-batch #108')" = '#108' ] \
  && [ "$(paste_tokens '/build-batch # 108 ')" = 3 ] \
  && [ "$(paste_arg2 '/build-batch # 108 ')" = '#' ]; }
ok $? "修前斷成 3 個 token、參數是裸 \`#\`;修後是 2 個 token、參數 \`#108\` —— 這把尺是活的"

echo "==================================================================="
echo "==== 情境 A  AC1:spec 帶前後空白,四個印 spec 的 mode 各走一遍"
echo "====        client 螢幕上要是 \`#108\`,而且照抄貼得動"
echo "==================================================================="

echo "---- A1  interrupted(票上重現步驟①,修後)"
spec_cell "$P_INTR" '重跑 `/build-batch #108`(Codex: `$build-batch #108`)會接續這條 lane'
ok $? "續跑指令印成 \`/build-batch #108\`,整份輸出沒有一個 \`# 108\`,參數是單一 token \`#108\`"

echo "---- A2  merged 全綠那半"
spec_cell "$P_DONE" '1 張已合併,下一步:`/client-demo #108`(Codex: `$client-demo #108`) — 一次 demo 這批'
ok $? "交棒行印成 \`/client-demo #108\`,貼得動"

echo "---- A3  merged 有人還在修那半"
spec_cell "$P_FIXING" '下一步:`/client-demo #108`(Codex: `$client-demo #108`) — 先 demo 已收的 1 張'
ok $? "同一批裡兩種下一棒指令(\`/build #48\` 與 \`/client-demo #108\`)都貼得動"

echo "---- A4  summary 的交棒行"
spec_cell "$P_SUMMARY" '下一步:`/client-demo #108`(Codex: `$client-demo #108`)'
ok $? "spec 票上那則批次總結的交棒行也印成 \`#108\`"

echo "---- A5  全掃:四個 mode 印出來的每一段照抄貼指令,參數都是 \`#<純數字>\`"
: > "$QA/allpaste.txt"
for p in "$P_INTR" "$P_DONE" "$P_FIXING" "$P_SUMMARY"; do
  printf '%s' "$p" | python "$ROOT/$BATCH" 2>/dev/null | tr -d '\r' >> "$QA/allpaste.txt"
done
paste_cmds "$QA/allpaste.txt"
ALLN="$(paste_cmds "$QA/allpaste.txt" | wc -l)"
BADN="$(paste_cmds "$QA/allpaste.txt" | grep -cvE '^[$/][a-z-]+ #[0-9]+$')"
echo "     照抄貼指令共 $ALLN 段,不合 \`<指令> #<純數字>\` 的有 $BADN 段"
{ [ "$ALLN" -ge 8 ] && [ "$BADN" = 0 ]; }
ok $? "$ALLN 段指令全部是 \`<指令> #<純數字>\`,一段都沒歪"

echo "---- A6  每一段都拿 shell 的斷詞規則量一次(不是只有 regex 說好)"
BAD2=0
paste_cmds "$QA/allpaste.txt" | sort -u > "$QA/uniqpaste.txt"
while IFS= read -r c; do
  echo "    '$c' -> $(paste_tokens "$c") 個 token,參數 '$(paste_arg2 "$c")'"
  [ "$(paste_tokens "$c")" = 2 ] || BAD2=1
  paste_arg2 "$c" | grep -qE '^#[0-9]+$' || BAD2=1
done < "$QA/uniqpaste.txt"
[ "$BAD2" = 0 ]
ok $? "每一段照抄貼的指令都是「指令 + \`#<純數字>\`」兩個 token,沒有一個裸 \`#\`"

echo "---- A7  AC1 的後半:帶空白那批跟裸整數 108 那批**逐字相同**"
echo "     (空白根本沒在輸出裡留下痕跡,不是「也印得出來」)"
same_path "$P_INTR" "$P_INTR_INT"; S1=$?
same_path "$P_DONE" "$P_DONE_INT"; S2=$?
same_path "$P_FIXING" "$P_FIXING_INT"; S3=$?
same_path "$P_SUMMARY" "$P_SUMMARY_INT"; S4=$?
[ "$S1" = 0 ] && [ "$S2" = 0 ] && [ "$S3" = 0 ] && [ "$S4" = 0 ]
ok $? "四個 mode 的 stdout / stderr / exit 三樣都跟裸整數版逐字相同"

echo "==================================================================="
echo "==== 情境 B  AC2:spec 轉不成整數 -> 當場停,指名 \`spec\` 那格 + 他填了什麼"
echo "====        不是裸 traceback、stdout 不准有半個字"
echo "==================================================================="

# bad <payload> <期待的 stderr 整句> <說明>
bad() {
  runp "$1"
  { [ "$RC" != 0 ] \
    && ! grep -q 'Traceback' "$QA/err.txt" \
    && [ ! -s "$QA/out.txt" ] \
    && [ "$(wc -l < "$QA/err.txt")" -le 1 ] \
    && grep -qF "$2" "$QA/err.txt"; }
  ok $? "$3"
}

echo "---- B1  票上重現步驟②(修後):spec=108.0"
bad "$B_FLOAT" \
  "停在這裡 —— \`spec\` 那格票號不是數字,他填的是 108.0 —— 改成票號那個數字(像 47 這樣)再重跑" \
  "108.0 當場停、指名是 \`spec\` 那格、原值 108.0 回貼給 client,stdout 空的、沒有 traceback"

echo "---- B2  spec=\"一〇八\""
bad "$B_CN" \
  "停在這裡 —— \`spec\` 那格票號不是數字,他填的是 '一〇八' —— 改成票號那個數字(像 47 這樣)再重跑" \
  "中文數字停得有聲、原文照樣回貼"

echo "---- B3  spec 那格填 null"
bad "$B_NULL" \
  "停在這裡 —— \`spec\` 那格票號不是數字,他填的是 None —— 改成票號那個數字(像 47 這樣)再重跑" \
  "沒填也停得有聲"

echo "---- B4  同型全掃:另外五種寫得出來的壞值,訊息長同一個樣子"
for p in "$B_EMPTY" "$B_FLOATSTR" "$B_HASH" "$B_TAIL" "$B_URL"; do
  printf '%s' "$p" | python "$ROOT/$BATCH" 2>&1 >/dev/null
done > "$QA/allbad.txt" 2>&1
tr -d '\r' < "$QA/allbad.txt" > "$QA/allbad.tmp" && mv "$QA/allbad.tmp" "$QA/allbad.txt"
cat "$QA/allbad.txt"
{ [ "$(grep -c '^停在這裡 —— `spec` 那格票號不是數字,他填的是 .* —— 改成票號那個數字(像 47 這樣)再重跑$' "$QA/allbad.txt")" = 5 ] \
  && ! grep -q 'Traceback' "$QA/allbad.txt"; }
ok $? "五格全部同一句型、全部指名 \`spec\`、全部沒有 traceback"

echo "---- B5  邊界:\`spec\` 這格整個缺席 —— 票上宣告過的天花板,不在 AC 裡"
echo "     (印出來當已知狀態,不判 FAIL)"
printf '%s' '{"mode":"merged","numbers":[47],"titles":{"47":"a"}}' \
  | python "$ROOT/$BATCH" > "$QA/miss.out" 2> "$QA/miss.err"
MISS_RC=$?
tr -d '\r' < "$QA/miss.err" | tail -3
echo "exit $MISS_RC —— commit message 已宣告:key 整個缺席時仍是裸 KeyError,不在這片 AC"

echo "==================================================================="
echo "==== 情境 C  AC3 / AC4:斷言與 knob 是活的嗎"
echo "==================================================================="

echo "---- C1  出貨版 --self-check 綠"
python "$ROOT/$BATCH" --self-check
ok $? "batch.py --self-check exit 0"

echo "---- C2  AC3:四段斷言從**原始碼裡抓出來**,每一段拿去實跑對答案"
echo "        (不是 grep 一個死字串 —— 抓到的 payload 真的餵進 batch.py,"
echo "         抓到的整句真的要出現在那個 mode 的 stdout 上)"
python - "$ROOT/$BATCH" > "$QA/asserts.txt" 2>&1 <<'PY'
import ast, io, json, subprocess, sys
src = io.open(sys.argv[1], encoding="utf-8").read()
pairs = []
for node in ast.walk(ast.parse(src)):
    if not isinstance(node, ast.For):
        continue
    try:
        items = ast.literal_eval(node.iter)
    except Exception:
        continue
    if not isinstance(items, (list, tuple)):
        continue
    got = [it for it in items
           if isinstance(it, tuple) and len(it) == 2
           and isinstance(it[0], dict) and "spec" in it[0]
           and isinstance(it[1], str)]
    if len(got) == len(items) and got:
        pairs = got
print("從 batch.py 的 self-check 抓到 %d 段咬 spec 的斷言" % len(pairs))
seen, ok = [], True
for payload, want in pairs:
    tag = payload["mode"] + ("/有人還在修" if payload.get("fixing") else
                             "/全綠" if payload["mode"] == "merged" else "")
    child = subprocess.run([sys.executable, sys.argv[1]],
                           input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                           capture_output=True)
    out = child.stdout.decode("utf-8")
    hit = want in out
    print("  [%s] mode=%-12s spec=%r" % ("咬到" if hit else "沒咬到", tag, payload["spec"]))
    print("       斷言整句: %s" % want.replace("\n", " "))
    print("       實跑 exit=%d,這句%s在 stdout 上" % (child.returncode, "" if hit else "**不**"))
    if not hit or child.returncode != 0 or "# 108" in out:
        ok = False
    seen.append(tag)
print("涵蓋的 mode:", seen)
want4 = {"interrupted", "merged/全綠", "merged/有人還在修", "summary"}
print("四個印 spec 的地方都在:", want4 == set(seen))
sys.exit(0 if ok and want4 == set(seen) and len(pairs) == 4 else 1)
PY
C2=$?
cat "$QA/asserts.txt"
[ "$C2" = 0 ]
ok $? "四段斷言各對一個印 spec 的地方,整句都咬得到、都是實跑出來的原文"

echo "---- C3  AC4:97-mutate 的 spec_not_normalized —— 只把 \`spec\` 那格漏掉"
echo "        client 螢幕要退回 #130 出廠的形狀,而 --self-check 要轉紅"
python "$ROOT/scripts/qa/97-mutate.py" --list | grep -xE 'spec_not_normalized|number_scalars_not_normalized'
[ "$(python "$ROOT/scripts/qa/97-mutate.py" --list | grep -cxE 'spec_not_normalized|number_scalars_not_normalized')" = 2 ]
ok $? "兩個 #130 knob 都在表上(只漏 spec / 單格值整條關掉的對照組)"

fresh
python "$ROOT/scripts/qa/97-mutate.py" "$QA/case" spec_not_normalized
ok $? "副本上套用 spec_not_normalized"
runp "$R_INTERRUPTED" "$QA/case/$BATCH"
{ [ "$RC" = 0 ] && [ ! -s "$QA/err.txt" ] \
  && grep -q '重跑 `/build-batch # 108 `' "$QA/out.txt"; }
ok $? "拆掉之後真的退回「\`# 108 \`、exit 0、stderr 空的」—— 這格量的是活的東西"
echo "     退化後那段照抄貼的指令:$(paste_tokens '/build-batch # 108 ') 個 token,參數是裸 '$(paste_arg2 '/build-batch # 108 ')'"
python "$QA/case/$BATCH" --self-check > "$QA/c-self.txt" 2>&1
CS=$?
tail -6 "$QA/c-self.txt"
{ [ "$CS" != 0 ] && grep -q 'AssertionError' "$QA/c-self.txt"; }
ok $? "同一個 knob 讓 --self-check 紅在 AssertionError"

fresh
python "$ROOT/scripts/qa/97-mutate.py" "$QA/case" number_scalars_not_normalized > /dev/null
python "$QA/case/$BATCH" --self-check > "$QA/c-self2.txt" 2>&1
CS2=$?
tail -3 "$QA/c-self2.txt"
[ "$CS2" != 0 ]
ok $? "對照組 number_scalars_not_normalized 也轉紅"

echo "---- C4  AC4:整張 mutation 表重跑一遍(不碰 repo 本體,全在暫存副本)"
echo "        跑的是 HEAD 的乾淨副本 —— 工作區裡別條 lane 的半成品不算在內"
python "$PRISTINE/scripts/qa/97-mutate.py" --run > "$QA/mutrun.txt" 2>&1
MR=$?
grep -E '^(咬住|沒咬住) +(spec_not_normalized|number_scalars_not_normalized)' "$QA/mutrun.txt"
tail -2 "$QA/mutrun.txt"
{ [ "$MR" = 0 ] && ! grep -q '^沒咬住' "$QA/mutrun.txt" \
  && grep -q '^咬住  spec_not_normalized ' "$QA/mutrun.txt"; }
ok $? "整張表每個 knob 都被 self-check 咬住,含 #130 那兩個"

echo "==================================================================="
echo "==== 情境 D  AC5:第二把尺(129-wide)母體有沒有 spec,重跑違例 0"
echo "==================================================================="

echo "---- D1  母體真的補進 \`spec\` 的型別混用 —— 四個 mode x 四種寫法 + 壞值那半"
grep -nE 'spec [0-9"]|壞 spec|N8' "$ROOT/scripts/qa/129-wide.py" | head -20
{ grep -q 'interrupted spec' "$ROOT/scripts/qa/129-wide.py" \
  && grep -q 'merged 全綠 spec' "$ROOT/scripts/qa/129-wide.py" \
  && grep -q 'merged 有人還在修 spec' "$ROOT/scripts/qa/129-wide.py" \
  && grep -q 'summary spec' "$ROOT/scripts/qa/129-wide.py" \
  && grep -q '壞 spec' "$ROOT/scripts/qa/129-wide.py" \
  && grep -q 'N8' "$ROOT/scripts/qa/129-wide.py"; }
ok $? "四個印 spec 的 mode 都在母體裡,壞值那半也在,而且多了 N8 這條判準"

echo "---- D2  129-wide 全跑(1900+ 批)—— 違例 0"
python "$ROOT/scripts/qa/129-wide.py" > "$QA/wide.txt" 2>&1
WD=$?
grep -E '^跑了|^==== 沒有違例|^==== 違例' "$QA/wide.txt"
{ [ "$WD" = 0 ] && grep -q '^==== 沒有違例 ====' "$QA/wide.txt"; }
ok $? "第二把尺重跑違例 0"

echo "---- D3  這把尺是活的:對著漏收 \`spec\` 的副本跑,N8 要紅"
fresh
python "$ROOT/scripts/qa/97-mutate.py" "$QA/case" spec_not_normalized > /dev/null
python "$QA/case/scripts/qa/129-wide.py" --quick > "$QA/wide-mut.txt" 2>&1
WM=$?
grep -E '^跑了|^==== 違例' "$QA/wide-mut.txt"
grep -m3 'N8 照抄貼的指令參數' "$QA/wide-mut.txt"
{ [ "$WM" != 0 ] && grep -q 'N8 照抄貼的指令參數是 `# 108 `' "$QA/wide-mut.txt"; }
ok $? "漏收 spec 的版本被 N8 抓出「\`# 108 \` 貼進終端機不會跑到那張票」"

echo "==================================================================="
echo "==== 情境 F  覆蓋驗收項那條原句 —— 端到端走一遍"
echo "====   「切票的時候,每張票都標了「快」或「慢」加一句理由,整批一次列給"
echo "====     我看,我可以當場改任何一張。」"
echo "====   走的是 classify 這條路(切完票列給 client 看的那份清單);票號那"
echo "====   幾格刻意混型別 —— #130 收的就是同一個入口,順便驗它沒把這條弄壞"
echo "==================================================================="

# 一批四張票,四種分級來源各一張,票號寫法**每張都不一樣**(47 / "48" / " 49 " / "50"):
#   #47 沒有覆蓋驗收項  -> 快
#   #48 有覆蓋驗收項    -> 慢
#   #49 動到判斷邏輯    -> 硬規則慢
#   #50 有覆蓋驗收項    -> 慢(F4 拿它示範「任何一張」不是只有第一張)
F_MIX='{"mode":"classify","tickets":[
  {"number":47,"coverage":[]},
  {"number":"48","coverage":["1. 登入頁"]},
  {"number":" 49 ","coverage":[],"judgement":true},
  {"number":"50","coverage":["2. 結帳"]}],
  "titles":{"47":"骨架","48":"登入頁","49":"算票","50":"結帳"}}'
# 同一批,票號全寫成裸整數 —— F5 比對「逐字相同」的母本
F_INT='{"mode":"classify","tickets":[
  {"number":47,"coverage":[]},
  {"number":48,"coverage":["1. 登入頁"]},
  {"number":49,"coverage":[],"judgement":true},
  {"number":50,"coverage":["2. 結帳"]}],
  "titles":{"47":"骨架","48":"登入頁","49":"算票","50":"結帳"}}'
# client 當場把 #47 從「快」改成「慢」(其他三張一個字都沒動)
F_OV47='{"mode":"classify","tickets":[
  {"number":47,"coverage":[],"override":"慢"},
  {"number":"48","coverage":["1. 登入頁"]},
  {"number":" 49 ","coverage":[],"judgement":true},
  {"number":"50","coverage":["2. 結帳"]}],
  "titles":{"47":"骨架","48":"登入頁","49":"算票","50":"結帳"}}'
# client 當場把 #50 從「慢」改成「快」—— 改的是名單上最後一張,不是第一張
F_OV50='{"mode":"classify","tickets":[
  {"number":47,"coverage":[]},
  {"number":"48","coverage":["1. 登入頁"]},
  {"number":" 49 ","coverage":[],"judgement":true},
  {"number":"50","coverage":["2. 結帳"],"override":"快"}],
  "titles":{"47":"骨架","48":"登入頁","49":"算票","50":"結帳"}}'
F_OV47_INT='{"mode":"classify","tickets":[
  {"number":47,"coverage":[],"override":"慢"},
  {"number":48,"coverage":["1. 登入頁"]},
  {"number":49,"coverage":[],"judgement":true},
  {"number":50,"coverage":["2. 結帳"]}],
  "titles":{"47":"骨架","48":"登入頁","49":"算票","50":"結帳"}}'
F_OV50_INT='{"mode":"classify","tickets":[
  {"number":47,"coverage":[]},
  {"number":48,"coverage":["1. 登入頁"]},
  {"number":49,"coverage":[],"judgement":true},
  {"number":50,"coverage":["2. 結帳"],"override":"快"}],
  "titles":{"47":"骨架","48":"登入頁","49":"算票","50":"結帳"}}'

# 把分級清單那幾列拆成(票號 / 分級 / 理由)三欄印出來,再照 <mode> 判。
# 不是 grep 一個恆真的 pattern:欄位是拆出來的,拆不出來就是 0 列,直接紅。
#   lanes  <檔> <期待幾張>  -> 每張都標到「快」或「慢」,一張都不漏
#   whys   <檔> <期待幾張>  -> 每張的理由都非空、不是佔位符
lane_check() {
  python - "$1" "$2" "$3" <<'PY'
import io, re, sys
path, want_n, mode = sys.argv[1], int(sys.argv[2]), sys.argv[3]
lane = re.compile(r"^  (快|慢) +#(\d+) (\S+) — (.+)$")
rows = [m for m in (lane.match(l)
        for l in io.open(path, encoding="utf-8").read().splitlines()) if m]
ok = True
for m in rows:
    grade, num, title, why = m.group(1), m.group(2), m.group(3), m.group(4)
    if mode == "lanes":
        print(f"  #{num} {title}  -> 分級「{grade}」")
    else:
        print(f"  #{num} {title}  -> 理由「{why}」({len(why)} 字)")
        # 空的、只有空白、或明顯的佔位符都不算「一句理由」
        if (not why.strip() or len(why.strip()) < 4
                or why.strip() in {"-", "—", "?", "??", "TODO", "待補", "N/A"}):
            print(f"      ^^ 這張的理由不算數"); ok = False
print("拆出來的分級列:", len(rows), "張;票號:", sorted(int(m.group(2)) for m in rows))
if len(rows) != want_n:
    print(f"  ^^ 期待 {want_n} 張,拆出來 {len(rows)} 張"); ok = False
if mode == "lanes" and {m.group(1) for m in rows} - {"快", "慢"}:
    print("  ^^ 有票沒標到「快」或「慢」"); ok = False
sys.exit(0 if ok else 1)
PY
}

echo "---- F1  「整批一次列給我看」—— 一份輸出把四張票全列完,不是分批印"
runp "$F_MIX"
echo "     分級列 $(grep -cE '^  (快|慢) +#[0-9]+ ' "$QA/out.txt") 行 / 貼票行 $(grep -cE '^  #[0-9]+  分級:' "$QA/out.txt") 行"
{ [ "$RC" = 0 ] && [ ! -s "$QA/err.txt" ] \
  && grep -q '^分級(4 張)— 標「慢」的會演給你看,標「快」的不會:$' "$QA/out.txt" \
  && [ "$(grep -cE '^  (快|慢) +#[0-9]+ ' "$QA/out.txt")" = 4 ] \
  && [ "$(grep -cE '^  #[0-9]+  分級:' "$QA/out.txt")" = 4 ] \
  && [ "$(grep -c '#47' "$QA/out.txt")" = 2 ] \
  && [ "$(grep -c '#48' "$QA/out.txt")" = 2 ] \
  && [ "$(grep -c '#49' "$QA/out.txt")" = 2 ] \
  && [ "$(grep -c '#50' "$QA/out.txt")" = 2 ]; }
ok $? "抬頭就是「4 張」,四張票在同一份輸出裡各出現一次(分級清單 + 貼票段)"

echo "---- F2  「每張票都標了『快』或『慢』」—— 欄位拆出來量,一張都不漏"
lane_check "$QA/out.txt" 4 lanes
ok $? "四張票各自拆得出分級,而且都落在「快」或「慢」"

echo "---- F3  「加一句理由」—— 每張的理由都非空、不是佔位符"
lane_check "$QA/out.txt" 4 whys
ok $? "四張票各有一句講得出來的理由(四種分級**來源**各一張,理由字串有三種 —— #48 與 #50 同樣是「覆蓋 1 條驗收項」)"

echo "---- F4  「我可以當場改任何一張」—— 改哪一張、那張才變,其他張一個字不動"
# ov_probe <改過的 payload> <改的是哪張> <改完應該長什麼樣> [<batch.py 路徑>]
#   只量、不判 —— F6 那格要拿**同一把尺**去量改壞的副本,所以判定跟量測分開。
ov_probe() {
  OVBIN="${4:-$ROOT/$BATCH}"
  printf '%s' "$F_MIX" | python "$OVBIN" 2>/dev/null | tr -d '\r' > "$QA/f-base.txt"
  printf '%s' "$1" | python "$OVBIN" > "$QA/f-ov.raw" 2> "$QA/f-ov.err"; OVRC=$?
  tr -d '\r' < "$QA/f-ov.raw" > "$QA/f-ov.txt"
  echo "--- 改之前 client 螢幕上那張的兩行:"; grep -- "$2" "$QA/f-base.txt"
  echo "--- 改之後 client 螢幕(整份):"; cat "$QA/f-ov.txt"
  echo "--- 其他張有沒有被動到(把 $2 那兩行拿掉之後 diff):"
  grep -v -- "$2" "$QA/f-base.txt" > "$QA/f-rest-a.txt"
  grep -v -- "$2" "$QA/f-ov.txt"   > "$QA/f-rest-b.txt"
  diff "$QA/f-rest-a.txt" "$QA/f-rest-b.txt" && echo "     (沒有差異)"
  { [ "$OVRC" = 0 ] && [ ! -s "$QA/f-ov.err" ] \
    && grep -qF "$3" "$QA/f-ov.txt" \
    && cmp -s "$QA/f-rest-a.txt" "$QA/f-rest-b.txt" \
    && ! cmp -s "$QA/f-base.txt" "$QA/f-ov.txt"; }
}
# ov <改過的 payload> <改的是哪張> <改完應該長什麼樣> <說明>
ov() { ov_probe "$1" "$2" "$3"; ok $? "$4"; }
echo "     F4a:把名單上**第一張** #47 從「快」改成「慢」"
ov "$F_OV47" '#47' '  慢  #47 骨架 — 你當場改成「慢」' \
  "#47 真的變成「慢」而且理由改口說是 client 當場改的,#48/#49/#50 三張逐字不變"
echo "     F4b:把名單上**最後一張** #50 從「慢」改成「快」——「任何一張」不是只有第一張"
ov "$F_OV50" '#50' '  快  #50 結帳 — 你當場改成「快」' \
  "#50 真的變成「快」,#47/#48/#49 三張逐字不變"

echo "---- F5  跟 #130 的接點:票號混型別的那批,跟全裸整數那批**逐字相同**"
echo "        (證明 #130 把 spec/number 收在入口,沒有把這條 demo path 弄壞)"
same_path "$F_MIX" "$F_INT"; F5A=$?
same_path "$F_OV47" "$F_OV47_INT"; F5B=$?
same_path "$F_OV50" "$F_OV50_INT"; F5C=$?
[ "$F5A" = 0 ] && [ "$F5B" = 0 ] && [ "$F5C" = 0 ]
ok $? "沒改的那批與 client 當場改過的兩批,混型別版與裸整數版 stdout / stderr / exit 全部逐字相同"

echo "---- F6  反證格:F1–F4 那幾把尺各演一次紅的"
echo "        (這 repo 的慣例 —— 尺沒紅過就不知道它在不在量東西。手法照 C3:"
echo '         `git archive HEAD` 出乾淨副本再改壞,工作區一個字都不碰)'

# mutate <檔> <改壞前> <改壞後> —— 找不到那一段就當場失敗,不會靜靜沒套上
mutate() {
  python - "$1" "$2" "$3" <<'PY'
import io, sys
p, old, new = sys.argv[1], sys.argv[2], sys.argv[3]
s = io.open(p, encoding="utf-8").read()
if old not in s:
    print("  找不到要改壞的那一段,knob 沒套上:", old)
    sys.exit(1)
io.open(p, "w", encoding="utf-8", newline="").write(s.replace(old, new, 1))
print("  改壞了:", old.strip())
print("      ->  ", new.strip())
PY
}

# f_rulers <batch.py 路徑> —— 拿 F1..F4 那**同一批**尺去量一份 batch.py,
# 結果放進 R1 / R2 / R3 / R4A / R4B(0=綠、非 0=紅)。F1..F4 量的是出貨版,
# F6 量的是改壞的副本 —— 同一把尺,只有受測物不一樣。
f_rulers() {
  runp "$F_MIX" "$1"
  R1=1
  { [ "$RC" = 0 ] \
    && [ "$(grep -cE '^  (快|慢) +#[0-9]+ ' "$QA/out.txt")" = 4 ] \
    && [ "$(grep -cE '^  #[0-9]+  分級:' "$QA/out.txt")" = 4 ]; } && R1=0
  echo "--- F2 那把尺(每張都標到快/慢):"
  lane_check "$QA/out.txt" 4 lanes; R2=$?
  echo "--- F3 那把尺(每張都有一句理由):"
  lane_check "$QA/out.txt" 4 whys; R3=$?
  echo "--- F4a 那把尺(當場改 #47 快->慢):"
  ov_probe "$F_OV47" '#47' '  慢  #47 骨架 — 你當場改成「慢」' "$1"; R4A=$?
  echo "--- F4b 那把尺(當場改 #50 慢->快):"
  ov_probe "$F_OV50" '#50' '  快  #50 結帳 — 你當場改成「快」' "$1"; R4B=$?
  echo "     這份 batch.py 量出來(0=綠 / 非 0=紅):F1=$R1  F2=$R2  F3=$R3  F4a=$R4A  F4b=$R4B"
}

echo "     F6a:把**分級那一欄**從清單列上拿掉 —— client 看不到誰快誰慢"
fresh
mutate "$QA/case/$BATCH" \
  'f"  {_grade_cell(grade, width)}  {_titled(n, titles)} — {reason}"' \
  'f"      {_titled(n, titles)} — {reason}"'
ok $? "副本上套用「分級欄拿掉」"
f_rulers "$QA/case/$BATCH"
{ [ "$R2" != 0 ] && [ "$R1" != 0 ]; }
ok $? "F2 轉紅(拆不出分級欄)、F1 也跟著紅(清單列量不到 4 行)—— 分級欄真的有人在量"

echo "     F6b:分級欄留著,把**理由**換成佔位符 TODO —— 這是 F3 專屬的紅"
fresh
mutate "$QA/case/$BATCH" \
  'f"  {_grade_cell(grade, width)}  {_titled(n, titles)} — {reason}"' \
  'f"  {_grade_cell(grade, width)}  {_titled(n, titles)} — TODO"'
ok $? "副本上套用「理由變佔位符」"
f_rulers "$QA/case/$BATCH"
{ [ "$R3" != 0 ] && [ "$R2" = 0 ] && [ "$R1" = 0 ]; }
ok $? "只有 F3 轉紅,F1 / F2 照樣綠 —— 理由那一欄是被單獨量的,不是靠行數蒙到的"

echo "     F6c:讓 client 的 override **靜靜失效**(改了跟沒改一模一樣)"
echo "          —— 這正是 batch.py 註解裡點名最怕的畫面:改成功跟被忽略長得一樣"
fresh
mutate "$QA/case/$BATCH" \
  '    if override is not None:' \
  '    if override is not None and False:'
ok $? "副本上套用「override 靜靜失效」"
f_rulers "$QA/case/$BATCH"
{ [ "$R4A" != 0 ] && [ "$R4B" != 0 ] \
  && [ "$R1" = 0 ] && [ "$R2" = 0 ] && [ "$R3" = 0 ]; }
ok $? "F4a 與 F4b 兩個方向都轉紅,F1/F2/F3 不受影響 —— 「當場改得動」是真的有人在量"

echo "     F6d:三種壞法收完之後,出貨版自己再量一次 —— 四把尺全綠"
f_rulers "$ROOT/$BATCH"
{ [ "$R1" = 0 ] && [ "$R2" = 0 ] && [ "$R3" = 0 ] && [ "$R4A" = 0 ] && [ "$R4B" = 0 ]; }
ok $? "同一批尺量出貨版全綠 —— 上面三格的紅是改壞造成的,不是尺壞了"

echo "==================================================================="
echo "==== 情境 E  收尾"
echo "==================================================================="

echo "---- E1  工作區沒被弄髒(所有改壞都跑在拋棄式副本上)"
git -C "$ROOT" status --porcelain -- skills scripts | grep -v '^?? '
[ -z "$(git -C "$ROOT" status --porcelain -- skills scripts | grep -v '^?? ')" ]
ok $? "skills / scripts 底下被追蹤的檔一個都沒被動到"

set +x
echo
if [ "$FAILED" = 0 ]; then echo "全部格子符合預期"; else
  echo "有格子不合預期 —— 見上面的 RESULT FAIL"; fi
exit $FAILED
