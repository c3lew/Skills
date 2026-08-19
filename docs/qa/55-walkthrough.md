# QA walkthrough — #55 build-batch 4/6:撞車 — agent 自己解,解不掉停下來講清楚

第 5 輪。前四輪各被獨立 judge 打回一次,打回的都修進受測物了:

- 第 1 輪:§7a 查「跟誰撞」的指令安靜回空的。
- 第 2 輪:「agent 自己解掉」是 QA 代打、「票上留一行紀錄」只 `echo` 沒真的貼票;另外
  §7a 會在「第三張乾淨動過同一個檔案」時報出錯的票號,而「查不出另一張」那條路在工具端
  是死路。
- 第 3 輪:§7a 遇到 modify/delete(一張刪檔、一張改同檔)問不出東西,會對 client 講一句
  假話(「跟主線上既有的內容撞」)並漏掉第二張票號。
- 第 4 輪:同一個病的第三種觸發 — 圖檔(binary)撞車沒有內容可讀,整個 class 無路可走;
  而且兩張票剛好各自加了同一句 boilerplate 時,內容鑑識會靜靜報出錯的票號。

第 4 輪之後把認票整個換掉:**不再讀內容**,改問「這批裡誰自己動過這個檔案」
(`git merge-base` + `git diff --name-only`)。這是撞法無關的問法 — 文字、圖檔、刪檔、
改名都答得出來,而且不會被第三張乾淨的票搶走。只有候選多於一條時才回頭看內容
(`git blame` 那一行),分不出來就把候選全列出來,不挑一張講死。

本輪的證據全部重新產生。

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
command substitution 層級、shell function 內部每一次迴圈、git 自己的 `+ batch/48`(branch
被別的 worktree checkout 的原生標記)全部照實出現,順序就是真的執行順序(stdout 與 stderr
合流)。整段原封不動貼上,沒有摺疊、沒有省略號。兩處轉換:scratchpad 的長路徑統一縮寫成
`…/scratchpad`;Windows 每寫一次檔就噴一行的 `warning: LF will be replaced by CRLF` 用
`grep -v '^warning:'` 濾掉。開場建 repo / 建 lane 的準備動作跑在 `set -x` 之前(那是佈景),
所以實錄從「§7 開始一張一張合」那一行起跳。

判定 oracle = 票上「覆蓋驗收項」原句:

> 兩張改到同一個檔案撞車 → agent 自己解掉,票上留一行紀錄;解不掉就停下來,講清楚哪兩張撞在哪個檔案。

一鍵重開:

```bash
cd "D:/Self Project/Skills/.git/batch-worktrees/55"
bash …/scratchpad/reg.sh        # 步驟 1:regression
bash …/scratchpad/qa55e-1.sh    # 步驟 2:撞車 + §7a 認票(跑完停在 conflict,等 agent 解)
bash …/scratchpad/qa55e-2.sh    # 步驟 3:驗解出來的結果 + 貼票 + 流程繼續(會真的貼 GitHub)
bash …/scratchpad/qa55f.sh      # 步驟 4:解不掉 → 停下
bash …/scratchpad/qa55g.sh      # 步驟 5:四種撞法的認票
bash …/scratchpad/clean.sh      # 步驟 6:清場
```

步驟 2 與 3 中間夾的是一個獨立 subagent(它呼叫 `/resolving-merge-conflicts` 解衝突),
那一段不是 script,見步驟 2 末尾。

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

佈景是四條 lane 的一批:`docs/notes.md` 有「待辦」與「附註」兩段,lane 47 改待辦、
lane 42 改附註(同一個檔案、不同段,乾淨)、lane 48 也改待辦(跟 47 必撞)、lane 49 改別的
檔案。照 §7 的順序 47 → 42 → 48 → 49 一張一張合。**42 是故意擺在中間的**:它讓「這批裡動過
這個檔案的」不只一條,逼 §7a 走到第二段(`git blame`)。

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
+ cands batch/48 docs/notes.md
++ git branch --list 'batch/*' '--format=%(refname:short)'
+ for lane in $(git branch --list 'batch/*' --format='%(refname:short)')
+ '[' batch/42 = batch/48 ']'
++ git merge-base batch/42 batch/48
+ base=75185a848fe971ea7f5a088810b6f1cdcdb1107d
++ git diff --name-only 75185a848fe971ea7f5a088810b6f1cdcdb1107d batch/42 -- docs/notes.md
+ '[' -n docs/notes.md ']'
+ echo batch/42
batch/42
+ for lane in $(git branch --list 'batch/*' --format='%(refname:short)')
+ '[' batch/47 = batch/48 ']'
++ git merge-base batch/47 batch/48
+ base=75185a848fe971ea7f5a088810b6f1cdcdb1107d
++ git diff --name-only 75185a848fe971ea7f5a088810b6f1cdcdb1107d batch/47 -- docs/notes.md
+ '[' -n docs/notes.md ']'
+ echo batch/47
batch/47
+ for lane in $(git branch --list 'batch/*' --format='%(refname:short)')
+ '[' batch/48 = batch/48 ']'
+ continue
+ for lane in $(git branch --list 'batch/*' --format='%(refname:short)')
+ '[' batch/49 = batch/48 ']'
++ git merge-base batch/49 batch/48
+ base=75185a848fe971ea7f5a088810b6f1cdcdb1107d
++ git diff --name-only 75185a848fe971ea7f5a088810b6f1cdcdb1107d batch/49 -- docs/notes.md
+ '[' -n '' ']'
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
  
++ git blame -l HEAD -- docs/notes.md
++ grep -F '47 加的'
++ cut '-d ' -f1
++ tr -d '^'
+ sha=8283250bdf2c23ed78f2c5e70e7199e48e135eb3
+ git branch --list 'batch/*' --contains 8283250bdf2c23ed78f2c5e70e7199e48e135eb3
  batch/47
```

- 撞車真的發生:`CONFLICT (content): Merge conflict in docs/notes.md`,exit 1。
- §7a 第一段(那個 for 迴圈)問「這批裡誰自己動過 `docs/notes.md`」→ 印出 `batch/42` 與
  `batch/47` 兩條;`batch/49` 沒動過它,迴圈裡的 `[ -n '' ]` 就是它被跳過的那一行。
- 候選有兩條,所以走第二段:`git blame` 主線那側衝突的那一行 → sha → `--contains` →
  **`batch/47`**,不是中間那張 42。

**接下來這一步不是 QA 做的**:把這個卡住的 repo 交給一個獨立 subagent,只告訴它「這裡有一個
進行中的 merge conflict,呼叫 `resolving-merge-conflicts` skill 解掉」,並明講禁止
`--abort` / `--force` / `-X ours|theirs` / `reset --hard`。它回報的原話(節錄它自己的判斷):

> **(1) 呼叫的 skill**:`resolving-merge-conflicts`(Skill tool)。
>
> **(2) 怎麼判斷該怎麼解**:… 比對三方內容:base 的 `## 待辦` 是 `- 舊的待辦`;47 把它換成
> 「寫 QA 實錄」,48 把它換成「補交棒 comment」。也就是兩邊都在做同一件事 —— 各自往待辦清單
> 加自己那批的項目 … 兩邊意圖不衝突,只是動到同一行才 conflict。所以照 skill 的
> 「preserve both intents where possible」:兩條待辦都留,順序按批次 47 → 48。`## 附註` 那段
> 的 `42 加的:附註改寫` 不在 conflict 區,原樣保留 … 全程沒用 `--abort` / `--force` /
> `-X ours|theirs` / `reset --hard`,沒 push。

QA 自己沒有動過任何一個字元 — 下一步是拿它的結果來驗。

## 步驟 3 — 解掉之後:紀錄貼上票、流程繼續

```text
+ git log --oneline -4
6210999 Merge branch 'batch/48'
f9c12ed Merge branch 'batch/42'
e5acc12 Merge branch 'batch/47'
6a07014 48
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
https://github.com/c3lew/Skills/issues/55#issuecomment-5339109569
+ echo '撞車已解:#9048 補交棒 comment 跟 #9047 寫 QA 實錄 都改到 docs/notes.md — 兩張加的是各自獨立的待辦、不是二選一,所以兩條都留著,照 9047 → 9048 的順序擺。合併照常繼續,不用你處理。'
+ gh issue comment 55 --repo c3lew/Skills --body-file -
https://github.com/c3lew/Skills/issues/55#issuecomment-5339109772
+ git merge -q --no-ff --no-edit batch/49
+ git push -q
+ git worktree remove .git/batch-worktrees/48
+ git worktree remove .git/batch-worktrees/49
+ git log --oneline --graph -8
*   7904dc2 Merge branch 'batch/49'
|\  
| * 971f079 49
* |   6210999 Merge branch 'batch/48'
|\ \  
| * | 6a07014 48
| |/  
* |   f9c12ed Merge branch 'batch/42'
|\ \  
| * | 4b55d97 42
| |/  
* |   e5acc12 Merge branch 'batch/47'
|\ \  
| |/  
|/|   
| * 8283250 47
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

- **「agent 自己解掉」**:`git log --oneline -4` 的 `Merge branch 'batch/48'` 是 subagent 收的
  merge commit,`git status --short` 空、`git diff --check` 沒話講;`cat docs/notes.md` 兩張的
  待辦都在,42 的附註也還在,沒有衝突標記。
- **「票上留一行紀錄」**:`conflict-resolved` 的輸出經 `gh issue comment` 真的貼上 GitHub,
  兩則 comment 的 URL 在輸出裡(#55 上點得開)。票號用 `#9047` / `#9048` 這種不存在的號碼,
  是為了不去騷擾這批真的在跑的票 — 走的路徑與命令完全是 §7b 的原句。
- **「不打擾 client、流程繼續」**:緊接著 `Merge branch 'batch/49'` 照常合完,中間沒有停下來問。
- 收尾:`git status --porcelain` 空、lane 工作區沒有殘留、`batch/*` 四條 branch 都還在。

## 步驟 4 — 解不掉:停下整個合併階段

兩張對同一條待辦做了互斥的決定(47 說「只留 47 這條」、48 說「只留 48 這條」),
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
+ cands batch/48 docs/notes.md
++ git branch --list 'batch/*' '--format=%(refname:short)'
+ for lane in $(git branch --list 'batch/*' --format='%(refname:short)')
+ '[' batch/47 = batch/48 ']'
++ git merge-base batch/47 batch/48
+ base=e9455f4318ce13d8d055c7b73aa2bd8db00e3fa0
++ git diff --name-only e9455f4318ce13d8d055c7b73aa2bd8db00e3fa0 batch/47 -- docs/notes.md
+ '[' -n docs/notes.md ']'
+ echo batch/47
batch/47
+ for lane in $(git branch --list 'batch/*' --format='%(refname:short)')
+ '[' batch/48 = batch/48 ']'
+ continue
+ for lane in $(git branch --list 'batch/*' --format='%(refname:short)')
+ '[' batch/49 = batch/48 ']'
++ git merge-base batch/49 batch/48
+ base=e9455f4318ce13d8d055c7b73aa2bd8db00e3fa0
++ git diff --name-only e9455f4318ce13d8d055c7b73aa2bd8db00e3fa0 batch/49 -- docs/notes.md
+ '[' -n '' ']'
+ git merge --abort
+ git status --porcelain
+ git log --oneline -1
0546a3a Merge branch 'batch/47'
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
  這條同時被 `batch.py` 的 `forced_merge_issue` 咬在文件那一面(見步驟 6)。

## 步驟 5 — 四種撞法,同一個認票法

**甲**:文字撞車,而且第三張(42)乾淨地動過同一個檔案 — 兩張票還各自加了同一句 boilerplate
`- [ ] 待補說明`(第 4 輪 judge 就是用這招把內容鑑識騙過去的)。**乙**:圖檔(binary)撞車。
**丙**:一張刪檔、一張改同一個檔案(modify/delete)。**丁**:主線那側是主線自己的 commit 改的。

```text
########## 甲:47 撞、42 乾淨、兩張都動過同一檔(還共用同一句 boilerplate)
Auto-merging notes.md
-- 候選(檔案層級):
batch/42
batch/47
-- blame 主線那側那一行:
a85b65e3 (Q 2026-08-19 15:49:01 +0800 2) - 47 加的
+ batch/47
-- 舊方法 -S(judge 說會被搶走):
a1651e2 42

########## 乙:binary 撞車
Auto-merging logo.bin
UU logo.bin
-- 候選(檔案層級):
batch/47

########## 丙:modify/delete
DU notes.md
-- 候選(檔案層級):
batch/47

########## 丁:主線自己改的(不是這批)
-- 候選(檔案層級):
(以上應為空)
撞車停下:#48 補交棒 comment 跟主線上既有的內容撞在 notes.md,自己解不掉 — 這批合併停在這裡,等你決定。

已經合進主線的(0 張):
  (無)

還沒合的(1 張),工作區與 branch 都留著:
  #48 補交棒 comment — .git/batch-worktrees/48(branch batch/48)

沒有猜、沒有強推,也沒有把任何一邊蓋掉。
```

- 甲:候選 = `batch/42` + `batch/47`,`git blame` 那一行 → **`batch/47`**,對的。同一份佈景下
  舊的內容鑑識法(`git log -S'- [ ] 待補說明'`)回的是 **`42`** — 錯的票號,而且錯得完全看不
  出來。兩個問法並排跑在同一個 conflict 上。
- 乙:`git status` 是 `UU`,`git diff` 只會說 `Binary files differ`(沒有內容可讀);候選法
  照樣回 **`batch/47`**。圖檔不可能被兩張票乾淨共改,所以這一類永遠只會有一條候選。
- 丙:`git status` 是 `DU`,主線那側整個檔案被刪掉了;候選法照樣回 **`batch/47`**。
- 丁:候選是空的 — 這才算真的查不出另一張票。這時候 `numbers` 只給正在合的那一張,印出來是
  「**#48 補交棒 comment 跟主線上既有的內容撞在 notes.md**」,不猜票號。

## 步驟 6 — 清場

```text
+ rm -rf …/scratchpad/qa55e …/scratchpad/qa55e-remote.git …/scratchpad/qa55f …/scratchpad/qa55f-remote.git
+ ls …/scratchpad
+ grep -E '^qa55|^probe|^reg|^clean'
clean.out
clean.sh
qa55e-1.out
qa55e-1.sh
qa55e-2.out
qa55e-2.sh
qa55f.out
qa55f.sh
qa55g.out
qa55g.sh
reg.out
reg.sh
+ cd 'D:/Self Project/Skills/.git/batch-worktrees/55'
+ git status --porcelain
 M skills/build-batch/SKILL.md
 M skills/build-batch/batch.py
+ git worktree list --porcelain
```

scratchpad 只剩本輪六支 `.sh` 與它們的 `.out`(重跑用),臨時 repo 全刪;受測物 worktree 只有
本票要改的兩個檔;`.git/batch-worktrees/` 底下只有本批的 54 / 55 / 56 三條 lane(本票沒有多開、
也沒有收掉別人的)。

固化在 `batch.py --self-check`(步驟 1 已綠)的 mutation 測試:`CONFLICT_LINES` 咬「呼叫
`/resolving-merge-conflicts`」「`git merge-base`」「`git branch --list 'batch/*' --contains`」
「worktree 與 branch 都留著」「`git merge --abort`」五句,任一句從 SKILL.md 消失就紅;
`forced_merge_issue` 在 bash block 裡貼一行 `--force` / `-X ours` / `-X theirs` / `push -f` /
`reset --hard` 就紅;`_who` / `_files` / `_how` 在連正在合的那張都沒給、沒給檔案、`how` 是多行
或帶衝突標記時直接 `SystemExit`,不讓半殘的句子貼上票。

## 判定

覆蓋驗收項一條,pass。無 blocking。

未涵蓋:rename/rename 撞法(候選法對它成立 — 它問的是檔案不是內容 — 但沒實測);
submodule 撞車(同上,沒實測);`conflict-stopped` 的貼票只有 `echo`,真的 `gh issue comment`
是在步驟 3 用 `conflict-resolved` 跑的(同一條命令路徑);`/resolving-merge-conflicts` 原件
本身的解題品質(本輪它真的被叫起來解了一次,但「它解得多好」是它自己的驗收範圍);
以及在真的多 lane GitHub 批次裡跑完整條 §6→§9(本票只驗撞車那一段)。
