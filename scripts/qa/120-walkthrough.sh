#!/usr/bin/env bash
# #120 QA walkthrough —— BUG(#108):硬規則的處置只活在 code 裡,天花板是過度宣稱。
# 覆蓋驗收項(原句,只有一條):
#   4. 動到判斷邏輯、篩選條件、或資料寫入的票,即使沒有可看的行為,也一定被標成「慢」。
#
# 這片沒有 web UI —— 交付物是散文(skills/slice-tickets/SKILL.md)、可執行判準
# (skills/build-batch/batch.py 的 classify)、守門(--self-check)、以及 mutation 台
# (scripts/qa/97-mutate.py)。所以走查的形狀 = 可重跑的 transcript:每格留指令 +
# 真實輸出 + 引用到的散文行號。形狀照 108-walkthrough.sh / 107-walkthrough.sh。
#
# 用法:bash scripts/qa/120-walkthrough.sh "$(mktemp -d)/qa120"
# 「改壞它」的格子一律跑在拋棄式副本上,repo 本體只讀(最後一格對帳 git status)。
# exit 非 0 = 有格子不合預期。
PS4='+ '
set +e
export PYTHONIOENCODING=utf-8
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
QA="${1:?usage: 120-walkthrough.sh <workdir>}"
rm -rf "$QA"; mkdir -p "$QA"
PRISTINE="$QA/pristine"
mkdir -p "$PRISTINE"
cp -r "$ROOT"/* "$PRISTINE/"   # .git 是隱藏檔,* 不會帶進來

FAILED=0
SLICE="skills/slice-tickets/SKILL.md"
BATCH="skills/build-batch/batch.py"
MUTATE="scripts/qa/97-mutate.py"

fresh() { rm -rf "$QA/case"; cp -r "$PRISTINE" "$QA/case"; }

# classify:把一份 JSON 餵進出貨的 batch.py,stdout+stderr 與 exit code 都留下來
classify() {
  printf '%s' "$1" | python "$ROOT/$BATCH" > "$QA/out.txt" 2>&1
  CL_EXIT=$?
  cat "$QA/out.txt"
  echo "exit $CL_EXIT"
}

# gate:在副本上跑兩支守門(batch.py --self-check + validate.py 全域 lint)
gate() {
  python "$QA/case/$BATCH" --self-check > "$QA/g-batch.txt" 2>&1
  G_BATCH=$?
  python "$QA/case/scripts/validate.py" > "$QA/g-validate.txt" 2>&1
  G_VALIDATE=$?
  echo "--- $BATCH --self-check"; tail -3 "$QA/g-batch.txt"; echo "exit $G_BATCH"
  echo "--- scripts/validate.py"; tail -3 "$QA/g-validate.txt"; echo "exit $G_VALIDATE"
  if [ "$G_BATCH" -ne 0 ] || [ "$G_VALIDATE" -ne 0 ]; then GATE_RED=1; else GATE_RED=0; fi
}

# expect_gate <red|green> <說明>
expect_gate() {
  local want="$1" what="$2"
  if [ "$want" = red ] && [ "$GATE_RED" = 1 ]; then
    echo "RESULT PASS ($what):預期守門紅、實際紅(batch=$G_BATCH validate=$G_VALIDATE)"
  elif [ "$want" = green ] && [ "$GATE_RED" = 0 ]; then
    echo "RESULT PASS ($what):預期守門綠、實際綠"
  else
    echo "RESULT FAIL ($what):預期 $want,實際 batch=$G_BATCH validate=$G_VALIDATE"
    FAILED=1
  fi
}

# note_gate <red|green> <說明> —— 繞道方向:紅是好的,綠是誠實記錄下來的天花板
note_gate() {
  local want="$1" what="$2"
  if [ "$want" = red ] && [ "$GATE_RED" = 1 ]; then
    echo "RESULT PASS ($what):繞道也被咬住(batch=$G_BATCH validate=$G_VALIDATE)"
  else
    echo "RESULT KNOWN ($what):守門沒紅 —— 字面 pin 的天花板,誠實記錄在報告裡"
  fi
}

ok() {
  if [ "$1" = 0 ]; then echo "RESULT PASS ($2)"; else echo "RESULT FAIL ($2)"; FAILED=1; fi
}

set -x

echo "==================================================================="
echo "==== AC1  batch.py 的錯誤訊息不再指路「改 judgement 旗標」"
echo "==================================================================="

echo "---- 1a  出貨的那段原文(附行號)"
grep -n -e '硬規則一律慢 —— 改不成快' -e '要改快只有一條路' -e '把動到判斷邏輯或資料寫入的那部分切出去' -e '票的內容沒變就是慢' "$ROOT/$BATCH"

echo "---- 1b  真的跑一次:judgement=true + override=快 → 當場停,看它到底印什麼"
classify '{"mode":"classify","tickets":[{"number":49,"coverage":[],"judgement":true,"override":"快"}],"titles":{"49":"算票"}}'
echo "     ↑ 這就是 agent 被 client 頂著時唯一看得到的字"

echo "---- 1c  指路的那條繞道不在了:訊息裡沒有「旗標」、也沒有「judgement」"
{ [ "$CL_EXIT" != 0 ] \
  && ! grep -q '旗標' "$QA/out.txt" \
  && ! grep -q 'judgement' "$QA/out.txt" \
  && ! grep -q '分級:' "$QA/out.txt"; }
ok $? "當場停、訊息沒把旗標寫出來、也沒印出任何一行分級"

echo "---- 1d  真的那條路在:訊息指向「回去改票的內容」"
grep -o '回去改票的內容[^,。]*' "$QA/out.txt"
grep -q '回去改票的內容' "$QA/out.txt"; ok $? "訊息指的是改票的內容,不是改旗標"

echo "---- 1e  對照組:同向 override(改成慢)不停,照樣判慢"
classify '{"mode":"classify","tickets":[{"number":49,"coverage":[],"judgement":true,"override":"慢"}],"titles":{"49":"算票"}}'
{ [ "$CL_EXIT" = 0 ] && grep -q '^  #49  分級:慢' "$QA/out.txt"; }
ok $? "同向 override 不擋"

echo "---- 1f  守門真的咬住這段訊息:把繞道寫回去 → self-check 該紅"
fresh
python "$QA/case/$MUTATE" "$QA/case" hardrule_msg_signposts_flag
gate; expect_gate red "錯誤訊息把「要改請先改 judgement 旗標」寫回去"

echo "---- 1g  另一面:只說改不成、不說真的那條路 → 也該紅"
fresh
python "$QA/case/$MUTATE" "$QA/case" hardrule_msg_no_real_path
gate; expect_gate red "訊息拿掉「回去改票的內容」那半"

echo "==================================================================="
echo "==== AC2  SKILL.md §4 補硬規則遇到 client 想改快時的處置,並被 CLASSIFY_LINES 咬住"
echo "==================================================================="

echo "---- 2a  出貨的那三段原文(附行號)"
grep -n -e '硬規則蓋過 client 的 override' -e '當場回報他為什麼停' -e '他真的要那張快,回去改票的內容' -e '不要自己去改 `judgement` 旗標讓它過' "$ROOT/$SLICE"

echo "---- 2b  它進了 CLASSIFY_LINES(守門的母體)"
grep -n -A2 '不要自己去改 `judgement` 旗標讓它過' "$ROOT/$BATCH" | head -8

echo "---- 2c-0  pristine 對照組 → 該綠"
fresh; gate; expect_gate green "pristine"

echo "---- 2c-1  刪掉方向:把那句從 SKILL.md 拿掉 → 該紅"
fresh
python - "$QA/case/$SLICE" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
old = "`judgement` 是你讀 diff 的判斷結果,不是放行開關 —— 不要自己去改 `judgement` 旗標讓它過。"
assert old in t, "散文被改過了 —— 這格的目標不在"
p.write_text(t.replace(old, "", 1), encoding="utf-8")
PY
gate; expect_gate red "硬規則處置那句被刪掉"
grep -m1 '硬規則被 client 頂著' "$QA/g-batch.txt"

echo "---- 2c-2  刪掉方向(守門自己那面):CLASSIFY_LINES 少一項 → 該紅"
fresh
python "$QA/case/$MUTATE" "$QA/case" hardrule_pin_dropped
gate; expect_gate red "守門自己把這條 pin 刪掉"

echo "---- 2c-3  繞道方向 A:整段改寫成相反的話(「旗標改掉就好」)→ 該紅"
fresh
python - "$QA/case/$SLICE" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
old = "`judgement` 是你讀 diff 的判斷結果,不是放行開關 —— 不要自己去改 `judgement` 旗標讓它過。"
new = "client 堅持的話,`judgement` 旗標改掉就好,改成 `false` 重跑一次就過了。"
assert old in t
p.write_text(t.replace(old, new, 1), encoding="utf-8")
PY
grep -n '旗標改掉就好' "$QA/case/$SLICE"
gate; expect_gate red "整段被改寫成相反的話(pin 的字面一起消失)"

echo "---- 2c-4  繞道方向 B(比較賊):pin 的原句留著,後面再加一句反話 → 守門咬不咬"
fresh
python - "$QA/case/$SLICE" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
old = "不要自己去改 `judgement` 旗標讓它過。"
new = ("不要自己去改 `judgement` 旗標讓它過。"
       "不過 client 真的很堅持的時候,把 `judgement` 改成 `false` 重跑就好。")
assert old in t
p.write_text(t.replace(old, new, 1), encoding="utf-8")
PY
grep -n '真的很堅持' "$QA/case/$SLICE"
gate; note_gate red "pin 留著、後面加一句反話"

echo "==================================================================="
echo "==== AC3  §4 天花板那句改成講得出真話的版本(降級回路只接得住有驗收項的那半)"
echo "==================================================================="

echo "---- 3a  出貨的那句原文(附行號)"
grep -n -e '這條判準的天花板' -e '接得住的是..有驗收項..的那半' "$ROOT/$SLICE"
echo "     裡面的三件真話:回路還沒出貨 / 只接得住有驗收項那半 / coverage 空的那半 judgement 是唯一一道"
grep -c '還沒出貨' "$ROOT/$SLICE"
grep -o 'coverage` 是空的那半[^。]*。' "$ROOT/$SLICE"
echo "     batch.py 的 classify_one docstring 同步(不是只有散文改)"
grep -n -e '接得住的也只有 `coverage` 非空的那半' -e '那個回路還沒出貨' "$ROOT/$BATCH"

echo "---- 3b-1  刪掉方向:天花板那句拿掉 → 該紅"
fresh
python - "$QA/case/$SLICE" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
old = "接得住的是**有驗收項**的那半"
assert old in t
p.write_text(t.replace(old, "接得住的東西不少", 1), encoding="utf-8")
PY
gate; expect_gate red "天花板那句被刪掉"
grep -m1 '只接得住一半' "$QA/g-batch.txt"

echo "---- 3b-2  刪掉方向(守門自己那面):CLASSIFY_LINES 少這一項 → 該紅"
fresh
python "$QA/case/$MUTATE" "$QA/case" ceiling_half_pin_dropped
gate; expect_gate red "守門自己把天花板這條 pin 刪掉"

echo "---- 3b-3  繞道方向 A:退回 #108 那版絕對句「由降級回路關住」→ 該紅"
fresh
python - "$QA/case/$SLICE" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
head = "判錯的代價要靠降級回路兜"
i = t.index(head)
j = t.index("\n", i)
print("換掉的那行:", t[i:j][:60], "…")
new = ("判錯的代價由降級回路關住(標「快」的票對驗收清單有任何一條沒過就當場降級)。"
       "不要為了把它判準而加規則。")
p.write_text(t[:i] + new + t[j:], encoding="utf-8")
PY
grep -n '由降級回路關住' "$QA/case/$SLICE"
gate; expect_gate red "天花板退回「關住」的過度宣稱"

echo "---- 3b-4  繞道方向 B:pin 的原句留著,旁邊再宣稱一次「全部關住」→ 守門咬不咬"
fresh
python - "$QA/case/$SLICE" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
old = "不要為了把它判準而加規則 —— 這是宣告過的天花板,要補的是那個洞,不是這條判準。"
new = (old + "實務上判錯的代價已經由降級回路一律接得住,不用擔心。")
assert old in t
p.write_text(t.replace(old, new, 1), encoding="utf-8")
PY
grep -n '一律接得住' "$QA/case/$SLICE"
gate; note_gate red "pin 留著、旁邊再宣稱一次「一律接得住」"

echo "==================================================================="
echo "==== AC4  frontmatter(SKILL.md:3)與 body 三個 delta 對得上"
echo "==================================================================="

echo "---- 4a  frontmatter 原文(附行號)"
grep -n '^description:' "$ROOT/$SLICE"
echo "---- 4b  body 的三個 delta 標題(附行號)"
grep -n '^## [0-9]\. Delta:' "$ROOT/$SLICE"
echo "---- 4c  三個 delta 在 description 裡都找得到對應的字"
python - "$ROOT/$SLICE" <<'PY'
import sys, pathlib, re
sys.stdout.reconfigure(encoding="utf-8")
t = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
desc = re.search(r"^description: (.*)$", t, re.M).group(1)
deltas = [d.strip() for d in re.findall(r"^## \d\. Delta:(.+)$", t, re.M)]
print("description:", desc)
print("body deltas :", deltas)
# 三個 delta 各給一組「description 裡至少要出現其中一個」的字。
# 「快/慢分級」在 description 裡是寫成「判快車道還是慢車道」—— 講的是同一件事,
# 所以認同義的那一族,不是死認標題四個字。
want = {"覆蓋驗收項": ("驗收項",),
        "快/慢分級": ("分級", "快車道", "慢車道"),
        "blocking 邊對帳": ("blocking 邊",)}
assert len(deltas) == 3, deltas
assert set(deltas) == set(want), deltas
missing = [d for d in deltas if not any(w in desc for w in want[d])]
print("description 沒提到的 delta:", missing)
assert not missing, missing
print("三個 delta 全部在 description 裡對得上")
PY
ok $? "frontmatter 與 body 三個 delta 對帳"

echo "==================================================================="
echo "==== AC5  §2(SKILL.md:16)不再把發佈自己包進「先做完」"
echo "==================================================================="

echo "---- 5a  出貨那行原文(附行號)"
grep -n '先做完' "$ROOT/$SLICE"
echo "---- 5b  §6 的標題本身就是「然後發佈」"
grep -n '^## 6\.' "$ROOT/$SLICE"
echo "---- 5c  舊句子不在了,新句子在"
{ ! grep -q '先做完 §3–§6' "$ROOT/$SLICE" \
  && ! grep -q '先做完 §3-§6' "$ROOT/$SLICE" \
  && grep -q '先做完 §3–§5,再照 §6 對帳與發佈' "$ROOT/$SLICE"; }
ok $? "§2 的範圍收到 §3–§5,發佈那步交給 §6"

echo "==================================================================="
echo "==== AC6  §4(SKILL.md:52)同一句話不再講兩次"
echo "==================================================================="

echo "---- 6a  出貨那行原文(附行號)"
grep -n '這批的快慢分級,有要改的嗎?' "$ROOT/$SLICE"
echo "---- 6b  重複的前半(「要改就照他說的改」)不在了,pin 的原句留著且只有一份"
grep -c '照你說的改,改完的才是寫進票裡的那個' "$ROOT/$SLICE"
python - "$ROOT/$SLICE" <<'PY'
import sys, pathlib
sys.stdout.reconfigure(encoding="utf-8")
t = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
line = [l for l in t.splitlines() if "這批的快慢分級" in l][0]
print("那一行:", line)
assert "要改就照他說的改" not in t, "重複的前半還在"
assert t.count("照你說的改,改完的才是寫進票裡的那個") == 1, "pin 的原句不只一份"
assert "照你說的改" in line
assert line.count("照他說的改") == 0, line
print("前半改寫完成,pin 的原句原封不動留著")
PY
ok $? "同一句話不再講兩次,而 pin 的原句沒被動到"

echo "==================================================================="
echo "==== AC7  新句子進 97-mutate.py,改壞後 --self-check 轉紅"
echo "==================================================================="

echo "---- 7a  整張表跑一次"
python "$ROOT/$MUTATE" --run > "$QA/mutate1.txt" 2>&1
M1=$?
cat "$QA/mutate1.txt"
[ "$M1" = 0 ]; ok $? "整張表 exit 0 —— 每個 knob 都被 self-check 咬住"
if grep -q '沒咬住' "$QA/mutate1.txt"; then
  echo "RESULT FAIL (有 knob 沒咬住)"; FAILED=1
else
  echo "RESULT PASS (輸出裡沒有任何一格「沒咬住」)"
fi

echo "---- 7b  #120 那五個 knob 在表上,而且都咬住"
for K in hardrule_msg_signposts_flag hardrule_msg_no_real_path hardrule_pin_dropped \
         ceiling_half_pin_dropped classify_lines_never_complains; do
  grep -E "^咬住  $K " "$QA/mutate1.txt"
  grep -qE "^咬住  $K " "$QA/mutate1.txt"; ok $? "#120 knob 在表上且咬住:$K"
done

echo "---- 7c  負向對照 A:整張表跑第二次,結果逐字相同(還原乾淨,沒有殘留)"
python "$ROOT/$MUTATE" --run > "$QA/mutate2.txt" 2>&1
M2=$?
diff "$QA/mutate1.txt" "$QA/mutate2.txt" && echo "(兩次輸出完全相同)"
{ [ "$M1" = "$M2" ] && diff -q "$QA/mutate1.txt" "$QA/mutate2.txt" >/dev/null; }
ok $? "兩次跑出來的表逐字相同 —— knob 之間有還原,不是越跑越紅"

echo "---- 7d  負向對照 B:多目標還原機制自己拆開來量"
echo "        (打 batch.py 的 knob → 兩支檔一起還原 → self-check 該回綠;"
echo "         只還原 validate.py 的話會殘留,那條也一起量)"
python - "$ROOT" "$ROOT/$MUTATE" <<'PY'
import importlib.util, pathlib, shutil, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
root = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("mut120", sys.argv[2])
mut = importlib.util.module_from_spec(spec); spec.loader.exec_module(mut)

print("TARGETS  =", mut.TARGETS)
print("GATES    =", mut.GATES)
batch_knobs = sorted(k for k in mut.KNOBS if mut.target_of(k) != mut.DEFAULT_TARGET)
val_knobs = sorted(k for k in mut.KNOBS if mut.target_of(k) == mut.DEFAULT_TARGET)
print(f"打 batch.py 的 knob {len(batch_knobs)} 個:{batch_knobs}")
print(f"打 validate.py 的 knob {len(val_knobs)} 個(前 3):{val_knobs[:3]} …")
assert mut.BATCH in mut.TARGETS and mut.DEFAULT_TARGET in mut.TARGETS
assert batch_knobs, "沒有任何 knob 打在 batch.py —— #120 的多目標機制沒接上"

bad = []
with tempfile.TemporaryDirectory() as tmp:
    copy = pathlib.Path(tmp) / "repo"
    shutil.copytree(root, copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    pristine = {rel: (copy / rel).read_bytes() for rel in mut.TARGETS}

    def restore(rels):
        for rel in rels:
            (copy / rel).write_bytes(pristine[rel])

    # 對照組:什麼都沒動 -> 該綠
    assert mut.self_check(copy).returncode == 0, "控制組就紅了,儀器壞了"
    print("控制組(沒套 knob)      -> self-check exit=0 綠")

    # 逐個 knob:套 -> 該紅 -> 全還原 -> 該回綠
    for knob in sorted(mut.KNOBS):
        restore(mut.TARGETS)
        mut.apply(copy, knob)
        red = mut.self_check(copy).returncode
        restore(mut.TARGETS)
        green = mut.self_check(copy).returncode
        if red == 0 or green != 0:
            bad.append((knob, red, green))
    print(f"套->還原 逐個量完 {len(mut.KNOBS)} 個 knob,還原後沒回綠的:{len(bad)}")
    for b in bad:
        print("  DIRTY", b)

    # 反證:只還原 validate.py(舊機制),打 batch.py 的 knob 會殘留下去
    restore(mut.TARGETS)
    mut.apply(copy, batch_knobs[0])
    restore([mut.DEFAULT_TARGET])          # 舊版只還原這一支
    leaked = mut.self_check(copy).returncode
    restore(mut.TARGETS)
    print(f"反證:只還原 {mut.DEFAULT_TARGET} 之後 self-check exit={leaked} "
          f"({'仍紅 = 殘留,證明多目標還原是必要的' if leaked else '綠 = 反證不成立'})")
    assert leaked != 0, "反證不成立 —— 打 batch.py 的 knob 沒有殘留?重讀這格"
sys.exit(1 if bad else 0)
PY
ok $? "每個 knob 套下去會紅、還原之後回綠;而且證明只還原一支會殘留"

echo "==================================================================="
echo "==== AC8 「改寫的 SKILL.md 過 /writing-for-agents」的機械那半"
echo "==================================================================="
echo "     (散文品質是人判的;這裡量得到的是 repo 自己的 agent-writing lint 與"
echo "      幾個機械可導的形狀。判讀寫在 QA 報告裡,不由這支決定。)"

echo "---- 8a  repo 的全域 lint 對這支檔綠"
python "$ROOT/scripts/validate.py" > "$QA/v.txt" 2>&1
V=$?
tail -3 "$QA/v.txt"; echo "exit $V"
{ [ "$V" = 0 ] && ! grep -q 'FAIL.*slice-tickets' "$QA/v.txt"; }
ok $? "scripts/validate.py 綠,而且沒有一條 FAIL 指向 slice-tickets"

echo "---- 8b  改寫過的那幾段,機械可導的形狀"
python - "$ROOT/$SLICE" <<'PY'
import sys, pathlib, re
sys.stdout.reconfigure(encoding="utf-8")
t = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
lines = t.splitlines()
bad = []
assert lines[0] == "---" and lines[3] == "---", lines[:4]
nums = [int(m.group(1)) for m in (re.match(r"^## (\d)\. ", l) for l in lines) if m]
print("章節編號:", nums)
if nums != list(range(1, len(nums) + 1)):
    bad.append(f"章節編號跳號:{nums}")
para = t[t.index("**硬規則蓋過 client 的 override**"):t.index("點頭之後,")]
print("--- §4 新增那段 ---")
print(para.strip())
if "1. " not in para or "2. " not in para:
    bad.append("處置沒有拆成可照做的步驟")
if "為什麼" not in para:
    bad.append("沒有交代要回報他「為什麼」")
if "——" not in para:
    bad.append("沒有一句給原因(全是命令句)")
ceiling = [l for l in lines if "這條判準的天花板" in l][0]
for overclaim in ("由降級回路關住", "一律接得住", "全部接得住", "整個關住"):
    if overclaim in ceiling:
        bad.append(f"天花板還在過度宣稱:{overclaim}")
print("--- 天花板那句 ---")
print(ceiling)
for sentence in ("照你說的改,改完的才是寫進票裡的那個",
                 "這批的快慢分級,有要改的嗎?"):
    if t.count(sentence) != 1:
        bad.append(f"句子出現 {t.count(sentence)} 次:{sentence}")
print("\n機械可導的抱怨:", bad or "(無)")
sys.exit(1 if bad else 0)
PY
ok $? "章節連號、新增段落有步驟有原因、天花板沒有殘留的過度宣稱、沒有重複句"

echo "==================================================================="
echo "==== 覆蓋驗收項「4. 動到判斷邏輯…也一定被標成慢」—— 全分支重掃"
echo "==================================================================="

echo "---- A4a  judgement=true 而 coverage=[](沒有可看的行為)→ 慢"
classify '{"mode":"classify","tickets":[{"number":49,"coverage":[],"judgement":true}],"titles":{"49":"算票"}}'
{ [ "$CL_EXIT" = 0 ] && grep -q '^  #49  分級:慢 — 動到判斷邏輯或資料寫入,硬規則一律慢$' "$QA/out.txt"; }
ok $? "沒有可看的行為也照樣慢"

echo "---- A4b  拿「沒有任何路徑會靜靜落到快」當尺,掃過 classify_one 的所有分支"
python - "$ROOT/$BATCH" <<'PY'
import sys, itertools, importlib.util, pathlib
sys.stdout.reconfigure(encoding="utf-8")
spec = importlib.util.spec_from_file_location("batch_sweep120", pathlib.Path(sys.argv[1]))
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
        return False            # 硬規則票永遠不准是快(覆蓋驗收項第 4 條)
    return o == "快" or (o is None and not items)


bad, rows, tally = [], 0, {"快": 0, "慢": 0, "停": 0}
judged_fast, msgs = [], 0
for (cn, cv), (jn, jv), (on, ov) in itertools.product(
        covs.items(), judges.items(), ovrs.items()):
    rows += 1
    grade = None
    try:
        grade, reason = m.classify_one(cv, jv, ov)
        tally[grade] += 1
    except SystemExit as e:
        tally["停"] += 1
        reason = f"(當場停:{str(e)[:20]}…)"
        # #120 的重點:硬規則停下來的那條路,訊息不准指路去改旗標
        if jv and ov == "快":
            msgs += 1
            assert "旗標" not in str(e) and "judgement" not in str(e), str(e)
            assert "回去改票的內容" in str(e), str(e)
    items = [c for c in cv if not m.NO_COVERAGE_RE.match(str(c).strip())]
    if grade == m.GRADE_FAST:
        if jv:
            judged_fast.append((cn, jn, on, reason))
        if not sanctioned(items, jv, ov):
            bad.append((cn, jn, on, reason))
    print(f"  coverage={cn:<24} judgement={jn:<8} override={on:<9} -> {grade or '停'}")
print(f"\n掃過 {rows} 條路:快 {tally['快']} / 慢 {tally['慢']} / 當場停 {tally['停']}")
print(f"硬規則被頂著而當場停、訊息逐條驗過的:{msgs} 條")
print(f"judgement 為真、卻落到「快」的:{len(judged_fast)}")
for b in judged_fast:
    print("  FAST-WITH-JUDGEMENT", b)
print(f"靜靜落到「快」而散文沒授權的:{len(bad)}")
for b in bad:
    print("  UNSAFE", b)
sys.exit(1 if bad or judged_fast or not msgs else 0)
PY
ok $? "classify_one 全分支掃過:judgement=true 沒有一條落到「快」,停下來的訊息也逐條驗過"

echo "---- A4c  已知洞(#108 就記錄過,#120 沒動它):JSON key 打錯是靜的"
classify '{"mode":"classify","tickets":[{"number":49,"coverage":[],"judgment":true}],"titles":{"49":"算票"}}'
if { [ "$CL_EXIT" = 0 ] && grep -q '^  #49  分級:快' "$QA/out.txt"; }; then
  echo "RESULT KNOWN (judgement key 打錯):現況 = exit 0 且判快 —— 值打錯會停,key 打錯不會"
else
  echo "RESULT CHANGED (judgement key 打錯):跟 #108 記錄的不一樣,重讀 A4c"
  FAILED=1
fi

echo "==================================================================="
echo "==== 收尾:改壞的都只在副本上,repo 本體乾淨"
echo "==================================================================="
# 範圍 = 這支走查碰得到的那幾支檔。scripts/qa/ 底下新開的走查腳本本來就是
# untracked,不算「repo 被改壞」。
TOUCHED="skills scripts/validate.py scripts/qa/97-mutate.py"
git -C "$ROOT" status --porcelain -- $TOUCHED
[ -z "$(git -C "$ROOT" status --porcelain -- $TOUCHED)" ]
ok $? "skills/、validate.py、97-mutate.py 一個字都沒動"

set +x
echo
echo "==== walkthrough 走完 ===="
if [ "$FAILED" -ne 0 ]; then
  echo "有格子不合預期 —— 見上面的 RESULT FAIL"
  exit 1
fi
echo "所有格子符合預期(RESULT KNOWN 是本輪誠實記錄下來的天花板/已知洞,不算不合預期)"
