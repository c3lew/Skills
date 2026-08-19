---
name: build-batch
description: 一批彼此不卡的票一次跑完 — 算出「要開(最多 3 張)/ 排隊 / 還卡著」名單等 client 點頭,點頭後每張各自在獨立 git worktree 平行跑 build + QA,做完一張從佇列補一張,中斷可續跑,全綠依序合回主線、整批再驗一次,交棒 client-demo。當一份 spec 切完票、想一次推進多張彼此不卡的票時使用;只有一張能跑就指路單張 /build。
---

# build-batch

**點頭之前什麼都不動** — 不開 worktree、不改任何檔案、不碰票。這一步只做一件事:把「誰現在能開」算出來給 client 看。他說不,就乾淨結束,沒有殘留。

用法:`/build-batch #<spec 票號>`。

## 1. 抓票

```bash
gh issue list --state all --limit 200 --json number,state,body,labels,title
```

候選是 **open、帶 `ready-for-agent`、且 body 的 `## Parent` 指向這份 spec** 的票。批次只在同一份 spec 切出來的票之間算 — 跨 spec 不湊票,所以 spec 票號是必要的:沒給就先印出「目前有 open `ready-for-agent` 票的 spec」清單問 client 是哪一份,不要自己掃全部票湊一批。

closed 的票不進候選,但要留在餵進去的資料裡 — 它們是判斷「卡關解除了沒」的依據。

## 2. 解卡關關係

卡關關係是票上**已經宣告好的**,不新發明標記:平台原生的 sub-issue / dependency 關係優先;退回時讀 body 的 `## Blocked by` 段,抓裡面的 `#<n>`。`None — can start immediately` 這種寫法就是空 list。

## 3. 算名單、印名單

把純資料餵進 [`batch.py`](batch.py),名單的算與印都在裡面,不要自己心算或自己排版:

```bash
python <skill dir>/batch.py <<'JSON'
{"tickets": [{"number": 47, "state": "open", "blocked_by": []},
             {"number": 48, "state": "open", "blocked_by": [47]}],
 "titles": {"47": "...", "48": "..."}}
JSON
```

`<skill dir>` 就是本 SKILL.md 所在的目錄。印出來長這樣:

```
要開(3 張):
  #47 <title>
  #48 <title>
  #42 <title>
排隊(1 張):
  #50 <title>
還卡著(1 張):
  #53 <title> — 卡在 #47
```

cap 寫死 3,不做設定。blocker 已關的票會被放行;blocker 還開著、或 blocker 根本不在這份資料裡的,一律留在「還卡著」— 看不到它關了就不賭。

## 4. 兩個提早結束的岔路

- **只有 1 張能跑** → 印「沒必要開批次,用 `/build #47`(Codex: `$build #47`)就好」,結束,不問點頭。
- **0 張能跑** → 名單已經寫了每張卡在誰後面,指路先去清那些 blocker,結束。

## 5. 等點頭

名單印完停下來,明確問 client:「這幾張要一起推嗎?」

- **說不** → 乾淨結束。什麼都沒開、什麼都沒改,不用回收。
- **說好** → 往下走 §6。從這一刻起才會動到檔案。

**有票 QA 沒過、merge 撞車** — 這兩件事還沒接上,遇到就停下來把現況講給 client 聽,不要自己發明處置。能開的超過 3 張不在此列:那是 §6 的排隊補位,照跑。

## 6. 平行開工 — 最多 3 條,做完一張補一張

同時最多 3 條 lane(cap 同 §3),名單上其餘的票排隊。**排隊中的票在被開工前完全不動它** — 不開 worktree、不貼 comment、不改它一個字:它可能根本輪不到(client 中途喊停),而一張被貼過「開工」卻沒人在做的票,下一個看到的人只能靠猜。

### 6.1 先接續上一次中斷的 lane

`/build-batch` 重跑的時候,先問 git 有沒有既有的 lane — 有就是上一次中斷留下的(§7),接續它,**不重開**:

```bash
git worktree list --porcelain | grep -F /.git/batch-worktrees/
```

沒有輸出(`grep` 回 exit 1,正常)就是乾淨的一批,直接往 §6.2。有輸出就把那幾行**原封不動**貼進 `worktrees`,票號由 [`batch.py`](batch.py) 從路徑認 — 別自己讀,認錯一條就是等一下去 merge 一條根本不是這條線開的 branch:

```bash
python <skill dir>/batch.py <<'JSON'
{"mode": "resume", "worktrees": "worktree D:/repo/.git/batch-worktrees/47", "titles": {"47": "..."}}
JSON
```

```
接續 #47 <title> — 既有工作區 .git/batch-worktrees/47(branch batch/47)還在,不重開
```

接續的 lane 就是「已經在跑」的 lane:它們佔掉的名額不能再開新的。接續了幾條就當成 §6.2 的 `running` 餵進去,別自己扣。

### 6.2 開頭那幾條

開工的每張票各自一個 git worktree — lane 之間是檔案系統層級隔離,不共用工作目錄,所以不可能互相把對方寫到一半的東西吃進去。開哪幾張、branch 與工作區路徑都由 [`batch.py`](batch.py) 算,不要自己拼也不要自己扣名額:`numbers` 餵「要開 → 排隊」整份名單,`running` 餵 §6.1 接續的那幾條(沒有就 `[]`):

```bash
python <skill dir>/batch.py <<'JSON'
{"mode": "start", "numbers": [47, 48, 42, 50], "running": [], "titles": {"47": "...", "48": "..."}}
JSON
```

**印幾行就開幾個 worktree,沒印到的就是還在佇列裡**,不要照名單全開 — 接續了 2 條、名單又滿 3 張的時候,自己扣名額的版本會開出 5 條同時在跑,而那個畫面跟正常的一模一樣。

印出來的每一行就是 client 在終端機看到的「開工」,同一行也告訴你 branch 與路徑:

```
開工 #47 名單 — 工作區 .git/batch-worktrees/47(branch batch/47)
```

照那兩個值開 worktree,一張一次,開完立刻把 branch 推上去:

```bash
git worktree add .git/batch-worktrees/47 -b batch/47
git push -u origin batch/47
```

`-u` 是必要的,不是順手:lane 內的 `/build` 會 `git push`,branch 沒有 upstream 它當場失敗 — 而它貼在票上的 commit link 指的就是那些還沒推上去的 sha,在 GitHub 上是 404。

同一行也貼回該張票 — client 離開電腦回來翻票就知道它什麼時候開的:

```bash
lane='{"mode": "start", "numbers": [47], "titles": {"47": "..."}}'
echo "$lane" | python <skill dir>/batch.py | gh issue comment 47 --body-file -
```

然後每張 lane **平行**跑 — 一個 lane 一個 subagent,工作目錄就是它自己的 worktree,在裡面依序跑 `/build #47` 與 `/qa #47`,兩個都綠這條 lane 才算綠。lane 之間不互等。

一條 lane 綠了就立刻報一行,不要等整批 — 印給 client、也貼回票上:

```bash
lane='{"mode": "done", "numbers": [47], "titles": {"47": "..."}}'
echo "$lane" | python <skill dir>/batch.py                                    # 印給 client
echo "$lane" | python <skill dir>/batch.py | gh issue comment 47 --body-file -
```

### 6.3 做完一張補一張

一條 lane 結束就**立刻**從佇列補一張進來,不等其他 lane、也不管它是綠的還是紅的 — 紅的那條停在原地等 client(§5),但沒有理由讓佇列裡其他票陪它一起卡著。

補誰不要自己算。把現場事實餵進去:`running` 是這一刻還在跑的 lane(不含剛收掉的那條),`queue` 是還沒開過的票,照「要開 → 排隊」的順序:

```bash
python <skill dir>/batch.py <<'JSON'
{"mode": "refill", "running": [48, 42], "queue": [50, 51], "titles": {"50": "..."}}
JSON
```

```
補位 #50 <title> — 工作區 .git/batch-worktrees/50(branch batch/50);同時跑 3 條,佇列剩 1 張
```

印出來的每一行就是 client 在終端機看到的「補位」,同一行也告訴你 branch 與路徑 — 照 §6.2 一模一樣的三步開下去(`git worktree add` → `git push -u` → 把這一行貼回該張票),然後照 §6.2 起一個 subagent 跑 `/build` + `/qa`。

行尾那兩個數字是補完之後的狀態:`同時跑 N 條` 就是 cap 這條不變量的當場證據,client 不用自己去數 worktree。沒名額或佇列空了會印「不補位 …」,那就是等剩下的 lane 收完,不要硬開。

全部票都跑完(佇列空、沒有 lane 在跑)才往 §8。

## 7. 中斷與續跑

Ctrl-C、lane 死掉、client 喊停 — **中斷不等於全部重來**。已經 merge 的留在主線,未合併的 lane 留著 worktree 與 branch,什麼都不回收:回收掉的那幾條下次得從零跑一次,那是這條線最貴的東西。

什麼時候寫這一段:**能寫的時候就寫**。Ctrl-C 直接把 agent 打死的話這一段根本輪不到跑 — 所以下一次重跑走到 §6.1、發現有既有 lane 但票上沒有中斷紀錄,就當場補上這一行再往下,不要當作沒發生過。

每條沒合併的 lane 在自己票上留一行,client 之後翻票就知道它可以續:

```bash
lane='{"mode": "interrupted", "numbers": [47], "spec": 51, "titles": {"47": "..."}}'
echo "$lane" | python <skill dir>/batch.py                                    # 印給 client
echo "$lane" | python <skill dir>/batch.py | gh issue comment 47 --body-file -
```

```
中斷,可續 #47 <title> — 未合併,工作區 .git/batch-worktrees/47 與 branch batch/47 都留著;重跑 `/build-batch #51`(Codex: `$build-batch #51`)會接續這條 lane
```

排隊中還沒開工的票不留任何紀錄 — 它們從頭到尾沒被碰過(§6),下次重跑就是一般的候選票。

重跑就照 §6.1:偵測到既有的 `batch/*` worktree 就接續那幾條,不重開一份。

## 8. 依序合回主線

全部 lane 綠了才進這一段,而且**一張一張**合、不同時 — 同時 merge 撞在一起會留下一個沒人看得懂的中間狀態。回到主 repo,照「要開」的順序,每張:

```bash
git merge --no-ff batch/47
git push
git worktree remove .git/batch-worktrees/47
```

`git push` 要當場綠再合下一張。這條 lane 到這裡就結束了,工作區當場回收 — 三份完整 checkout 沒必要一路佔到整批跑完。**branch 留著**到票結案。

撞車不在本版範圍 — 停下來把哪兩張撞在哪個檔案講給 client 聽,不要硬推。

## 9. 整批驗證

三個 lane 各自綠不蘊含合起來綠(語意衝突、共用檔案的互相假設)。這是平行化唯一真正新增的風險,所以合完之後在主線上再跑一次:

1. regression suite。
2. 這批**所有票**的「覆蓋驗收項」聯集 — 每張票 body 的 `## 覆蓋驗收項` 段,去重後的清單。這份清單跟 §10 批次總結裡列的是同一份;兩邊對不起來就是有一條沒驗到。

綠了才往下。紅了停下來報給 client,不要往 demo 送。

## 10. 收尾

整批驗證綠 → 終端機印最後一行:

```bash
python <skill dir>/batch.py <<'JSON'
{"mode": "merged", "numbers": [47, 48, 42], "spec": 51}
JSON
```

每張票上的產出紀錄由 lane 內的 `/build` 自己寫完了(它本來就會 push 完再貼 commit link),這裡不重複寫。spec 票上再留一則批次總結:

```bash
python <skill dir>/batch.py <<'JSON' | gh issue comment 51 --body-file -
{"mode": "summary", "numbers": [47, 48], "spec": 51,
 "titles": {"47": "...", "48": "..."},
 "coverage": [["#47 覆蓋的驗收項原句"], ["#48 覆蓋的驗收項原句"]]}
JSON
```

`<<'JSON'` 寫在 `|` 之前,整段連結尾的 `JSON` 一起複製。

工作區已經在 §8 一張一張回收掉了,這裡不用再收。要確認有沒有漏收,母體只有 `.git/batch-worktrees/` 底下這幾個(路徑同 §8)— 只問這個母體,順便確認 branch 照 §8 留著:

```bash
git worktree list --porcelain | grep -F /.git/batch-worktrees/   # 應該沒有輸出
git branch --list 'batch/*'                                      # 應該還列得出來
```

第一行沒有輸出(`grep` 回 exit 1,正常)就是工作區收乾淨了;印出來的每一列就是一條沒走完 §8 的 lane,照 §8 的 `git worktree remove` 收掉再往下。第二行反過來要**有**輸出 — `batch/*` 空掉表示有人連 branch 一起刪了,§8 明寫 branch 留著到票結案。兩行合起來才是「worktree 移除、branch 保留」這條驗收原句的判準,只跑第一行等於只驗了一半。

判準只看 `.git/batch-worktrees/` 這個母體、不看 `git worktree list` 的列數,因為完整輸出是整個 repo 的所有 worktree,包含別人開的 — 例如 Claude Code 給 subagent 常駐的 `.claude/worktrees/agent-*`,跟 `/build-batch` 無關卻一直住在這裡。#53 的 QA 實錄(步驟 6):0 個 lane 殘留,`git worktree list` 還是印 4 列(1 列主 repo + 3 列 subagent worktree),拿「只剩主 repo」判就是紅的;反過來真的殘留 1 條時,那一列混在同樣的 4 列裡也認不出來(#61)。

也不要退回 `ls .git/batch-worktrees`:在 linked worktree 底下 `.git` 是檔案不是目錄,`ls` 直接報錯(被 `2>/dev/null` 一吃就是假綠),而「註冊還在、目錄先沒了」的 lane 它根本看不到。問 git 的版本這兩種都答得對,而且 git 自己失敗(cwd 不在 repo 裡)會把 `fatal:` 印在 stderr 上,看得見 — 不像被重導掉的 `ls`。

## Codex 端

`$build-batch` 走完全一樣的 §1–§4,印完名單與建議順序就結束 — **不開 worktree、不平行**。Codex 端拿到的是「這幾張彼此不卡,順序是 #A → #B → #C,一張一張跑 `$build #A`」,不是半殘的平行版。
