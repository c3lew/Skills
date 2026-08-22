#!/usr/bin/env bash
# #108 QA walkthrough —— 分級判準:切票時標快/慢,整批給 client 點頭。
# 範圍 = 票上「覆蓋驗收項」的原句,只有兩條:
#   AC1 切票的時候,每張票都標了「快」或「慢」加一句理由,整批一次列給我看,
#       我可以當場改任何一張。
#   AC4 動到判斷邏輯、篩選條件、或資料寫入的票,即使沒有可看的行為,
#       也一定被標成「慢」。
#
# 這片的交付物是散文(skills/slice-tickets/SKILL.md)+ 可執行判準
# (skills/build-batch/batch.py 的 classify)+ 守門(scripts/validate.py 的
# grade_line_issues),沒有 web UI,所以走查的形狀 = 照著出貨的 SKILL.md
# 當下一個 agent 實際操作一遍,每步留指令 + 真實輸出 + 引用到的散文行號。
#
# 用法:bash scripts/qa/108-walkthrough.sh "$(mktemp -d)/qa108"
# 改壞散文的格子一律跑在拋棄式副本上,repo 本體只讀。exit 非 0 = 有格子不合預期。
PS4='+ '
set +e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
QA="${1:?usage: 108-walkthrough.sh <workdir>}"
rm -rf "$QA"; mkdir -p "$QA"
PRISTINE="$QA/pristine"
mkdir -p "$PRISTINE"
cp -r "$ROOT"/* "$PRISTINE/"   # .git 是隱藏檔,* 不會帶進來

FAILED=0
SLICE="skills/slice-tickets/SKILL.md"
BATCH="skills/build-batch/batch.py"

fresh() { rm -rf "$QA/case"; cp -r "$PRISTINE" "$QA/case"; }

# classify:把一份 JSON 餵進出貨的 batch.py,輸出與 exit code 都留在 transcript
classify() {
  printf '%s' "$1" | python "$ROOT/$BATCH" > "$QA/out.txt" 2>&1
  CL_EXIT=$?
  cat "$QA/out.txt"
  echo "exit $CL_EXIT"
}

# gate:在副本上跑兩支守門(validate.py 全域 lint + batch.py 的 self-check)
gate() {
  python "$QA/case/scripts/validate.py" > "$QA/g-validate.txt" 2>&1
  G_VALIDATE=$?
  python "$QA/case/$BATCH" --self-check > "$QA/g-batch.txt" 2>&1
  G_BATCH=$?
  echo "--- scripts/validate.py"; tail -3 "$QA/g-validate.txt"; echo "exit $G_VALIDATE"
  echo "--- $BATCH --self-check"; tail -3 "$QA/g-batch.txt"; echo "exit $G_BATCH"
  if [ "$G_VALIDATE" -ne 0 ] || [ "$G_BATCH" -ne 0 ]; then GATE_RED=1; else GATE_RED=0; fi
}

# expect_gate <red|green> <說明>
expect_gate() {
  local want="$1" what="$2"
  if [ "$want" = red ] && [ "$GATE_RED" = 1 ]; then
    echo "RESULT PASS ($what):預期守門紅、實際紅(validate=$G_VALIDATE batch=$G_BATCH)"
  elif [ "$want" = green ] && [ "$GATE_RED" = 0 ]; then
    echo "RESULT PASS ($what):預期守門綠、實際綠"
  else
    echo "RESULT FAIL ($what):預期 $want,實際 validate=$G_VALIDATE batch=$G_BATCH"
    FAILED=1
  fi
}

# ok <上一個指令的 exit code> <說明>
ok() {
  if [ "$1" = 0 ]; then echo "RESULT PASS ($2)"; else echo "RESULT FAIL ($2)"; FAILED=1; fi
}

set -x

echo "==================================================================="
echo "==== AC1  每張票都標了快或慢加一句理由,整批一次列給我看,我可以當場改任何一張"
echo "==================================================================="

echo "---- 1a  出貨的 skills/slice-tickets/SKILL.md §4 原文(下一個 agent 照著做的那份)"
# 用 §4 的標題當範圍,不是寫死行號 —— 兩張票都在動 §4,行號 pin 每次都要跟著改
awk '/^## 4\. /,/^## 5\. /' "$ROOT/$SLICE" | head -n -2 | cat -n

echo "---- 1b  照抄 §4 那個指令跑一次 —— placeholder 換成安裝根目錄,其餘一個字不改"
sed -n '35,41p' "$ROOT/$SLICE" | sed 's#<build-batch skill dir>#skills/build-batch#' > "$QA/verbatim.sh"
cat "$QA/verbatim.sh"
( cd "$ROOT" && bash "$QA/verbatim.sh" ) > "$QA/verbatim.out" 2>&1
VERB_EXIT=$?
cat "$QA/verbatim.out"
echo "exit $VERB_EXIT"
[ "$VERB_EXIT" = 0 ]; ok $? "文件照抄跑得起來"

echo "---- 1c  每張都有分級 + 一句理由(不是只有快/慢)"
grep -nE '^  (快|慢)  #[0-9]+' "$QA/verbatim.out"
GRADED="$(grep -cE '^  (快|慢)  #[0-9]+.* — .+$' "$QA/verbatim.out")"
TICKETS="$(grep -cE '^  #[0-9]+  分級:' "$QA/verbatim.out")"
echo "有分級且有理由的行數: $GRADED / 票數: $TICKETS"
[ "$GRADED" = 3 ] && [ "$TICKETS" = 3 ]; ok $? "3 張票 3 行分級,每行都帶一句理由"

echo "---- 1d 「整批一次列給我看」:一次呼叫、一份清單、張數自己數出來"
grep -nE '^分級\([0-9]+ 張\)' "$QA/verbatim.out"
HEAD_N="$(grep -cE '^分級\([0-9]+ 張\)' "$QA/verbatim.out")"
[ "$HEAD_N" = 1 ] && grep -q '^分級(3 張)' "$QA/verbatim.out"; ok $? "一份清單、標題自己報 3 張"

echo "---- 1e  client 當場改任何一張:#47 由「慢」改成「快」,override 餵進去重跑"
echo "     改之前(同一批,沒有 override):"
classify '{"mode":"classify","tickets":[{"number":47,"coverage":["1. 切票的時候…"],"judgement":false},{"number":48,"coverage":[],"judgement":false}],"titles":{"47":"分級","48":"骨架"}}'
grep '#47' "$QA/out.txt" > "$QA/before-47.txt"; cat "$QA/before-47.txt"
echo "     client 說:#47 改成快 —— 把 override 填進去重跑"
classify '{"mode":"classify","tickets":[{"number":47,"coverage":["1. 切票的時候…"],"judgement":false,"override":"快"},{"number":48,"coverage":[],"judgement":false}],"titles":{"47":"分級","48":"骨架"}}'
grep '#47' "$QA/out.txt" > "$QA/after-47.txt"; cat "$QA/after-47.txt"
grep -q '^  #47  分級:慢 — 覆蓋 1 條驗收項$' "$QA/before-47.txt" && grep -q '^  #47  分級:快 — 你當場改成「快」$' "$QA/after-47.txt"
ok $? "改後的那一行才是要寫進票的那個,理由也講明是 client 改的"
echo "     另一個方向:#48 由「快」改成「慢」"
classify '{"mode":"classify","tickets":[{"number":48,"coverage":[],"judgement":false,"override":"慢"}],"titles":{"48":"骨架"}}'
grep -q '^  #48  分級:慢 — 你當場改成「慢」$' "$QA/out.txt"; ok $? "反方向也改得動"

echo "---- 1f 「改了但沒生效」不會靜靜發生:認不得的 override 當場停"
for BAD in fast 快車道 Fast '快 ' ''; do
  echo "     override=[$BAD]"
  classify "$(printf '{"mode":"classify","tickets":[{"number":48,"coverage":[],"override":"%s"}]}' "$BAD")"
  { [ "$CL_EXIT" != 0 ] && grep -q '你填的分級只能是「快」或「慢」' "$QA/out.txt" \
    && ! grep -q 'override' "$QA/out.txt" && ! grep -q '分級:' "$QA/out.txt"; }
  ok $? "override=[$BAD] 當場停、沒有印出貼票的那一行"
done

echo "---- 1g  分級行格式三邊 byte 對齊:SKILL.md 示範 / batch.py 印的 / validate.py 咬的"
python - "$ROOT" <<'PY'
import pathlib, sys, importlib.util
sys.stdout.reconfigure(encoding="utf-8")
root = pathlib.Path(sys.argv[1])
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m
batch = load("batch108", root / "skills/build-batch/batch.py")
val = load("validate108", root / "scripts/validate.py")
printed = batch.format_grade_line(batch.GRADE_SLOW, "覆蓋 2 條驗收項")
doc = (root / "skills/slice-tickets/SKILL.md").read_text(encoding="utf-8")
line_no = [i for i, l in enumerate(doc.splitlines(), 1) if l == printed]
print("batch.py 印的       :", repr(printed))
print("bytes               :", printed.encode("utf-8").hex(" "))
print("SKILL.md 示範的行號  :", line_no)
print("validate 掃到的分級行 :", val.GRADE_LINE_RE.findall(doc))
print("validate 判格式 OK   :", bool(val.GRADE_LINE_OK_RE.match(printed)))
print("validate 對出貨檔的抱怨:", val.grade_line_issues(doc))
assert line_no, "SKILL.md 沒有一行跟 batch.py 印出來的 byte 相同"
assert val.GRADE_LINE_OK_RE.match(printed), printed
assert val.grade_line_issues(doc) == []
for grade in (batch.GRADE_FAST, batch.GRADE_SLOW):
    line = batch.format_grade_line(grade, "沒有覆蓋驗收項")
    assert val.GRADE_LINE_OK_RE.match(line), line
print("三邊對齊 OK")
PY
ok $? "SKILL.md 示範 = batch.py 印出來 = validate.py 咬的,byte 對齊"

echo "==================================================================="
echo "==== AC4  動到判斷邏輯/篩選條件/資料寫入的票,即使沒有可看的行為也一定被標成「慢」"
echo "==================================================================="

echo "---- 4a  judgement=true 而 coverage=[](沒有可看的行為)→ 慢"
classify '{"mode":"classify","tickets":[{"number":49,"coverage":[],"judgement":true}],"titles":{"49":"算票"}}'
{ [ "$CL_EXIT" = 0 ] && grep -q '^  #49  分級:慢 — 動到判斷邏輯或資料寫入,硬規則一律慢$' "$QA/out.txt"; }
ok $? "沒有可看的行為也照樣慢"

echo "---- 4b  硬規則蓋過 client 的 override:client 想改成快 → 當場停"
classify '{"mode":"classify","tickets":[{"number":49,"coverage":[],"judgement":true,"override":"快"}],"titles":{"49":"算票"}}'
{ [ "$CL_EXIT" != 0 ] && grep -q '硬規則一律慢 —— 改不成快' "$QA/out.txt" && ! grep -q '分級:' "$QA/out.txt"; }
ok $? "當場停、沒有靜靜忽略、沒有印出貼票的那一行"
echo "     改成「慢」是同一個結果,不用停"
classify '{"mode":"classify","tickets":[{"number":49,"coverage":[],"judgement":true,"override":"慢"}],"titles":{"49":"算票"}}'
{ [ "$CL_EXIT" = 0 ] && grep -q '^  #49  分級:慢' "$QA/out.txt"; }
ok $? "同向的 override 不擋"

echo "---- 4c  硬規則票遇到認不得的 override 一樣當場停(那條路的結果剛好也是慢)"
for BAD in fast ''; do
  classify "$(printf '{"mode":"classify","tickets":[{"number":49,"coverage":[],"judgement":true,"override":"%s"}]}' "$BAD")"
  { [ "$CL_EXIT" != 0 ] && grep -q '你填的分級只能是「快」或「慢」' "$QA/out.txt" \
    && ! grep -q 'override' "$QA/out.txt"; }
  ok $? "judgement=true + override=[$BAD] 也停在 override 那關"
done

echo "---- 4d  拿「沒有任何路徑會靜靜落到快」當尺,掃過 classify_one 的所有分支"
python - "$ROOT/$BATCH" <<'PY'
import sys, itertools, importlib.util, pathlib
sys.stdout.reconfigure(encoding="utf-8")
spec = importlib.util.spec_from_file_location("batch_sweep", pathlib.Path(sys.argv[1]))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
covs = {
    "[]": [], "['1. 登入頁']": ["1. 登入頁"], "['1. a','2. b']": ["1. a", "2. b"],
    "['無 — 由後續票…']": ["無 — 由後續票的驗收項間接驗證"],
    "['無 - 由後續票…']": ["無 - 由後續票的驗收項間接驗證"],
    "['無障礙:鍵盤走得完']": ["無障礙:鍵盤走得完整個表單"],
    "['']": [""], "''": "", "'1. 登入頁'": "1. 登入頁",
}
judges = {"False": False, "True": True, "0": 0, "1": 1, "None": None,
          "'false'": "false", "''": ""}
ovrs = {"None": None, "'快'": "快", "'慢'": "慢", "'fast'": "fast", "''": "",
        "'快 '": "快 ", "'快車道'": "快車道", "'Fast'": "Fast"}


def sanctioned(items, j, o):
    """散文授權落到「快」的路只有兩條:client 當場改成快、以及沒有覆蓋驗收項。"""
    if j:
        return False            # 硬規則票永遠不准是快(AC4 原句)
    return o == "快" or (o is None and not items)


bad, rows, tally = [], 0, {"快": 0, "慢": 0, "停": 0}
for (cn, cv), (jn, jv), (on, ov) in itertools.product(
        covs.items(), judges.items(), ovrs.items()):
    rows += 1
    grade = None
    try:
        grade, reason = m.classify_one(cv, jv, ov)
        tally[grade] += 1
    except m.OverrideRejected:
        # #118 之後單張這一層拒絕不再是 SystemExit —— 整批算完才由 main 停,
        # 但「這條路不會落到快」是同一句話,掃法照舊
        tally["停"] += 1
        reason = "(當場停)"
    items = [c for c in cv if not m.NO_COVERAGE_RE.match(str(c).strip())]
    if grade == m.GRADE_FAST and not sanctioned(items, jv, ov):
        bad.append((cn, jn, on, reason))
    print(f"  coverage={cn:<24} judgement={jn:<8} override={on:<9} -> {grade or '停'}")
print(f"\n掃過 {rows} 條路:快 {tally['快']} / 慢 {tally['慢']} / 當場停 {tally['停']}")
print(f"靜靜落到「快」而散文沒授權的:{len(bad)}")
for b in bad:
    print("  UNSAFE", b)
sys.exit(1 if bad else 0)
PY
ok $? "classify_one 全分支掃過,沒有一條靜靜落到「快」"

echo "---- 4e  已知洞(不影響 AC 判定,固定住現況當回歸見證):JSON key 打錯是靜的"
echo "     judgement 打成 judgment(少一個 e),coverage=[] → 靜靜落到「快」"
classify '{"mode":"classify","tickets":[{"number":49,"coverage":[],"judgment":true}],"titles":{"49":"算票"}}'
{ [ "$CL_EXIT" = 0 ] && grep -q '^  #49  分級:快' "$QA/out.txt"; }
if [ $? = 0 ]; then
  echo "RESULT KNOWN (judgement key 打錯):現況 = exit 0 且判快 —— 值打錯會停,key 打錯不會"
else
  echo "RESULT CHANGED (judgement key 打錯):行為跟本輪記錄的不一樣,重讀 4e"
  FAILED=1
fi
echo "     override 打成 overide → client 改的那個字靜靜消失,畫面跟「沒改」一模一樣"
classify '{"mode":"classify","tickets":[{"number":48,"coverage":[],"overide":"慢"}],"titles":{"48":"骨架"}}'
{ [ "$CL_EXIT" = 0 ] && grep -q '^  #48  分級:快' "$QA/out.txt"; }
if [ $? = 0 ]; then
  echo "RESULT KNOWN (override key 打錯):現況 = exit 0 且判快"
else
  echo "RESULT CHANGED (override key 打錯):行為跟本輪記錄的不一樣,重讀 4e"
  FAILED=1
fi
echo "     對照組:整個 mode 漏掉會不會靜靜變成別的 mode"
classify '{"tickets":[{"number":47,"coverage":["1. a"]}]}'
[ "$CL_EXIT" != 0 ]; ok $? "mode 漏掉當場炸,不會靜靜印出別的東西"

echo "==================================================================="
echo "==== SKILL.md 那半:下一個 agent 照著讀,做不做得對(§4 三段 + 守門)"
echo "==================================================================="

echo "---- 5a  三段都在,附行號"
grep -n -e 'skill 目錄底下的 `batch.py`' -e "<build-batch skill dir>/batch.py" -e '不在 → 這批整批判慢車道' -e '判錯必然會發生' "$ROOT/$SLICE"
echo "---- 5b  點頭那兩句(否決權怎麼兌現)+ #120 補的兩句也在"
grep -n -e '這批的快慢分級,有要改的嗎?' -e '照你說的改,改完的才是寫進票裡的那個' -e '不要自己去改 `judgement` 旗標讓它過' -e '接得住的是..有驗收項..的那半' "$ROOT/$SLICE"

echo "---- 5c  對真檔改壞、跑守門、還原 —— 全部在副本上做"
echo "     5c-0  原封不動 → 該綠"
fresh; gate; expect_gate green "pristine"

echo "     5c-1  拿掉「batch.py 不在 → 整批判慢」的退路 → 該紅"
fresh
python - "$QA/case/$SLICE" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
old = "`batch.py` 不在 → 這批整批判慢車道,不要自己重寫一份判斷。保守方向不會漏掉 demo,兩份各說各話會。"
assert old in t
p.write_text(t.replace(old, "", 1), encoding="utf-8")
PY
gate; expect_gate red "退路那句不見"
grep -m1 '退路' "$QA/g-batch.txt"

echo "     5c-2  拿掉判準天花板(judgement 判錯必然會發生)→ 該紅"
fresh
python - "$QA/case/$SLICE" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
assert "判錯必然會發生" in t
p.write_text(t.replace("判錯必然會發生", "判得很準", 1), encoding="utf-8")
PY
gate; expect_gate red "天花板那句不見"
grep -m1 '天花板' "$QA/g-batch.txt"

echo "     5c-3  拿掉「有要改的嗎?」那一問(否決權)→ 該紅"
fresh
python - "$QA/case/$SLICE" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
assert "這批的快慢分級,有要改的嗎?" in t
p.write_text(t.replace("這批的快慢分級,有要改的嗎?", "這批分級如下。", 1), encoding="utf-8")
PY
gate; expect_gate red "點頭那一問不見"
grep -m1 '否決權' "$QA/g-batch.txt"

echo "     5c-4  拿掉「改完的才是寫進票裡的那個」→ 該紅"
fresh
python - "$QA/case/$SLICE" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
old = "照你說的改,改完的才是寫進票裡的那個"
assert old in t
p.write_text(t.replace(old, "照你說的改", 1), encoding="utf-8")
PY
gate; expect_gate red "以 client 改的為準那句不見"

echo "     5c-4b 拿掉硬規則被 client 頂著時的處置(#120)→ 該紅"
fresh
python - "$QA/case/$SLICE" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
old = "不要自己去改 `judgement` 旗標讓它過"
assert old in t
p.write_text(t.replace(old, "不要亂改", 1), encoding="utf-8")
PY
gate; expect_gate red "硬規則遇到 client 想改快的處置不見"
grep -q '硬規則被 client 頂著' "$QA/g-batch.txt"; ok $? "紅在對的地方(batch 的散文 pin,不是別條順便)"

echo "     5c-4c 天花板退回「降級回路全部關住」的過度宣稱(#120)→ 該紅"
fresh
python - "$QA/case/$SLICE" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
old = "接得住的是**有驗收項**的那半"
assert old in t
p.write_text(t.replace(old, "把判錯的代價整個關住", 1), encoding="utf-8")
PY
gate; expect_gate red "降級回路只接得住一半那句不見"
grep -q '只接得住一半' "$QA/g-batch.txt"; ok $? "紅在對的地方(天花板那條 pin)"

echo "     5c-5  分級行示範改壞(全形冒號那一族:改成「中」)→ 該紅"
fresh
python - "$QA/case/$SLICE" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
assert "分級:慢 — 覆蓋 2 條驗收項" in t
p.write_text(t.replace("分級:慢 — 覆蓋 2 條驗收項", "分級:中 — 覆蓋 2 條驗收項", 1), encoding="utf-8")
PY
gate; expect_gate red "分級行示範寫歪"
grep -m1 '分級行格式不對' "$QA/g-validate.txt"

echo "     5c-6  分級行示範整行拿掉(呼叫了 classify 卻沒示範)→ 該紅"
fresh
python - "$QA/case/$SLICE" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
p.write_text(t.replace("分級:慢 — 覆蓋 2 條驗收項\n", "", 1), encoding="utf-8")
PY
gate; expect_gate red "呼叫 classify 卻沒示範分級行"
grep -m1 '發明' "$QA/g-validate.txt"

echo "     5c-7  指令那段不再把 JSON 餵進 batch.py → 該紅(#58 的形狀)"
fresh
python - "$QA/case/$SLICE" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
assert '"mode": "classify"' in t
p.write_text(t.replace('"mode": "classify"', '"mode": "nope"', 1), encoding="utf-8")
PY
gate; expect_gate red "分級清單走不進 batch.py"

echo "     5c-8  安裝根目錄寫法改壞:<build-batch skill dir>/ → 裸 batch.py"
echo "            (slice-tickets 自己裝起來的時候身邊沒有 batch.py,這行照抄跑不動)"
fresh
python - "$QA/case/$SLICE" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
old = "python <build-batch skill dir>/batch.py <<'JSON'"
assert old in t
p.write_text(t.replace(old, "python batch.py <<'JSON'", 1), encoding="utf-8")
PY
grep -n "python batch.py" "$QA/case/$SLICE"
gate
if [ "$GATE_RED" = 1 ]; then
  echo "RESULT PASS (安裝根目錄寫法被守著):預期紅、實際紅"
else
  echo "RESULT KNOWN (安裝根目錄寫法沒被守著):兩支守門都綠 —— 這行漂掉沒有任何東西會當場紅"
fi

echo "     5c-9  同型全掃:repo 裡所有 <… skill dir>/ 的寫法,有沒有任何一條被守著"
grep -rno "<[^>]*skill dir>/[a-z_.]*" "$ROOT/skills" --include=*.md | sed "s/^.*skills\///" | sort | uniq -c | sort -rn
echo "     守門那兩支檔裡有沒有任何一條規則提到 skill dir 的路徑寫法:"
grep -c "skill dir" "$ROOT/scripts/validate.py" "$ROOT/$BATCH"

echo "---- 5d  改壞的都只在副本上,repo 本體乾淨"
git -C "$ROOT" status --porcelain -- skills scripts/validate.py
[ -z "$(git -C "$ROOT" status --porcelain -- skills scripts/validate.py)" ]
ok $? "skills/ 與 scripts/validate.py 一個字都沒動"

set +x
echo
echo "==== walkthrough 走完 ===="
if [ "$FAILED" -ne 0 ]; then
  echo "有格子不合預期 —— 見上面的 RESULT FAIL"
  exit 1
fi
echo "所有格子符合預期(RESULT KNOWN 是本輪記錄下來的已知洞,不算不合預期)"
