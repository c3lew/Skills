#!/usr/bin/env bash
# #57 QA walkthrough — 快車道接進產線(/next 推薦、切票守門、藍圖同步)。
# 全程 xtrace,指令與輸出同一份。
#
# 用法:bash scripts/qa/57-walkthrough.sh "$(mktemp -d)/qa57"
# 這支不寫任何東西到 GitHub,也不碰 repo 本體 — mutation 全部在拋棄式暫存目錄裡。
set -e
PS4='+ '
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
B="$ROOT/skills/build-batch/batch.py"
QA="$1"
rm -rf "$QA"
mkdir -p "$QA"
set -x

echo "==== STEP 1  regression suite(五支 self-check + validate)===="
python "$ROOT/scripts/validate.py"
python "$ROOT/scripts/validate.py" --self-check
python "$ROOT/scripts/batch.py" --self-check
python "$ROOT/scripts/install.py" --self-check
python "$ROOT/scripts/hooks/triage-to-maintain.py" --self-check
python "$B" --self-check

echo "==== STEP 2  AC1:/next 路由表新增一列,且排在單張 /build 那列上面 ===="
grep -n 'ready-for-agent' "$ROOT/skills/next/SKILL.md"
echo "-- 表序就是優先序 —— 先把那條規則本身印出來,不要只用講的"
grep -n '照表序推薦最上面的' "$ROOT/skills/next/SKILL.md"
echo "-- 所以批次那列的行號要小於單張那列"
python - "$ROOT/skills/next/SKILL.md" <<'PY'
import io, sys
lines = io.open(sys.argv[1], encoding="utf-8").read().splitlines()
batch = next(i for i, l in enumerate(lines, 1) if l.startswith("| ≥2 張"))
single = next(i for i, l in enumerate(lines, 1) if l.startswith("| 有 `ready-for-agent` 切片票沒開工"))
sys.stdout.reconfigure(encoding="utf-8")
print(f"批次列 line {batch} / 單張列 line {single} -> 批次在上:{batch < single}")
print(f"批次列原文:{lines[batch-1]}")
assert batch < single
assert "/build #N` 列替代" in lines[batch-1], "沒把 /build #N 列為替代"
PY

echo "==== STEP 3  AC2:推薦行雙寫 Codex 形式(推薦與替代兩半都要)===="
grep -n 'build-batch #51`(Codex: `\$build-batch #51`)' "$ROOT/skills/next/SKILL.md"
grep -n '替代是 `/build #47`(Codex: `\$build #47`)' "$ROOT/skills/next/SKILL.md"

echo "==== STEP 4  AC3:判斷重用 plan_batch — 不是照抄一份說法,是真的餵得動那支檔 ===="
echo "-- 4a  /next 自己指向哪支檔(這是 AC3 的主張,先印 /next 那邊)"
grep -n 'batch.py' "$ROOT/skills/next/SKILL.md"
echo "-- 那支檔存在"
ls -l "$B"
echo "-- 它裡面真的有 plan_batch,而且 CLI 走的就是它"
grep -n 'def plan_batch' "$B"
grep -n 'plan_batch(data\["tickets"\])' "$B"
echo "-- 而 /build-batch §3 跑的也是同一支檔(所以「同一支」不是說法,是同一個路徑)"
grep -n 'batch.py' "$ROOT/skills/build-batch/SKILL.md" | head -3
echo "-- 4b  /next SKILL.md 裡那段範例 JSON 原封不動抄出來餵進去(48 卡在 47 後面 -> 只開得了 1 張,不命中這一列)"
python - "$ROOT/skills/next/SKILL.md" > "$QA/example.json" <<'PY'
import io, re, sys
text = io.open(sys.argv[1], encoding="utf-8").read()
block = re.search(r"<<'JSON'\n(.*?)\nJSON\n", text, re.S).group(1)
sys.stdout.reconfigure(encoding="utf-8")
sys.stdout.write(block)
PY
cat "$QA/example.json"
python "$B" < "$QA/example.json"
echo "-- 4c  同一支檔、換成兩張彼此不卡 -> 「要開」2 張,命中批次那一列"
printf '%s\n' '{"tickets": [{"number": 47, "state": "open", "blocked_by": []}, {"number": 48, "state": "open", "blocked_by": []}], "titles": {"47": "一", "48": "二"}}' > "$QA/two.json"
cat "$QA/two.json"
python "$B" < "$QA/two.json"
echo "-- 4d  「要開」只有 1 張時不命中(卡關那張不算)—— 用 4b 那份的計數"
python - "$B" "$QA/example.json" "$QA/two.json" <<'PY'
import io, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")
for path in sys.argv[2:]:
    out = subprocess.run([sys.executable, sys.argv[1]],
                         stdin=io.open(path, encoding="utf-8"),
                         capture_output=True, text=True, encoding="utf-8").stdout
    head = out.splitlines()[0]
    n = int(head.split("(")[1].split(" 張")[0])
    print(f"{path.split('/')[-1]}: 要開 {n} 張 -> 命中批次列:{n >= 2}")
PY

echo "==== STEP 5  AC4:slice-tickets 帶「一張 blocking 邊都沒宣告就回報 client」這一步 ===="
sed -n '/## 4. Delta:blocking 邊對帳/,/## 5\./p' "$ROOT/skills/slice-tickets/SKILL.md"

echo "==== STEP 6  AC5:validate.py guard + mutation-bite(拿真的 SKILL.md 咬,不是手寫字串)===="
echo "-- 6a  未動過的 slice-tickets:綠"
mkdir -p "$QA/m/skills/slice-tickets"
cp "$ROOT/skills/slice-tickets/SKILL.md" "$QA/m/skills/slice-tickets/SKILL.md"
python - "$ROOT" "$QA/m" <<'PY'
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(sys.argv[1]) / "scripts"))
sys.stdout.reconfigure(encoding="utf-8")
import validate as V
root = pathlib.Path(sys.argv[2])
errs = [e for e in V.validate(root / "skills", root) if "blocking" in e]
print(f"blocking 相關 error {len(errs)} 條:{errs}")
assert errs == []
PY
echo "-- 6b  把那一句從真的 SKILL.md 刪掉 -> guard 要紅,而且要指名 slice-tickets"
python - "$QA/m/skills/slice-tickets/SKILL.md" <<'PY'
import io, sys
p = sys.argv[1]
t = io.open(p, encoding="utf-8").read()
assert "一張 blocking 邊都沒宣告" in t
io.open(p, "w", encoding="utf-8").write(t.replace("一張 blocking 邊都沒宣告", "", 1))
sys.stdout.reconfigure(encoding="utf-8")
print("已刪掉那句(只刪第一次出現)")
PY
python - "$ROOT" "$QA/m" <<'PY'
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(sys.argv[1]) / "scripts"))
sys.stdout.reconfigure(encoding="utf-8")
import validate as V
root = pathlib.Path(sys.argv[2])
errs = [e for e in V.validate(root / "skills", root) if "blocking" in e]
for e in errs:
    print("RED:", e)
assert errs and all(e.startswith("skills/slice-tickets/SKILL.md") for e in errs)
PY
echo "-- 6c  假陽性那半:只『提到』/to-tickets(交棒行、路由表)的 skill 不上鉤"
python - "$ROOT" <<'PY'
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(sys.argv[1]) / "scripts"))
sys.stdout.reconfigure(encoding="utf-8")
import validate as V
skills = sorted((pathlib.Path(sys.argv[1]) / "skills").glob("*/SKILL.md"))
callers, mentioners = [], []
for s in skills:
    t = s.read_text(encoding="utf-8")
    if V.TO_TICKETS_CALL_RE.search(t):
        callers.append(s.parent.name)
    elif "/to-tickets" in t:
        mentioners.append(s.parent.name)
print(f"母體(呼叫 /to-tickets 發佈票)共 {len(callers)} 張:{callers}")
print(f"只是提到、不上鉤的共 {len(mentioners)} 張:{mentioners}")
assert callers, "母體空了 — mutation 咬不到東西"
PY
echo "-- 6d  母體空了 -> #57 自己那條 vacuity assert 要當場失敗(不是別條先擋下來)"
echo "   做法:整份 skills 原封不動複製一份,只抽掉唯一呼叫 /to-tickets 的那張(slice-tickets),"
echo "   其他 guard 的母體都還在 -> 擋下來的一定是 #57 那條。"
python - "$ROOT" "$QA" <<'PYX'
import sys, pathlib, shutil, tempfile
sys.path.insert(0, str(pathlib.Path(sys.argv[1]) / "scripts"))
sys.stdout.reconfigure(encoding="utf-8")
import validate as V
real = pathlib.Path(sys.argv[1])
with tempfile.TemporaryDirectory(dir=sys.argv[2]) as tmp:
    fake = pathlib.Path(tmp) / "repo"
    shutil.copytree(real / "skills", fake / "skills",
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.rmtree(fake / "skills" / "slice-tickets")
    kept = sorted(d.name for d in (fake / "skills").iterdir() if d.is_dir())
    print(f"假 repo 留下 {len(kept)} 張 skill,抽掉的是 slice-tickets")
    orig = V.REPO
    V.REPO = fake
    try:
        V.self_check()
        print("BUG:母體空了竟然還綠")
        raise SystemExit(1)
    except AssertionError as e:
        print("空母體 -> AssertionError:", e)
        assert "no skill publishes tickets via `/to-tickets`" in str(e), f"擋下來的不是 #57 那條:{e}"
        print("確認:擋下來的就是 #57 的 vacuity assert")
    finally:
        V.REPO = orig
PYX

echo "==== STEP 7  AC6:blueprint.md Greenfield 第 4 格加註快車道 ===="
grep -n '^| 4 |' "$ROOT/docs/blueprint.md"

echo "==== STEP 9(額外,不在驗收條裡)同型全掃:prose-presence guard 的繞過方向 ===="
echo "   判準:written-evidence 的「Mutation 要驗兩種:改壞 / 繞過」。"
echo "   母體用數的、不用「所有」—— 掃描器本身在 scripts/qa/57-guard-sweep.py。"
python "$ROOT/scripts/qa/57-guard-sweep.py" "$ROOT"

echo "==== STEP 8  AC7:python scripts/validate.py 全綠(repo 本體,未被 mutation 汙染)===="
git -C "$ROOT" status --porcelain -- skills scripts docs || true
python "$ROOT/scripts/validate.py"
set +x
echo "==== walkthrough 結束 ===="
