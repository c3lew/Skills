# QA walkthrough — #55 build-batch 4/6:撞車 — agent 自己解,解不掉停下來講清楚

第 4 輪。前三輪各被獨立 judge 打回一次,打回的東西都修進受測物或補進證據了:

- 第 1 輪:§7a 查「跟誰撞」的指令安靜回空的(blocking,已修)。
- 第 2 輪:「agent 自己解掉」是 QA 用 `printf` 代打、「票上留一行紀錄」只 `echo` 沒真的貼票
  (兩條 blocking,本輪都改成真的跑);另外 judge 抓到 §7a 會在「第三張乾淨動過同一個檔案」
  的情況報出錯的票號、以及「查不出另一張票」那條逃生路在工具端是死路(兩條都修進受測物)。

- 第 3 輪:§7a 只寫了「兩邊都改到同一段」那條認票路,遇到 modify/delete(一張刪檔、
  另一張改同一個檔案)問不出東西,agent 會掉進「查不出來」的逃生路,對 client 講一句假話
  (「跟主線上既有的內容撞」),而且第二張票號整個消失(blocking,已修:§7a 加一條
  `--diff-filter=D` 的認票路,並寫明只有 `--contains` 空掉才算查不出來)。

本輪的證據全部重新產生,不沿用前幾輪的檔案。

環境:受測物在 `D:/Self Project/Skills/.git/batch-worktrees/55`(branch `batch/55`)。
本票是 skill 文件 + CLI 純函式 + 一串 client 端真的會貼進終端機的 git 指令,沒有 UI、
沒有視覺 oracle,不走 Playwright;本檔是終端實錄。

**三個地方,分清楚:**

- **regression**(步驟 1)跑在受測物的 worktree,只讀不寫。
- **git 那一整套**(步驟 2–5)跑在 scratchpad 的臨時 repo,origin 指向同樣在 scratchpad 的
  bare repo。主 repo 沒有被開過額外 worktree、沒多出 branch、沒被 push,清場見步驟 6。
- **`gh` 那一段**(步驟 3)打的是真的 GitHub,真的在 #55 上留下 comment。

**實錄的呈現規則**:每個步驟是一支 script 一次跑完的輸出,**指令那幾行是 bash 自己的
xtrace 印的**(`PS4='+ '`,`set -x`),不是事後照著寫的 — 引號、`'''` 逃脫、`++` 的
command substitution 層級、git 自己的 `+ batch/48`(branch 被別的 worktree checkout 的原生
標記)全部照實出現,順序就是真的執行順序(stdout 與 stderr 合流)。整段原封不動貼上,沒有
摺疊、沒有省略號。兩處改動:scratchpad 的長路徑統一縮寫成 `…/scratchpad`;Windows 每次寫檔
都會噴的 `warning: LF will be replaced by CRLF` 用 `grep -v` 濾掉(它跟受測行為無關,一行檔案
一行 warning 會把實錄淹掉)。開場建 repo / 建 lane 的準備動作跑在 `set -x` 之前(那是佈景,
不是受測物),所以實錄從「§7 開始一張一張合」那一行起跳。

判定 oracle = 票上「覆蓋驗收項」原句:

> 兩張改到同一個檔案撞車 → agent 自己解掉,票上留一行紀錄;解不掉就停下來,講清楚哪兩張撞在哪個檔案。

一鍵重開:

```bash
cd "D:/Self Project/Skills/.git/batch-worktrees/55"
bash …/scratchpad/reg.sh        # 步驟 1:regression
bash …/scratchpad/qa55e-1.sh    # 步驟 2:撞車 + §7a 認票(跑完停在 conflict,等 agent 解)
bash …/scratchpad/qa55e-2.sh    # 步驟 3:驗解出來的結果 + 貼票 + 流程繼續
bash …/scratchpad/qa55f.sh      # 步驟 4:解不掉 → 停下
bash …/scratchpad/qa55g.sh      # 步驟 5:§7a 的三條邊界
bash …/scratchpad/clean.sh      # 步驟 6:清場
```

步驟 2 與 3 中間夾的是一個獨立 subagent(它呼叫 `/resolving-merge-conflicts` 解衝突),那一段
不是 script,見步驟 2 末尾。

## 步驟 1 — regression suite

```text
+ python scripts/validate.py --self-check
OK validate self-check green
+ python scripts/validate.py
OK validate green
+ python scripts/batch.py --self-check
OK batch self-check green
+ python skills/build-batch/batch.py --self-check
OK batch self-check green
+ python scripts/install.py --self-check
[fixture] FAIL skills/bad: missing SKILL.md
OK install self-check green
+ python scripts/hooks/triage-to-maintain.py --self-check
OK triage-to-maintain self-check green
```

全綠(`install.py` 那行 `[fixture] FAIL skills/bad` 是它自己的 fixture 輸出,不是紅)。

## 步驟 2 — 撞車發生 + §7a 查出「跟誰撞」

佈景是四條 lane 的一批:`docs/notes.md` 有「待辦」與「附註」兩段,lane 47 改待辦、lane 42 改
附註(同一個檔案、不同段,乾淨)、lane 48 也改待辦(跟 47 必撞)、lane 49 改別的檔案。
照 §7 的順序 47 → 42 → 48 → 49 一張一張合。

**42 是故意擺在中間的**:它讓「最近一次動到這個檔案的 merge」變成 42,而真正撞的是 47 —
§7a 認票如果問錯問題,這裡就會把錯的票號印給 client。

```text
+ git merge -q --no-ff --no-edit batch/47
+ git push -q
+ git worktree remove .git/batch-worktrees/47
+ git merge -q --no-ff --no-edit batch/42
Auto-merging docs/notes.md
+ git push -q
+ git worktree remove .git/batch-worktrees/42
+ git merge --no-ff --no-edit batch/48
Auto-merging docs/notes.md
CONFLICT (content): Merge conflict in docs/notes.md
Automatic merge failed; fix conflicts and then commit the result.
+ echo 'merge exit=1'
merge exit=1
+ git diff --name-only --diff-filter=U
docs/notes.md
+ git diff -- docs/notes.md
diff --cc docs/notes.md
index 2a7bc95,82c548e..0000000
--- a/docs/notes.md
+++ b/docs/notes.md
@@@ -2,7 -2,7 +2,11 @@@
  
  ## 待辦
  
++<<<<<<< HEAD
 +- 47 加的:寫 QA 實錄
++=======
+ - 48 加的:補交棒 comment
++>>>>>>> batch/48
  
  ## 附註
  
+ git log '-S47 加的:寫 QA 實錄' --format=%h -1 HEAD --not MERGE_HEAD -- docs/notes.md
04f7de1
++ git log '-S47 加的:寫 QA 實錄' --format=%h -1 HEAD --not MERGE_HEAD -- docs/notes.md
+ git branch --list 'batch/*' --contains 04f7de1
  batch/47
```

- 撞車真的發生:`CONFLICT (content): Merge conflict in docs/notes.md`,exit 1。
- §7a 第一行給檔案(`docs/notes.md`),第二行給衝突兩側的內容,第三行問「主線那側那段文字
  是哪顆 commit 寫的」(`04f7de1`),第四行把它換算成 lane → **`batch/47`**,不是中間那張 42。

**接下來這一步不是 QA 做的**:把這個卡住的 repo 交給一個獨立 subagent,只告訴它「這裡有一個
進行中的 merge conflict,呼叫 `resolving-merge-conflicts` skill 解掉」,並明講禁止 `--abort` /
`--force` / `-X ours|theirs` / `reset --hard`。它回報的原話(節錄它自己講的判斷):

> **(1) 呼叫的 skill**:`resolving-merge-conflicts`(Skill tool)。
>
> **(2) 怎麼判斷該怎麼解**:先看三方版本 … base 的 `## 待辦` 只有一行 `- 舊的待辦`。
> ours(HEAD,已經 merge 過 batch/47 + batch/42)把那行換成 `- 47 加的:寫 QA 實錄`。
> theirs(batch/48)把同一行換成 `- 48 加的:補交棒 comment`。兩邊都是各自往待辦清單加自己的
> 項目,不是同一件事的兩種寫法,也沒有互斥語意 — 只是剛好動到同一行才撞到。所以照 skill 的
> 「preserve both intents where possible」,兩行都留 … 沒有用任何禁用手段。

QA 自己沒有動過任何一個字元 — 下一步是拿它的結果來驗。

## 步驟 3 — 解掉之後:紀錄貼上票、流程繼續

```text
+ git log --oneline -4
03cab1c Merge branch 'batch/48'
77f2e33 Merge branch 'batch/42'
8b7911c Merge branch 'batch/47'
1f5d9f0 48
+ git status --short
+ cat docs/notes.md
# 專案筆記

## 待辦

- 47 加的:寫 QA 實錄
- 48 加的:補交棒 comment

## 附註

- 42 加的:附註改寫
+ git diff --check
+ git push -q
++ python 'D:/Self Project/Skills/.git/batch-worktrees/55/skills/build-batch/batch.py'
+ note='撞車已解:#9048 補交棒 comment 跟 #9047 寫 QA 實錄 都改到 docs/notes.md — 兩張加的是各自獨立的待辦、不是二選一,所以兩條都留著,照 9047 → 9048 的順序擺。合併照常繼續,不用你處理。'
+ echo '撞車已解:#9048 補交棒 comment 跟 #9047 寫 QA 實錄 都改到 docs/notes.md — 兩張加的是各自獨立的待辦、不是二選一,所以兩條都留著,照 9047 → 9048 的順序擺。合併照常繼續,不用你處理。'
撞車已解:#9048 補交棒 comment 跟 #9047 寫 QA 實錄 都改到 docs/notes.md — 兩張加的是各自獨立的待辦、不是二選一,所以兩條都留著,照 9047 → 9048 的順序擺。合併照常繼續,不用你處理。
+ echo '撞車已解:#9048 補交棒 comment 跟 #9047 寫 QA 實錄 都改到 docs/notes.md — 兩張加的是各自獨立的待辦、不是二選一,所以兩條都留著,照 9047 → 9048 的順序擺。合併照常繼續,不用你處理。'
+ gh issue comment 55 --repo c3lew/Skills --body-file -
https://github.com/c3lew/Skills/issues/55#issuecomment-5338893531
+ echo '撞車已解:#9048 補交棒 comment 跟 #9047 寫 QA 實錄 都改到 docs/notes.md — 兩張加的是各自獨立的待辦、不是二選一,所以兩條都留著,照 9047 → 9048 的順序擺。合併照常繼續,不用你處理。'
+ gh issue comment 55 --repo c3lew/Skills --body-file -
https://github.com/c3lew/Skills/issues/55#issuecomment-5338893784
+ git merge -q --no-ff --no-edit batch/49
+ git push -q
+ git worktree remove .git/batch-worktrees/48
+ git worktree remove .git/batch-worktrees/49
+ git log --oneline --graph -8
*   438c1b3 Merge branch 'batch/49'
|\  
| * 3e06bb4 49
* |   03cab1c Merge branch 'batch/48'
|\ \  
| * | 1f5d9f0 48
| |/  
* |   77f2e33 Merge branch 'batch/42'
|\ \  
| * | f85231a 42
| |/  
* |   8b7911c Merge branch 'batch/47'
|\ \  
| |/  
|/|   
| * 04f7de1 47
|/  
+ git status --porcelain
+ git worktree list --porcelain
+ grep -F /.git/batch-worktrees/
+ echo '(沒有殘留的 lane 工作區)'
(沒有殘留的 lane 工作區)
+ git branch --list 'batch/*'
  batch/42
  batch/47
  batch/48
  batch/49
```

- **「agent 自己解掉」**:`git log --oneline -4` 的 `03cab1c Merge branch 'batch/48'` 是
  subagent 收的 merge commit,`git status --short` 空、`git diff --check` 沒話講;
  `cat docs/notes.md` 兩張的待辦都在,42 的附註也還在,沒有衝突標記。
- **「票上留一行紀錄」**:`conflict-resolved` 的輸出經 `gh issue comment` 真的貼上 GitHub,
  兩則 comment 的 URL 在輸出裡(#55 上點得開)。票號用 `#9047` / `#9048` 這種不存在的號碼,
  是為了不去騷擾這批真的在跑的票 — 走的路徑與命令完全是 §7b 的原句。
- **「不打擾 client、流程繼續」**:緊接著 `Merge branch 'batch/49'` 照常合完,中間沒有停下來問。
- 收尾:`git status --porcelain` 空、lane 工作區沒有殘留、`batch/*` 四條 branch 都還在。

## 步驟 4 — 解不掉:停下整個合併階段

同樣的佈景,但兩張對同一條待辦做了互斥的決定(47 說「只留 47 這條」、48 說「只留 48 這條」),
`/resolving-merge-conflicts` 判不出誰對誰錯 — 這種要 client 說了算,走 §7c。

```text
+ git merge -q --no-ff --no-edit batch/47
+ git push -q
+ git worktree remove .git/batch-worktrees/47
+ git merge --no-ff --no-edit batch/48
Auto-merging docs/notes.md
CONFLICT (content): Merge conflict in docs/notes.md
Automatic merge failed; fix conflicts and then commit the result.
+ echo 'merge exit=1'
merge exit=1
+ git diff --name-only --diff-filter=U
docs/notes.md
++ git log '-S只留 47 這條' --format=%h -1 HEAD --not MERGE_HEAD -- docs/notes.md
+ sha=701211c
+ git branch --list 'batch/*' --contains 701211c
  batch/47
+ git merge --abort
+ git status --porcelain
+ git log --oneline -1
76eb687 Merge branch 'batch/47'
+ git diff --stat origin/main
++ python 'D:/Self Project/Skills/.git/batch-worktrees/55/skills/build-batch/batch.py'
+ note='撞車停下:#48 補交棒 comment 跟 #47 寫 QA 實錄 都改到 docs/notes.md,自己解不掉 — 這批合併停在這裡,等你決定。

已經合進主線的(1 張):
  #47 寫 QA 實錄

還沒合的(2 張),工作區與 branch 都留著:
  #48 補交棒 comment — .git/batch-worktrees/48(branch batch/48)
  #49 收尾 — .git/batch-worktrees/49(branch batch/49)

沒有猜、沒有強推,也沒有把任何一邊蓋掉。'
+ echo '撞車停下:#48 補交棒 comment 跟 #47 寫 QA 實錄 都改到 docs/notes.md,自己解不掉 — 這批合併停在這裡,等你決定。

已經合進主線的(1 張):
  #47 寫 QA 實錄

還沒合的(2 張),工作區與 branch 都留著:
  #48 補交棒 comment — .git/batch-worktrees/48(branch batch/48)
  #49 收尾 — .git/batch-worktrees/49(branch batch/49)

沒有猜、沒有強推,也沒有把任何一邊蓋掉。'
撞車停下:#48 補交棒 comment 跟 #47 寫 QA 實錄 都改到 docs/notes.md,自己解不掉 — 這批合併停在這裡,等你決定。

已經合進主線的(1 張):
  #47 寫 QA 實錄

還沒合的(2 張),工作區與 branch 都留著:
  #48 補交棒 comment — .git/batch-worktrees/48(branch batch/48)
  #49 收尾 — .git/batch-worktrees/49(branch batch/49)

沒有猜、沒有強推,也沒有把任何一邊蓋掉。
+ git worktree list --porcelain
+ grep -F /.git/batch-worktrees/
worktree …/scratchpad/qa55f/.git/batch-worktrees/48
worktree …/scratchpad/qa55f/.git/batch-worktrees/49
+ git branch --list 'batch/*'
  batch/47
+ batch/48
+ batch/49
+ cat docs/notes.md
# 專案筆記

## 待辦

- 只留 47 這條,48 那條不要
```

- **「講清楚哪兩張撞在哪個檔案」**:`撞車停下:#48 補交棒 comment 跟 #47 寫 QA 實錄 都改到
  docs/notes.md`。整段沒有 conflict / merge / index / rebase 這些字。
- **「停下時狀態乾淨」**:`git merge --abort` 之後 `git status --porcelain` 空、
  `git diff --stat origin/main` 空 — 沒有留一個帶衝突標記的 index 給 client。
- **「已經 merge 成功的留在主線」**:`git log --oneline -1` 是 `Merge branch 'batch/47'`,
  `cat docs/notes.md` 是 47 的內容。
- **「還沒 merge 的 lane 保留 worktree 與 branch」**:`git worktree list` 撈得到 48、49,
  `git branch --list 'batch/*'` 三條都在(48/49 前面的 `+` 是 git 自己標的「被別的 worktree
  checkout 中」)。
- **「不猜、不強推、不 `--force`」**:整段沒有 `--force`、`-X ours/theirs`、`reset --hard`。
  這條同時被 `batch.py` 的 `forced_merge_issue` 咬在文件那一面(見步驟 6 的 regression)。

## 步驟 5 — §7a 的三條邊界

**甲**:第三張(42)乾淨地動過同一個檔案。**丙**:一張刪檔、另一張改同一個檔案
(modify/delete)。**乙**:主線那側那段內容根本不是這批寫的(主線自己的 commit 改的)。

```text
Auto-merging notes.md
+ git log --merges --full-history --format=%s -1 -- notes.md
Merge branch 'batch/42'
++ git log '-S47 加的待辦' --format=%h -1 HEAD --not MERGE_HEAD -- notes.md
+ sha=1f0bc4b
+ git branch --list 'batch/*' --contains 1f0bc4b
+ batch/47
+ set +x
+ git diff --name-only --diff-filter=U
notes.md
+ git status --short
DU notes.md
+ git diff -- notes.md
* Unmerged path notes.md
++ git log --diff-filter=D --format=%h -1 HEAD --not MERGE_HEAD -- notes.md
+ sha=e19dff7
+ echo sha=e19dff7
sha=e19dff7
+ git branch --list 'batch/*' --contains e19dff7
+ batch/47
+ set +x
+ git diff --name-only --diff-filter=U
notes.md
++ git log -S主線自己改的待辦 --format=%h -1 HEAD --not MERGE_HEAD -- notes.md
+ sha=ddcb124
+ echo sha=ddcb124
sha=ddcb124
+ git branch --list 'batch/*' --contains ddcb124
++ git branch --list 'batch/*' --contains ddcb124
++ wc -c
+ echo 上一行的輸出字數:0
上一行的輸出字數:0
+ python 'D:/Self Project/Skills/.git/batch-worktrees/55/skills/build-batch/batch.py'
撞車停下:#48 補交棒 comment 跟主線上既有的內容撞在 notes.md,自己解不掉 — 這批合併停在這裡,等你決定。

已經合進主線的(0 張):
  (無)

還沒合的(1 張),工作區與 branch 都留著:
  #48 補交棒 comment — .git/batch-worktrees/48(branch batch/48)

沒有猜、沒有強推,也沒有把任何一邊蓋掉。
+ set +x
```

- 甲:舊問法(`git log --merges --full-history -1`)回 **`Merge branch 'batch/42'`** — 錯的票號,
  client 會被指去看一張根本沒撞的票;現在文件裡的問法回 **`batch/47`**,對的。
- 丙:`git status --short` 是 `DU`,`git diff -- notes.md` 只吐一行 `* Unmerged path notes.md` —
  主線那側被刪掉了,**沒有內容可以拿去 `-S`**。這時候照 §7a 改問「誰刪的」
  (`--diff-filter=D`)→ **`batch/47`**,票號照樣報得準。(第 3 輪 judge 抓到的就是這條:
  當時 §7a 只寫了 `-S` 那一條,agent 問不出來就會掉進「查不出來」的逃生路,對 client 講
  「跟主線上既有的內容撞」— 那是假的,撞的是這批裡刪檔的 #47,而且第二張票號整個消失。)
- 乙:`git branch --contains` 回空的(`wc -c` = 0,是真的空不是被截),這才算真的查不出來 →
  `conflict-stopped` 的 `numbers` 只給正在合的那一張,印出來是「**#48 補交棒 comment 跟主線上
  既有的內容撞在 notes.md**」。工具收得下這條路(第 2 輪 judge 抓到的死路:當時 `_two` 硬性
  要求兩張票,照文件走的 agent 會撞 `SystemExit`,然後只能自己現編一句貼上票)。

## 步驟 6 — 清場

```text
+ rm -rf …/scratchpad/qa55e …/scratchpad/qa55e-remote.git …/scratchpad/qa55f …/scratchpad/qa55f-remote.git
+ ls …/scratchpad
+ grep -E '^qa55|^probe'
probe3.sh
qa55e-1.out
qa55e-1.sh
qa55e-2.out
qa55e-2.sh
qa55f.out
qa55f.sh
qa55g.out
qa55g.sh
+ cd 'D:/Self Project/Skills/.git/batch-worktrees/55'
+ git status --porcelain
 M skills/build-batch/SKILL.md
 M skills/build-batch/batch.py
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

scratchpad 只剩本輪四支 `.sh` 與它們的 `.out`(重跑用),臨時 repo 全刪;受測物 worktree 只有
本票要改的兩個檔;`.git/batch-worktrees/` 底下只有本批的 54 / 55 / 56 三條 lane(本票沒有多開、
也沒有收掉別人的)。

固化在 `batch.py --self-check`(步驟 1 已綠)的 mutation 測試:`CONFLICT_LINES` 咬「呼叫
`/resolving-merge-conflicts`」「`git log -S`」「`git branch --list 'batch/*' --contains`」
「worktree 與 branch 都留著」「`git merge --abort`」五句,任一句從 SKILL.md 消失就紅;
`forced_merge_issue` 在 bash block 裡貼一行 `--force` / `-X ours` / `-X theirs` / `push -f` /
`reset --hard` 就紅;`_two` / `_files` / `_how` / `_stopped_headline` 在票號數不對、沒給檔案、
`how` 是多行或帶衝突標記時直接 `SystemExit`,不讓半殘的句子貼上票。

## 判定

覆蓋驗收項一條,pass。無 blocking。

未涵蓋:rename/rename 這種撞法(§7a 兩條認票路都沒對它實測過);`/resolving-merge-conflicts` 原件本身的解題品質(本輪它真的被叫起來解了一次,但
「它解得多好」是它自己的驗收範圍,不是本票的);以及在真的多 lane GitHub 批次裡跑完整條
§6→§9(本票只驗撞車那一段,整條路是 #53 的範圍)。
