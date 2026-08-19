#!/usr/bin/env bash
# #56 QA walkthrough — 排隊補位 + 中斷續跑。全程 xtrace,指令與輸出同一份。
#
# 用法:bash scripts/qa/56-walkthrough.sh <一個可以砍掉重建的目錄>
# 這支不寫任何東西到 GitHub — 對票只做唯讀查詢(STEP 0 / STEP 9)。
set -e
PS4='+ '
LANE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"   # repo root
B="$LANE/skills/build-batch/batch.py"
QA="$1"          # 拋棄式 git repo,用來真的開 worktree
rm -rf "$QA"
mkdir -p "$QA"
set -x

echo "==== STEP 0  真的在排隊的那兩張票(#54、#55,同一份 spec、這一輪沒被開工)現在的 comment 數 ===="
gh issue view 54 --repo c3lew/Skills --json comments --jq '.comments | length'
gh issue view 55 --repo c3lew/Skills --json comments --jq '.comments | length'

echo "==== STEP 1  regression suite ===="
python "$LANE/scripts/validate.py"
python "$LANE/scripts/validate.py" --self-check
python "$LANE/scripts/batch.py" --self-check
python "$LANE/scripts/install.py" --self-check
python "$LANE/scripts/hooks/triage-to-maintain.py" --self-check
python "$B" --self-check

echo "==== STEP 2  5 張能跑 -> 只開 3 張,其餘進佇列(SKILL.md §3)===="
printf '%s\n' '{"tickets": [{"number": 61, "state": "open", "blocked_by": []}, {"number": 62, "state": "open", "blocked_by": []}, {"number": 63, "state": "open", "blocked_by": []}, {"number": 64, "state": "open", "blocked_by": []}, {"number": 65, "state": "open", "blocked_by": []}], "titles": {"61": "一", "62": "二", "63": "三", "64": "四", "65": "五"}}' > "$QA/plan.json"
cat "$QA/plan.json"
python "$B" < "$QA/plan.json"

echo "==== STEP 2b  開頭那幾條:名單 5 張只印 3 行(印幾行才開幾個 worktree,§6.2)===="
printf '%s\n' '{"mode": "start", "numbers": [61, 62, 63, 64, 65], "running": [], "titles": {"61": "一", "62": "二", "63": "三", "64": "四", "65": "五"}}' > "$QA/start.json"
cat "$QA/start.json"
python "$B" < "$QA/start.json"
echo "-- 接續了 2 條的情況:名額只剩 1,同一份名單只印 1 行"
printf '%s\n' '{"mode": "start", "numbers": [61, 62, 63, 64, 65], "running": [70, 71], "titles": {"61": "一", "62": "二", "63": "三"}}' > "$QA/start2.json"
cat "$QA/start2.json"
python "$B" < "$QA/start2.json"

echo "==== STEP 3  #61 做完 -> 補 #64;#62 做完 -> 補 #65(SKILL.md §6.3)===="
printf '%s\n' '{"mode": "refill", "running": [62, 63], "queue": [64, 65], "titles": {"64": "四", "65": "五"}}' > "$QA/r1.json"
cat "$QA/r1.json"
python "$B" < "$QA/r1.json"
printf '%s\n' '{"mode": "refill", "running": [63, 64], "queue": [65], "titles": {"65": "五"}}' > "$QA/r2.json"
cat "$QA/r2.json"
python "$B" < "$QA/r2.json"

echo "==== STEP 4  名額滿 / 佇列空 -> 不補位,不硬開 ===="
printf '%s\n' '{"mode": "refill", "running": [63, 64, 65], "queue": [66], "titles": {}}' > "$QA/r3.json"
cat "$QA/r3.json"
python "$B" < "$QA/r3.json"
printf '%s\n' '{"mode": "refill", "running": [65], "queue": [], "titles": {}}' > "$QA/r4.json"
cat "$QA/r4.json"
python "$B" < "$QA/r4.json"

echo "==== STEP 5  真的開 worktree:三條在跑,收掉一條之後才補第四條進來 ===="
git -C "$QA" init -q
git -C "$QA" -c user.email=qa@x -c user.name=qa commit -q --allow-empty -m init
git -C "$QA" worktree add .git/batch-worktrees/61 -b batch/61
git -C "$QA" worktree add .git/batch-worktrees/62 -b batch/62
git -C "$QA" worktree add .git/batch-worktrees/63 -b batch/63
echo "-- 三條 lane 各自產出一個 commit(在自己的工作區裡,互不相干)"
git -C "$QA/.git/batch-worktrees/61" -c user.email=qa@x -c user.name=qa commit -q --allow-empty -m "lane 61 的產出"
git -C "$QA/.git/batch-worktrees/62" -c user.email=qa@x -c user.name=qa commit -q --allow-empty -m "lane 62 的產出(未合併)"
echo "-- 同時存在的 lane 數(母體 = .git/batch-worktrees/,同 §10 清場判準)"
git -C "$QA" worktree list --porcelain | grep -c -F /.git/batch-worktrees/
echo "-- #61 綠了:照 §8 收掉工作區(branch 留著),名額讓出來給 #64"
git -C "$QA" worktree remove .git/batch-worktrees/61
git -C "$QA" worktree add .git/batch-worktrees/64 -b batch/64
git -C "$QA" worktree list --porcelain | grep -c -F /.git/batch-worktrees/
echo "-- 被收掉工作區的 lane,branch 照 §8 留著"
git -C "$QA" branch --list 'batch/*'

echo "==== STEP 5b  #61 照 §8 合回主線(等一下要驗它在中斷之後還在)===="
git -C "$QA" -c user.email=qa@x -c user.name=qa merge --no-ff batch/61 -m "Merge batch/61"
git -C "$QA" log --oneline

echo "==== STEP 6  中斷:已 merge 的留主線、未合併的留 worktree + branch,票上留「中斷,可續」 ===="
printf '%s\n' '{"mode": "interrupted", "numbers": [62, 63, 64], "spec": 51, "titles": {"62": "二", "63": "三", "64": "四"}}' > "$QA/stop.json"
cat "$QA/stop.json"
python "$B" < "$QA/stop.json"
echo "-- 中斷後未合併的 worktree 與 branch 都還在(什麼都不回收)"
git -C "$QA" worktree list --porcelain | grep -F /.git/batch-worktrees/
git -C "$QA" branch --list 'batch/*'
echo "-- 已 merge 的 #61 照樣留在主線,中斷沒有把它退掉"
git -C "$QA" log --oneline master
git -C "$QA" branch --contains batch/61 master
echo "-- 未合併的 #62 產出還在它自己的 branch 上,沒混進主線"
git -C "$QA" log --oneline batch/62 -1
git -C "$QA" log --oneline master --grep "lane 62" --format="master 上找到的 lane 62 產出:%s"

echo "==== STEP 7  重跑:偵測既有 worktree -> 接續,不重開(SKILL.md §6.1)===="
echo "-- 混進一條別人開的 worktree(Claude Code 給 subagent 常駐的那種)"
git -C "$QA" worktree add .claude/worktrees/agent-9 -b agent/9
git -C "$QA" worktree list --porcelain > "$QA/wt.txt"
cat "$QA/wt.txt"
echo "-- 把上面那份原封不動餵進 batch.py,票號由它從路徑認"
python - "$QA/wt.txt" > "$QA/resume.json" <<'PY'
import json, sys, io
raw = io.open(sys.argv[1], encoding="utf-8").read()
sys.stdout.reconfigure(encoding="utf-8")
print(json.dumps({"mode": "resume", "worktrees": raw,
                  "titles": {"62": "二", "63": "三", "64": "四"}},
                 ensure_ascii=False))
PY
cat "$QA/resume.json"
python "$B" < "$QA/resume.json"

echo "==== STEP 8  清場 ===="
git -C "$QA" worktree list --porcelain | grep -F /.git/batch-worktrees/ | sed 's/^worktree //' | while read -r p; do git -C "$QA" worktree remove --force "$p"; done
git -C "$QA" worktree remove --force .claude/worktrees/agent-9
git -C "$QA" worktree list --porcelain | grep -F /.git/batch-worktrees/ || echo "(沒有輸出 = lane 收乾淨了,grep exit 1)"
git -C "$QA" branch --list 'batch/*'

echo "==== STEP 9  #54、#55 整輪下來 comment 數沒變 —— 排隊的票在開工前不被碰(§6)===="
gh issue view 54 --repo c3lew/Skills --json comments --jq '.comments | length'
gh issue view 55 --repo c3lew/Skills --json comments --jq '.comments | length'
set +x
echo "==== walkthrough 結束 ===="
