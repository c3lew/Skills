---
name: build-batch
description: 一批彼此不卡的票一次跑完 — 算出「要開(最多 3 張)/ 排隊 / 還卡著」名單等 client 點頭,點頭後每張各自在獨立 git worktree 平行跑 build + QA,全綠依序合回主線、整批再驗一次,交棒 client-demo。當一份 spec 切完票、想一次推進多張彼此不卡的票時使用;只有一張能跑就指路單張 /build。
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

本版只走全綠路徑。**有票 QA 沒過、能開的超過 3 張要排隊** — 這兩件事還沒接上,遇到就停下來把現況講給 client 聽,不要自己發明處置。merge 撞車已經接上了(§7a–§7c):解得掉 agent 自己解,解不掉停下整個合併階段講清楚哪兩張撞在哪個檔案。

## 6. 平行開工

「要開」名單上每張票各自一個 git worktree — lane 之間是檔案系統層級隔離,不共用工作目錄,所以不可能互相把對方寫到一半的東西吃進去。branch 與工作區路徑由 [`batch.py`](batch.py) 算,不要自己拼:

```bash
python <skill dir>/batch.py <<'JSON'
{"mode": "start", "numbers": [47, 48], "titles": {"47": "...", "48": "..."}}
JSON
```

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

## 7. 依序合回主線

全部 lane 綠了才進這一段,而且**一張一張**合、不同時 — 同時 merge 撞在一起會留下一個沒人看得懂的中間狀態。回到主 repo,照「要開」的順序,每張:

```bash
git merge --no-ff batch/47
git push
git worktree remove .git/batch-worktrees/47
```

`git push` 要當場綠再合下一張。這條 lane 到這裡就結束了,工作區當場回收 — 三份完整 checkout 沒必要一路佔到整批跑完。**branch 留著**到票結案。

### 7a. 撞車:先查出「跟誰撞」

`git merge` 紅了就是撞車。因為是一張一張合,衝突一次只會發生在一張票上 — 正在合的那張,跟這批裡先合進去、動到同一段的那張。兩張都要查出來:少了任何一張,票上的紀錄跟終端機那句都寫不出來。

```bash
git diff --name-only --diff-filter=U                    # 撞在哪些檔案
git diff -- <撞到的檔案>                                 # 衝突兩側各是什麼內容
git log -S'<主線那側的那段內容>' --format=%h -1 HEAD --not MERGE_HEAD -- <撞到的檔案>
git branch --list 'batch/*' --contains <上一行給的 sha>   # 那顆 commit 屬於哪條 lane
```

第三行問的是「主線這側那段文字是哪一顆 commit 寫進來的」,第四行把那顆 commit 換算成 lane,branch 名字後半就是另一張的票號。

**不要**改用「最近一次動到這個檔案的 merge」去猜:同一個檔案這批裡常有第三張乾淨地動過(改的是別的段落),那個問法會回報第三張的票號 — 撞的明明是另一張,client 讀到的卻是錯的票。`-S` 問的是「那段文字」而不是「那個檔案」,所以第三張插在中間也不會被誤認(QA 步驟 4 有並排實測)。

`--not MERGE_HEAD` 把正在合的那張排掉,剩下的才是主線這側;`--contains` 用 git 自己的 commit 歸屬回答,不靠 parse merge 訊息。

查不出來(那段內容不是這批任何一條 lane 寫的,例如檔案是主線本來就有的)就不要猜票號,直接走 §7c 停下來 — `conflict-stopped` 的 `numbers` 只給正在合的那一張,印出來的話會照實講「跟主線上既有的內容撞」。

### 7b. 解得掉:自己解,不打擾 client

呼叫既有的 `/resolving-merge-conflicts` 原件解。它是唯一的解法來源 — 不自己 `-X ours` / `-X theirs` 挑一邊蓋過去,不強推,不砍 branch 重來。那三招都不是解衝突,是把其中一張票的工作丟掉,而且丟掉的當下沒有人看得見。

解掉之後把 merge commit 收掉、`git push`,然後在**兩張**相關的票上各留同一行白話紀錄:

```bash
note=$(python <skill dir>/batch.py <<'JSON'
{"mode": "conflict-resolved", "numbers": [48, 47],
 "titles": {"48": "...", "47": "..."},
 "files": ["<撞到的檔案>"], "how": "<一句白話:怎麼解的>"}
JSON
)
echo "$note" | gh issue comment 48 --body-file -
echo "$note" | gh issue comment 47 --body-file -
```

`numbers` 第一個是正在合的那張,第二個是先合進去的那張;`how` 用 client 看得懂的話寫「兩邊各加了什麼、最後怎麼擺」,不要貼 diff。

貼完就回 §7 繼續合下一張 — 撞車解掉不是需要 client 決定的事,不停、不問。

### 7c. 解不掉:停下整個合併階段

`/resolving-merge-conflicts` 也收不掉的時候(兩張票對同一段做了互斥的決定,誰對誰錯要 client 說了算),停下整個合併階段。停之前先把工作區弄乾淨 — 把這次沒合完的 merge 退掉,主線留在「上一張合完」的樣子,不要留一個帶衝突標記的 index 給 client:

```bash
git merge --abort
```

已經合成功並 push 的留在主線,不 revert、不 reset;還沒合的 lane **worktree 與 branch 都留著**,不 `git worktree remove`、不刪 branch — client 決定怎麼處理之後,那些 lane 要能原地接著跑。

然後印給 client,同一份也貼到撞在一起的那兩張票上:

```bash
note=$(python <skill dir>/batch.py <<'JSON'
{"mode": "conflict-stopped", "numbers": [48, 47],
 "titles": {"48": "...", "47": "...", "42": "...", "49": "..."},
 "files": ["<撞到的檔案>"], "merged": [42, 47], "pending": [48, 49]}
JSON
)
echo "$note"
echo "$note" | gh issue comment 48 --body-file -
echo "$note" | gh issue comment 47 --body-file -
```

`merged` 是已經合進主線的(照合的順序),`pending` 是還沒合的(含撞車失敗的那張)。印完就結束,§8 之後都不跑 — 這批沒有全部進主線,整批驗證與 demo 都還不成立。

## 8. 整批驗證

三個 lane 各自綠不蘊含合起來綠(語意衝突、共用檔案的互相假設)。這是平行化唯一真正新增的風險,所以合完之後在主線上再跑一次:

1. regression suite。
2. 這批**所有票**的「覆蓋驗收項」聯集 — 每張票 body 的 `## 覆蓋驗收項` 段,去重後的清單。這份清單跟 §9 批次總結裡列的是同一份;兩邊對不起來就是有一條沒驗到。

綠了才往下。紅了停下來報給 client,不要往 demo 送。

## 9. 收尾

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

工作區已經在 §7 一張一張回收掉了,這裡不用再收。要確認有沒有漏收,母體只有 `.git/batch-worktrees/` 底下這幾個(路徑同 §7)— 只問這個母體,順便確認 branch 照 §7 留著:

```bash
git worktree list --porcelain | grep -F /.git/batch-worktrees/   # 應該沒有輸出
git branch --list 'batch/*'                                      # 應該還列得出來
```

第一行沒有輸出(`grep` 回 exit 1,正常)就是工作區收乾淨了;印出來的每一列就是一條沒走完 §7 的 lane,照 §7 的 `git worktree remove` 收掉再往下。第二行反過來要**有**輸出 — `batch/*` 空掉表示有人連 branch 一起刪了,§7 明寫 branch 留著到票結案。兩行合起來才是「worktree 移除、branch 保留」這條驗收原句的判準,只跑第一行等於只驗了一半。

判準只看 `.git/batch-worktrees/` 這個母體、不看 `git worktree list` 的列數,因為完整輸出是整個 repo 的所有 worktree,包含別人開的 — 例如 Claude Code 給 subagent 常駐的 `.claude/worktrees/agent-*`,跟 `/build-batch` 無關卻一直住在這裡。#53 的 QA 實錄(步驟 6):0 個 lane 殘留,`git worktree list` 還是印 4 列(1 列主 repo + 3 列 subagent worktree),拿「只剩主 repo」判就是紅的;反過來真的殘留 1 條時,那一列混在同樣的 4 列裡也認不出來(#61)。

也不要退回 `ls .git/batch-worktrees`:在 linked worktree 底下 `.git` 是檔案不是目錄,`ls` 直接報錯(被 `2>/dev/null` 一吃就是假綠),而「註冊還在、目錄先沒了」的 lane 它根本看不到。問 git 的版本這兩種都答得對,而且 git 自己失敗(cwd 不在 repo 裡)會把 `fatal:` 印在 stderr 上,看得見 — 不像被重導掉的 `ls`。

## Codex 端

`$build-batch` 走完全一樣的 §1–§4,印完名單與建議順序就結束 — **不開 worktree、不平行**。Codex 端拿到的是「這幾張彼此不卡,順序是 #A → #B → #C,一張一張跑 `$build #A`」,不是半殘的平行版。
