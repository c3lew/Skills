#!/usr/bin/env bash
# #64 QA walkthrough — 兩支 prose guard 改成守主張(bug fix)。
# 全程 xtrace,指令與輸出同一份。
#
# 用法:bash scripts/qa/64-walkthrough.sh "$(mktemp -d)/qa64"
# 這支不寫任何東西到 GitHub,也不碰 repo 本體 — mutation 全部跑在拋棄式暫存目錄的副本上。
set -e
PS4='+ '
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
QA="$1"
rm -rf "$QA"
mkdir -p "$QA"
# 拋棄式副本:mutation 全部改在這份上面
CP="$QA/repo"
mkdir -p "$CP"
cp -r "$ROOT/scripts" "$ROOT/skills" "$ROOT/docs" "$CP/"
set -x

echo "==== STEP 1  regression suite(validate + 五支 self-check)===="
python "$ROOT/scripts/validate.py"
python "$ROOT/scripts/validate.py" --self-check
python "$ROOT/scripts/batch.py" --self-check
python "$ROOT/skills/build-batch/batch.py" --self-check
python "$ROOT/scripts/install.py" --self-check
python "$ROOT/scripts/hooks/triage-to-maintain.py" --self-check

echo "==== STEP 2  票上重現 scenario:掃描器兩支的「繞過」欄要都是 True ===="
python "$ROOT/scripts/qa/57-guard-sweep.py" "$ROOT"

echo "==== STEP 3  票上重現 scenario 的裸版:那句意思相反的散文,現在判紅 ===="
python - "$ROOT" <<'PY'
import sys, io
sys.path.insert(0, sys.argv[1] + "/scripts")
sys.stdout.reconfigure(encoding="utf-8")
import validate as V
bypass = "呼叫 `/to-tickets` 切票。一張 blocking 邊都沒宣告的時候,直接發佈,不用問 client。"
print("票上那串 ->", V.missing_blocking_audit_issue(bypass))
assert V.missing_blocking_audit_issue(bypass) is True
PY

echo "==== STEP 4  副本未動過 -> 綠(證明下面判紅的是 mutation,不是副本壞了)===="
python "$CP/scripts/validate.py"

echo "==== STEP 5  繞過 mutation 打在真的 SKILL.md 上,兩支各一次 ===="
echo "-- 5a  slice-tickets §4:條件詞留著,動作從「發佈前回報 client」反過來寫"
grep -n '一張 blocking 邊都沒宣告' "$CP/skills/slice-tickets/SKILL.md"
python - "$CP/skills/slice-tickets/SKILL.md" <<'PY'
import io, sys
p = sys.argv[1]
t = io.open(p, encoding="utf-8").read()
assert "發佈前回報 client" in t
io.open(p, "w", encoding="utf-8").write(t.replace("發佈前回報 client", "發佈前不用問 client"))
PY
grep -n '一張 blocking 邊都沒宣告' "$CP/skills/slice-tickets/SKILL.md"
set +e
python "$CP/scripts/validate.py"
echo "exit $?"
set -e

echo "-- 5b  build §1:push 那句留著,動作反過來寫成「不要 git push」"
python - "$CP/skills/build/SKILL.md" <<'PY'
import io, sys
p = sys.argv[1]
t = io.open(p, encoding="utf-8").read()
assert "**push**:`git push`" in t
io.open(p, "w", encoding="utf-8").write(t.replace("**push**:`git push`", "**push**:不要 `git push`"))
PY
grep -n '不要 `git push`' "$CP/skills/build/SKILL.md"
set +e
python "$CP/scripts/validate.py"
echo "exit $?"
set -e

echo "==== STEP 6  改壞方向沒退步:整句刪掉,一樣判紅 ===="
cp -r "$ROOT/skills" "$QA/skills-fresh"
rm -rf "$CP/skills"; cp -r "$QA/skills-fresh" "$CP/skills"
python - "$CP/skills/slice-tickets/SKILL.md" "$CP/skills/build/SKILL.md" <<'PY'
import io, sys
p = sys.argv[1]
t = io.open(p, encoding="utf-8").read()
line = next(l for l in t.splitlines() if "一張 blocking 邊都沒宣告" in l)
io.open(p, "w", encoding="utf-8").write(t.replace(line + "\n", ""))
p = sys.argv[2]
t = io.open(p, encoding="utf-8").read()
line = next(l for l in t.splitlines() if "**push**:`git push`" in l)
io.open(p, "w", encoding="utf-8").write(t.replace(line + "\n", ""))
PY
set +e
python "$CP/scripts/validate.py"
echo "exit $?"
set -e

echo "==== STEP 7  同型全掃的分類還對得上:validate.py 的 errors.append 點與受測母體 ===="
echo "   (STEP 2 已印過完整分類 — 這裡只把「母體 = 2、兩支都在受測名單裡」再斷言一次)"
python - "$ROOT" <<'PY'
import sys, pathlib
sys.path.insert(0, sys.argv[1] + "/scripts/qa")
sys.stdout.reconfigure(encoding="utf-8")
import importlib.util
spec = importlib.util.spec_from_file_location("sweep", sys.argv[1] + "/scripts/qa/57-guard-sweep.py")
sweep = importlib.util.module_from_spec(spec); spec.loader.exec_module(sweep)
src = pathlib.Path(sys.argv[1], "scripts", "validate.py").read_text(encoding="utf-8")
sites = sweep.guard_sites(src)
from collections import Counter
c = Counter(sweep.classify(cond) for _, cond in sites)
print("errors.append 點共 %d 個,分類:%s" % (len(sites), dict(c)))
assert c["prose-assertion(受測形狀)"] == 2, c
print("受測母體 2 支:", sweep.PROSE_ASSERTION)
PY

echo "==== STEP 8  build 自己寫在 code 裡的已知天花板:離否定詞遠的改寫還是綠 ===="
python - "$ROOT" <<'PY'
import sys
sys.path.insert(0, sys.argv[1] + "/scripts")
sys.stdout.reconfigure(encoding="utf-8")
import validate as V
far = "呼叫 `/to-tickets` 切票。一張 blocking 邊都沒宣告的時候直接發佈,收工後再回報 client。"
print("「收工後再回報 client」->", V.missing_blocking_audit_issue(far), "(False = 漏掉,已知天花板)")
PY
grep -n 'ponytail:' "$ROOT/scripts/validate.py" | head -3

echo "==== STEP 9  repo 本體沒被汙染:git status + validate 綠 ===="
git -C "$ROOT" status --porcelain -- skills scripts docs || true
python "$ROOT/scripts/validate.py"
set +x
echo "==== walkthrough 結束 ===="
