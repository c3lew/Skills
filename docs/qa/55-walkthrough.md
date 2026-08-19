# QA walkthrough — #55 build-batch 4/6:撞車 — agent 自己解,解不掉停下來講清楚

第 2 輪。第 1 輪抓到一條 blocking(§7a 查「跟誰撞」的指令安靜回空的),同一條 lane 內修掉、
重跑本檔;第 1 輪的其他步驟與本輪相同,本檔是修完之後從頭跑一遍的完整實錄。

環境:受測物在 `D:/Self Project/Skills/.git/batch-worktrees/55`(branch `batch/55`),
working tree 乾淨(唯一異動就是本檔)。本票是 skill 文件 + CLI 純函式 + 一串 client 端真的會
貼進終端機的 git 指令,沒有 UI、沒有視覺 oracle,不走 Playwright;本檔是終端實錄。

**兩個地方,分清楚:**

- **regression 與 CLI 輸出**(步驟 1)跑在受測物的 worktree,只讀不寫。
- **git 那一整套**(步驟 2、3、4)跑在 scratchpad 的臨時 repo(`…/scratchpad/qa55a`、
  `qa55b`、`qa55c`),origin 指向同樣在 scratchpad 的 bare repo。本 repo 與主 repo 沒有被
  開過額外 worktree、沒多出 branch、沒被 push,清場見步驟 5。

**實錄的呈現規則**:步驟 2–4 各是一支 script 一次跑完的輸出,**指令那幾行是 bash 自己的
xtrace 印的**(`PS4='+ '`,`set -x`),不是事後照著寫的 — 引號、`cd`、command substitution
全部照實出現,順序就是真的執行順序(stdout 與 stderr 合流)。整段原封不動貼上,沒有摺疊、
沒有省略號。唯一的改動是把 scratchpad 的長路徑統一縮寫成 `…/scratchpad`。開場那段建 repo /
建 lane 的準備動作跑在 `set -x` 之前(它不是受測物,是佈景),所以實錄從「§7 開始一張一張合」
那一行起跳。

判定 oracle = 票上「覆蓋驗收項」原句:

> 兩張改到同一個檔案撞車 → agent 自己解掉,票上留一行紀錄;解不掉就停下來,講清楚哪兩張撞在哪個檔案。

一鍵重開(沿用既有 CLI QA 入口,在受測物的 worktree 底下跑):

```bash
cd "D:/Self Project/Skills/.git/batch-worktrees/55"
python scripts/validate.py --self-check
python scripts/validate.py
python scripts/batch.py --self-check
python skills/build-batch/batch.py --self-check
python scripts/install.py --self-check
python scripts/hooks/triage-to-maintain.py --self-check
```

撞車那兩條情境的重跑:`bash …/scratchpad/qa55a.sh`(解得掉)、`bash …/scratchpad/qa55b.sh`
(解不掉)、`bash …/scratchpad/qa55c.sh`(§7a 的 mutation)。三支都自己建 repo、自己清,
不依賴前一次的殘留。

## 步驟 1 — regression suite

```text
$ python scripts/validate.py --self-check
OK validate self-check green
rc=0
$ python scripts/validate.py
OK validate green
rc=0
$ python scripts/batch.py --self-check
OK batch self-check green
rc=0
$ python skills/build-batch/batch.py --self-check
OK batch self-check green
rc=0
$ python scripts/install.py --self-check
[fixture] FAIL skills/bad: missing SKILL.md
OK install self-check green
rc=0
$ python scripts/hooks/triage-to-maintain.py --self-check
OK triage-to-maintain self-check green
rc=0
```

全綠(`install.py` 那行 `[fixture] FAIL skills/bad` 是它自己的 fixture 輸出,不是紅)。

## 步驟 2 — 情境 A:兩張改到同一個檔案,撞車而且解得掉

佈景:`docs/notes.md` 三行,lane 47 與 lane 48 各改中間那一行(必撞),lane 49 改別的檔案
(不撞)。照 §7 一張一張合。

```text
warning: in the working copy of 'docs/notes.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/notes.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/notes.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/other.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/other.md', LF will be replaced by CRLF the next time Git touches it
+ git merge --no-ff -m 'Merge branch '\''batch/47'\''' batch/47
Merge made by the 'ort' strategy.
 docs/notes.md | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
+ git push -q
+ git worktree remove .git/batch-worktrees/47
+ git merge --no-ff -m 'Merge branch '\''batch/48'\''' batch/48
Auto-merging docs/notes.md
CONFLICT (content): Merge conflict in docs/notes.md
Automatic merge failed; fix conflicts and then commit the result.
+ echo 'merge exit=1'
merge exit=1
+ git diff --name-only --diff-filter=U
docs/notes.md
+ git log --merges --full-history --format=%s -1 -- docs/notes.md
Merge branch 'batch/47'
+ printf 'line1\n47 改的那行\n48 改的那行\nline3\n'
+ git add docs/notes.md
warning: in the working copy of 'docs/notes.md', LF will be replaced by CRLF the next time Git touches it
+ git commit -q --no-edit
+ git push -q
+ cat docs/notes.md
line1
47 改的那行
48 改的那行
line3
++ python 'D:/Self Project/Skills/.git/batch-worktrees/55/skills/build-batch/batch.py'
+ note='撞車已解:#48 點頭 跟 #47 名單 都改到 docs/notes.md — 兩邊改的那行都留著,照 47 → 48 的順序擺。合併照常繼續,不用你處理。'
+ echo '撞車已解:#48 點頭 跟 #47 名單 都改到 docs/notes.md — 兩邊改的那行都留著,照 47 → 48 的順序擺。合併照常繼續,不用你處理。'
撞車已解:#48 點頭 跟 #47 名單 都改到 docs/notes.md — 兩邊改的那行都留著,照 47 → 48 的順序擺。合併照常繼續,不用你處理。
+ git merge --no-ff -m 'Merge branch '\''batch/49'\''' batch/49
Merge made by the 'ort' strategy.
 docs/other.md | 1 +
 1 file changed, 1 insertion(+)
 create mode 100644 docs/other.md
+ git push -q
+ git worktree remove .git/batch-worktrees/48
+ git worktree remove .git/batch-worktrees/49
+ git log --oneline --graph -6
*   ace2175 Merge branch 'batch/49'
|\  
| * 201746d 49
* |   6632a37 Merge branch 'batch/48'
|\ \  
| * | 1671985 48
| |/  
* |   492994d Merge branch 'batch/47'
|\ \  
| |/  
|/|   
| * 8917d6c 47
|/  
+ git status --porcelain
+ git worktree list --porcelain
+ grep -F /.git/batch-worktrees/
+ echo '(沒有殘留的 lane 工作區)'
(沒有殘留的 lane 工作區)
+ git branch --list 'batch/*'
  batch/47
  batch/48
  batch/49
```

對著驗收原句逐條看:

- 「兩張改到同一個檔案撞車」— `git merge` 的 `CONFLICT (content): Merge conflict in
  docs/notes.md`,exit 1。
- 「agent 自己解掉」— §7a 兩行查出撞在 `docs/notes.md`、跟這批裡的 `batch/47` 撞;§7b 解掉之後
  `cat docs/notes.md` 兩邊改的那行都在,沒有衝突標記。(這裡由 QA 代打
  `/resolving-merge-conflicts` 的解法:兩邊都留著、依序擺。)
- 「票上留一行紀錄」— `conflict-resolved` 那一行印出來了,而且自己講完哪兩張(#48、#47)、
  哪個檔案(`docs/notes.md`)、怎麼解的(兩邊改的那行都留著)。
- 「不打擾 client、流程繼續」— 緊接著 `Merge branch 'batch/49'` 照常合完,中間沒有停下來問。
- 收尾狀態:`git status --porcelain` 空的、lane 工作區沒有殘留、`batch/*` 三條 branch 都還在。

## 步驟 3 — 情境 B:一樣撞車,但解不掉

同一組佈景,§7b 判定解不掉(兩張對同一行做了互斥的決定),走 §7c。

```text
warning: in the working copy of 'docs/notes.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/notes.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/notes.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/other.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/other.md', LF will be replaced by CRLF the next time Git touches it
+ git merge --no-ff -m 'Merge branch '\''batch/47'\''' batch/47
Merge made by the 'ort' strategy.
 docs/notes.md | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
+ git push -q
+ git worktree remove .git/batch-worktrees/47
+ git merge --no-ff -m 'Merge branch '\''batch/48'\''' batch/48
Auto-merging docs/notes.md
CONFLICT (content): Merge conflict in docs/notes.md
Automatic merge failed; fix conflicts and then commit the result.
+ echo 'merge exit=1'
merge exit=1
+ git diff --name-only --diff-filter=U
docs/notes.md
+ git log --merges --full-history --format=%s -1 -- docs/notes.md
Merge branch 'batch/47'
+ git merge --abort
+ git status --porcelain
+ git log --oneline -1
7eca8ef Merge branch 'batch/47'
+ git diff --stat origin/main
++ python 'D:/Self Project/Skills/.git/batch-worktrees/55/skills/build-batch/batch.py'
+ note='撞車停下:#48 點頭 跟 #47 名單 都改到 docs/notes.md,自己解不掉 — 這批合併停在這裡,等你決定。

已經合進主線的(1 張):
  #47 名單

還沒合的(2 張),工作區與 branch 都留著:
  #48 點頭 — .git/batch-worktrees/48(branch batch/48)
  #49 收尾 — .git/batch-worktrees/49(branch batch/49)

沒有猜、沒有強推,也沒有把任何一邊蓋掉。'
+ echo '撞車停下:#48 點頭 跟 #47 名單 都改到 docs/notes.md,自己解不掉 — 這批合併停在這裡,等你決定。

已經合進主線的(1 張):
  #47 名單

還沒合的(2 張),工作區與 branch 都留著:
  #48 點頭 — .git/batch-worktrees/48(branch batch/48)
  #49 收尾 — .git/batch-worktrees/49(branch batch/49)

沒有猜、沒有強推,也沒有把任何一邊蓋掉。'
撞車停下:#48 點頭 跟 #47 名單 都改到 docs/notes.md,自己解不掉 — 這批合併停在這裡,等你決定。

已經合進主線的(1 張):
  #47 名單

還沒合的(2 張),工作區與 branch 都留著:
  #48 點頭 — .git/batch-worktrees/48(branch batch/48)
  #49 收尾 — .git/batch-worktrees/49(branch batch/49)

沒有猜、沒有強推,也沒有把任何一邊蓋掉。
+ git worktree list --porcelain
+ grep -F /.git/batch-worktrees/
worktree …/scratchpad/qa55b/.git/batch-worktrees/48
worktree …/scratchpad/qa55b/.git/batch-worktrees/49
+ git branch --list 'batch/*'
  batch/47
+ batch/48
+ batch/49
+ cat docs/notes.md
line1
47 改的那行
line3
```

對著驗收原句逐條看:

- 「解不掉就停下來」— `git merge --abort` 之後 `git status --porcelain` 空的、
  `git diff --stat origin/main` 空的:主線就是「上一張合完」的樣子,沒有帶衝突標記的 index
  留給 client。
- 「講清楚哪兩張撞在哪個檔案」— `conflict-stopped` 第一行就是 `#48 點頭 跟 #47 名單 都改到
  docs/notes.md`。整段沒有出現 conflict / merge / index 這種字。
- 「已經 merge 成功的留在主線」— `git log --oneline -1` 是 `Merge branch 'batch/47'`,
  而且 `cat docs/notes.md` 是 47 的內容。
- 「還沒 merge 的 lane 保留 worktree 與 branch」— `git worktree list` 撈得到 48、49 兩個
  工作區,`git branch --list 'batch/*'` 三條都在。
- 「不猜、不強推、不 `--force`」— 整段實錄裡沒有 `--force`、`-X ours/theirs`、`reset --hard`。
  這條同時被 `batch.py` 的 `forced_merge_issue` 咬住(步驟 4)。

## 步驟 4 — 第 1 輪抓到的那條:§7a 少了 `--full-history` 會安靜回空的

第 1 輪跑情境 A 的時候,§7a 第二行原本寫的是 `git log --merges --format=%s -1 -- <檔案>`,
在 conflict 當下**回空的** — git 的 history simplification 會把「跟其中一個 parent 同樹」的
merge commit 省掉,而合 lane 的 merge 每個都是這種形狀。照文件跑的 agent 會以為查不出另一張
票,於是本來解得掉的撞車也走進 §7c 停下來,白白打擾 client。

修法:加 `--full-history`,並把這個 flag 加進 `batch.py` 的 `CONFLICT_LINES`,以後拿掉它
self-check 直接紅。下面是兩個版本並排跑在同一個 conflict 上:

```text
warning: in the working copy of 'docs/notes.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/notes.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/notes.md', LF will be replaced by CRLF the next time Git touches it
+ git log --merges --format=%s -1 -- docs/notes.md
++ git log --merges --format=%s -1 -- docs/notes.md
++ wc -c
+ echo 上面那行輸出的字數:0
上面那行輸出的字數:0
+ git log --merges --full-history --format=%s -1 -- docs/notes.md
Merge branch 'batch/47'
+ set +x
```

`wc -c` 是 0 → 舊版真的什麼都沒印,不是被截掉。新版印出 `Merge branch 'batch/47'`。

`CONFLICT_LINES` / `forced_merge_issue` 這兩組 guard 的 mutation 測試在
`batch.py --self-check` 裡常駐(步驟 1 已綠):拿掉「呼叫 `/resolving-merge-conflicts`」、
「worktree 與 branch 都留著」、「`git merge --abort`」、「`--full-history`」任何一句,或在
bash block 裡貼一行 `--force` / `-X ours` / `-X theirs` / `push -f` / `reset --hard`,
self-check 都紅。

## 步驟 5 — 清場

```text
+ rm -rf …/scratchpad/qa55a …/scratchpad/qa55a-remote.git …/scratchpad/qa55b …/scratchpad/qa55b-remote.git
+ ls …/scratchpad
+ grep qa55
qa55a.out
qa55a.sh
qa55b.out
qa55b.sh
+ cd 'D:/Self Project/Skills/.git/batch-worktrees/55'
+ git status --porcelain
+ git worktree list --porcelain
+ grep -F /.git/batch-worktrees/
worktree D:/Self Project/Skills/.git/batch-worktrees/54
worktree D:/Self Project/Skills/.git/batch-worktrees/55
worktree D:/Self Project/Skills/.git/batch-worktrees/56
+ git branch --list 'batch/*'
+ batch/54
* batch/55
+ batch/56
  batch/61
  batch/62
```

scratchpad 只剩三支 `.sh` 與它們的 `.out`(重跑用),臨時 repo 全刪;受測物 worktree
`git status` 乾淨;`.git/batch-worktrees/` 底下只有本批的 54 / 55 / 56 三條 lane
(本票沒有多開也沒有收掉別人的)。

## 判定

覆蓋驗收項一條,pass。無 blocking、無 known issue。

未涵蓋:`/resolving-merge-conflicts` 原件本身的解題能力(本檔由 QA 代打它的輸出)、
以及真的在 GitHub 上把那兩行紀錄貼成 comment(`gh issue comment` 的行為在 #53 已驗過,
本票沿用同一條路)。
