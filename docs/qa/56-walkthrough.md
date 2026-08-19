# QA walkthrough — #56 排隊補位 + 中斷續跑

拿驗收清單實測 `/build-batch` 的排隊補位與中斷續跑。CLI 純函式 + skill 文件,沒有 UI、沒有視覺 oracle,不走 Playwright、沒有錄影 — 實錄就是下面這份終端 transcript。

全程 bash xtrace(`PS4='+ '` + `set -x`),指令與輸出在同一份裡,沒有事後 render。餵進去的 JSON 每一份都先 `printf` 建檔、再 `cat` 出來,才 pipe 進 `batch.py`。

一鍵重開(client-demo 直接抄,`<repo>` 換成 repo 根目錄):

```bash
bash scripts/qa/56-walkthrough.sh "$(mktemp -d)/qa56repo"
```

步驟:

| # | 驗的是 |
| --- | --- |
| 1 | regression suite(全部 `--self-check` + `validate.py`) |
| 2 | 5 張能跑 → 要開 3 張、排隊 2 張 |
| 2b | 開頭那幾條也扣名額:同一份 5 張名單,沒接續時印 3 行、接續 2 條時只印 1 行 |
| 3 | 做完一張補一張:收掉 #61 補 #64、收掉 #62 補 #65,行尾都是「同時跑 3 條」 |
| 4 | 名額滿 / 佇列空 → 印「不補位」,不硬開 |
| 5 | 真的開 worktree:3 條在跑時數就是 3,收掉一條才開得進第 4 張;被收掉的 branch 留著 |
| 6 | 中斷:三條未合併 lane 各留一行「中斷,可續」,worktree 與 branch 都沒被回收 |
| 7 | 重跑偵測:整份 `git worktree list --porcelain`(含主 repo 與 subagent 的 `.claude/worktrees/agent-9`)餵進去,只認出 62/63/64 三條 lane |
| 8 | 清場 |

## Transcript

```
+ echo '==== STEP 1  regression suite ===='
==== STEP 1  regression suite ====
+ python 'D:/Self Project/Skills/.git/batch-worktrees/56/scripts/validate.py'
OK validate green
+ python 'D:/Self Project/Skills/.git/batch-worktrees/56/scripts/validate.py' --self-check
OK validate self-check green
+ python 'D:/Self Project/Skills/.git/batch-worktrees/56/scripts/batch.py' --self-check
OK batch self-check green
+ python 'D:/Self Project/Skills/.git/batch-worktrees/56/scripts/install.py' --self-check
[fixture] FAIL skills/bad: missing SKILL.md
OK install self-check green
+ python 'D:/Self Project/Skills/.git/batch-worktrees/56/scripts/hooks/triage-to-maintain.py' --self-check
OK triage-to-maintain self-check green
+ python 'D:/Self Project/Skills/.git/batch-worktrees/56/skills/build-batch/batch.py' --self-check
OK batch self-check green
+ echo '==== STEP 2  5 張能跑 -> 只開 3 張,其餘進佇列(SKILL.md §3)===='
==== STEP 2  5 張能跑 -> 只開 3 張,其餘進佇列(SKILL.md §3)====
+ printf '%s\n' '{"tickets": [{"number": 61, "state": "open", "blocked_by": []}, {"number": 62, "state": "open", "blocked_by": []}, {"number": 63, "state": "open", "blocked_by": []}, {"number": 64, "state": "open", "blocked_by": []}, {"number": 65, "state": "open", "blocked_by": []}], "titles": {"61": "一", "62": "二", "63": "三", "64": "四", "65": "五"}}'
+ cat C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo/plan.json
{"tickets": [{"number": 61, "state": "open", "blocked_by": []}, {"number": 62, "state": "open", "blocked_by": []}, {"number": 63, "state": "open", "blocked_by": []}, {"number": 64, "state": "open", "blocked_by": []}, {"number": 65, "state": "open", "blocked_by": []}], "titles": {"61": "一", "62": "二", "63": "三", "64": "四", "65": "五"}}
+ python 'D:/Self Project/Skills/.git/batch-worktrees/56/skills/build-batch/batch.py'
要開(3 張):
  #61 一
  #62 二
  #63 三
排隊(2 張):
  #64 四
  #65 五
還卡著(0 張):
  (無)
+ echo '==== STEP 2b  開頭那幾條:名單 5 張只印 3 行(印幾行才開幾個 worktree,§6.2)===='
==== STEP 2b  開頭那幾條:名單 5 張只印 3 行(印幾行才開幾個 worktree,§6.2)====
+ printf '%s\n' '{"mode": "start", "numbers": [61, 62, 63, 64, 65], "running": [], "titles": {"61": "一", "62": "二", "63": "三", "64": "四", "65": "五"}}'
+ cat C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo/start.json
{"mode": "start", "numbers": [61, 62, 63, 64, 65], "running": [], "titles": {"61": "一", "62": "二", "63": "三", "64": "四", "65": "五"}}
+ python 'D:/Self Project/Skills/.git/batch-worktrees/56/skills/build-batch/batch.py'
開工 #61 一 — 工作區 .git/batch-worktrees/61(branch batch/61)
開工 #62 二 — 工作區 .git/batch-worktrees/62(branch batch/62)
開工 #63 三 — 工作區 .git/batch-worktrees/63(branch batch/63)
+ echo '-- 接續了 2 條的情況:名額只剩 1,同一份名單只印 1 行'
-- 接續了 2 條的情況:名額只剩 1,同一份名單只印 1 行
+ printf '%s\n' '{"mode": "start", "numbers": [61, 62, 63, 64, 65], "running": [70, 71], "titles": {"61": "一", "62": "二", "63": "三"}}'
+ cat C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo/start2.json
{"mode": "start", "numbers": [61, 62, 63, 64, 65], "running": [70, 71], "titles": {"61": "一", "62": "二", "63": "三"}}
+ python 'D:/Self Project/Skills/.git/batch-worktrees/56/skills/build-batch/batch.py'
開工 #61 一 — 工作區 .git/batch-worktrees/61(branch batch/61)
+ echo '==== STEP 3  #61 做完 -> 補 #64;#62 做完 -> 補 #65(SKILL.md §6.3)===='
==== STEP 3  #61 做完 -> 補 #64;#62 做完 -> 補 #65(SKILL.md §6.3)====
+ printf '%s\n' '{"mode": "refill", "running": [62, 63], "queue": [64, 65], "titles": {"64": "四", "65": "五"}}'
+ cat C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo/r1.json
{"mode": "refill", "running": [62, 63], "queue": [64, 65], "titles": {"64": "四", "65": "五"}}
+ python 'D:/Self Project/Skills/.git/batch-worktrees/56/skills/build-batch/batch.py'
補位 #64 四 — 工作區 .git/batch-worktrees/64(branch batch/64);同時跑 3 條,佇列剩 1 張
+ printf '%s\n' '{"mode": "refill", "running": [63, 64], "queue": [65], "titles": {"65": "五"}}'
+ cat C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo/r2.json
{"mode": "refill", "running": [63, 64], "queue": [65], "titles": {"65": "五"}}
+ python 'D:/Self Project/Skills/.git/batch-worktrees/56/skills/build-batch/batch.py'
補位 #65 五 — 工作區 .git/batch-worktrees/65(branch batch/65);同時跑 3 條,佇列剩 0 張
+ echo '==== STEP 4  名額滿 / 佇列空 -> 不補位,不硬開 ===='
==== STEP 4  名額滿 / 佇列空 -> 不補位,不硬開 ====
+ printf '%s\n' '{"mode": "refill", "running": [63, 64, 65], "queue": [66], "titles": {}}'
+ cat C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo/r3.json
{"mode": "refill", "running": [63, 64, 65], "queue": [66], "titles": {}}
+ python 'D:/Self Project/Skills/.git/batch-worktrees/56/skills/build-batch/batch.py'
不補位 — 沒有名額或佇列已空;同時跑 3 條,佇列剩 1 張
+ printf '%s\n' '{"mode": "refill", "running": [65], "queue": [], "titles": {}}'
+ cat C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo/r4.json
{"mode": "refill", "running": [65], "queue": [], "titles": {}}
+ python 'D:/Self Project/Skills/.git/batch-worktrees/56/skills/build-batch/batch.py'
不補位 — 沒有名額或佇列已空;同時跑 1 條,佇列剩 0 張
+ echo '==== STEP 5  真的開 worktree:三條在跑時第四張開不了,收掉一條才補得進來 ===='
==== STEP 5  真的開 worktree:三條在跑時第四張開不了,收掉一條才補得進來 ====
+ git -C C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo init -q
+ git -C C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo -c user.email=qa@x -c user.name=qa commit -q --allow-empty -m init
+ git -C C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo worktree add .git/batch-worktrees/61 -b batch/61
Preparing worktree (new branch 'batch/61')
HEAD is now at 09439d7 init
+ git -C C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo worktree add .git/batch-worktrees/62 -b batch/62
Preparing worktree (new branch 'batch/62')
HEAD is now at 09439d7 init
+ git -C C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo worktree add .git/batch-worktrees/63 -b batch/63
Preparing worktree (new branch 'batch/63')
HEAD is now at 09439d7 init
+ echo '-- 同時存在的 lane 數(母體 = .git/batch-worktrees/,同 §10 清場判準)'
-- 同時存在的 lane 數(母體 = .git/batch-worktrees/,同 §10 清場判準)
+ git -C C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo worktree list --porcelain
+ grep -c -F /.git/batch-worktrees/
3
+ echo '-- 收掉 #61 這條 lane,名額讓出來'
-- 收掉 #61 這條 lane,名額讓出來
+ git -C C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo worktree remove .git/batch-worktrees/61
+ git -C C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo worktree add .git/batch-worktrees/64 -b batch/64
Preparing worktree (new branch 'batch/64')
HEAD is now at 09439d7 init
+ git -C C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo worktree list --porcelain
+ grep -c -F /.git/batch-worktrees/
3
+ echo '-- 被收掉的 lane 的 branch 照 §8 留著'
-- 被收掉的 lane 的 branch 照 §8 留著
+ git -C C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo branch --list 'batch/*'
  batch/61
+ batch/62
+ batch/63
+ batch/64
+ echo '==== STEP 6  中斷:未合併的 lane 留 worktree + branch,票上留「中斷,可續」 ===='
==== STEP 6  中斷:未合併的 lane 留 worktree + branch,票上留「中斷,可續」 ====
+ printf '%s\n' '{"mode": "interrupted", "numbers": [62, 63, 64], "spec": 51, "titles": {"62": "二", "63": "三", "64": "四"}}'
+ cat C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo/stop.json
{"mode": "interrupted", "numbers": [62, 63, 64], "spec": 51, "titles": {"62": "二", "63": "三", "64": "四"}}
+ python 'D:/Self Project/Skills/.git/batch-worktrees/56/skills/build-batch/batch.py'
中斷,可續 #62 二 — 未合併,工作區 .git/batch-worktrees/62 與 branch batch/62 都留著;重跑 `/build-batch #51`(Codex: `$build-batch #51`)會接續這條 lane
中斷,可續 #63 三 — 未合併,工作區 .git/batch-worktrees/63 與 branch batch/63 都留著;重跑 `/build-batch #51`(Codex: `$build-batch #51`)會接續這條 lane
中斷,可續 #64 四 — 未合併,工作區 .git/batch-worktrees/64 與 branch batch/64 都留著;重跑 `/build-batch #51`(Codex: `$build-batch #51`)會接續這條 lane
+ echo '-- 中斷後 worktree 與 branch 都還在(什麼都不回收)'
-- 中斷後 worktree 與 branch 都還在(什麼都不回收)
+ git -C C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo worktree list --porcelain
+ grep -F /.git/batch-worktrees/
worktree C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo/.git/batch-worktrees/62
worktree C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo/.git/batch-worktrees/63
worktree C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo/.git/batch-worktrees/64
+ git -C C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo branch --list 'batch/*'
  batch/61
+ batch/62
+ batch/63
+ batch/64
+ echo '==== STEP 7  重跑:偵測既有 worktree -> 接續,不重開(SKILL.md §6.1)===='
==== STEP 7  重跑:偵測既有 worktree -> 接續,不重開(SKILL.md §6.1)====
+ echo '-- 混進一條別人開的 worktree(Claude Code 給 subagent 常駐的那種)'
-- 混進一條別人開的 worktree(Claude Code 給 subagent 常駐的那種)
+ git -C C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo worktree add .claude/worktrees/agent-9 -b agent/9
Preparing worktree (new branch 'agent/9')
HEAD is now at 09439d7 init
+ git -C C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo worktree list --porcelain
+ cat C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo/wt.txt
worktree C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo
HEAD 09439d74eae56725c325a4c604488f0c053a9eed
branch refs/heads/master

worktree C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo/.claude/worktrees/agent-9
HEAD 09439d74eae56725c325a4c604488f0c053a9eed
branch refs/heads/agent/9

worktree C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo/.git/batch-worktrees/62
HEAD 09439d74eae56725c325a4c604488f0c053a9eed
branch refs/heads/batch/62

worktree C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo/.git/batch-worktrees/63
HEAD 09439d74eae56725c325a4c604488f0c053a9eed
branch refs/heads/batch/63

worktree C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo/.git/batch-worktrees/64
HEAD 09439d74eae56725c325a4c604488f0c053a9eed
branch refs/heads/batch/64

+ echo '-- 把上面那份原封不動餵進 batch.py,票號由它從路徑認'
-- 把上面那份原封不動餵進 batch.py,票號由它從路徑認
+ python - C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo/wt.txt
+ cat C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo/resume.json
{"mode": "resume", "worktrees": "worktree C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo\nHEAD 09439d74eae56725c325a4c604488f0c053a9eed\nbranch refs/heads/master\n\nworktree C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo/.claude/worktrees/agent-9\nHEAD 09439d74eae56725c325a4c604488f0c053a9eed\nbranch refs/heads/agent/9\n\nworktree C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo/.git/batch-worktrees/62\nHEAD 09439d74eae56725c325a4c604488f0c053a9eed\nbranch refs/heads/batch/62\n\nworktree C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo/.git/batch-worktrees/63\nHEAD 09439d74eae56725c325a4c604488f0c053a9eed\nbranch refs/heads/batch/63\n\nworktree C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo/.git/batch-worktrees/64\nHEAD 09439d74eae56725c325a4c604488f0c053a9eed\nbranch refs/heads/batch/64\n\n", "titles": {"62": "二", "63": "三", "64": "四"}}
+ python 'D:/Self Project/Skills/.git/batch-worktrees/56/skills/build-batch/batch.py'
接續 #62 二 — 既有工作區 .git/batch-worktrees/62(branch batch/62)還在,不重開
接續 #63 三 — 既有工作區 .git/batch-worktrees/63(branch batch/63)還在,不重開
接續 #64 四 — 既有工作區 .git/batch-worktrees/64(branch batch/64)還在,不重開
+ echo '==== STEP 8  清場 ===='
==== STEP 8  清場 ====
+ git -C C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo worktree list --porcelain
+ grep -F /.git/batch-worktrees/
+ sed 's/^worktree //'
+ read -r p
+ git -C C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo worktree remove --force C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo/.git/batch-worktrees/62
+ read -r p
+ git -C C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo worktree remove --force C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo/.git/batch-worktrees/63
+ read -r p
+ git -C C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo worktree remove --force C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo/.git/batch-worktrees/64
+ read -r p
+ git -C C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo worktree remove --force .claude/worktrees/agent-9
+ git -C C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo worktree list --porcelain
+ grep -F /.git/batch-worktrees/
+ echo '(沒有輸出 = lane 收乾淨了,grep exit 1)'
(沒有輸出 = lane 收乾淨了,grep exit 1)
+ git -C C:/Users/user/AppData/Local/Temp/claude/D--Self-Project-Skills/cb4f8175-1a2f-4604-a31e-62e3651d2fb2/scratchpad/qa56repo branch --list 'batch/*'
  batch/61
  batch/62
  batch/63
  batch/64
+ set +x
==== walkthrough 結束 ====
```
