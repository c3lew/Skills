---
name: build-batch
description: 一批彼此不卡的票一次跑完 — 算出「要開(最多 3 張)/ 排隊 / 還卡著」名單等 client 點頭,點頭後每張各自在獨立 git worktree 平行跑 build + QA,綠的依序合回主線、整批再驗一次,交棒 client-demo;有票沒過 QA 就好的先收、沒過那張留在自己工作區繼續修。當一份 spec 切完票、想一次推進多張彼此不卡的票時使用;只有一張能跑就指路單張 /build。
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

有 lane 沒過 QA 是接上的(§7.5:好的先收,壞的留在旁邊修)。**merge 撞車、能開的超過 3 張要排隊** — 這兩件事還沒接上,遇到就停下來把現況講給 client 聽,不要自己發明處置。

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

一條 lane 沒綠(`/build` 或 `/qa` 任一沒過)**不拖別條** — 記下它的票號,別的 lane 照跑到完。處置在 §7.5,現場什麼都不要收。

## 7. 依序合回主線

全部 lane 都跑完了才進這一段(綠的、沒綠的都跑完),而且**一張一張**合、不同時 — 同時 merge 撞在一起會留下一個沒人看得懂的中間狀態。

先把整批餵進去,拿到「哪幾張要合、哪幾張留著」,不要自己從三張裡挑兩張:

```bash
python <skill dir>/batch.py <<'JSON'
{"mode": "split", "numbers": [47, 48, 42], "fixing": [48],
 "titles": {"47": "...", "48": "...", "42": "..."}}
JSON
```

`numbers` 是整批,`fixing` 是沒過 QA 的那幾張。印出來的「已收」那段就是合併佇列,照它的順序、回到主 repo,每張:

```bash
git merge --no-ff batch/47
git push
git worktree remove .git/batch-worktrees/47
```

`git push` 要當場綠再合下一張。這條 lane 到這裡就結束了,工作區當場回收 — 三份完整 checkout 沒必要一路佔到整批跑完。**branch 留著**到票結案。

撞車不在本版範圍 — 停下來把哪兩張撞在哪個檔案講給 client 聽,不要硬推。

## 7.5 沒過的那張留在旁邊修

「已收」那幾張照 §7 收完之後,對「還在修」那幾張做三件事 — 一件都不能省:

1. **沒過 QA 那張的 worktree 與 branch 都留著,不 remove**。§7 那行 `git worktree remove` 只對已收的 lane 跑。client 回頭要接著修的就是那份 checkout,收掉他就得從頭再開一次。
2. **票上留一則 comment**,寫明它沒過、還在修、東西放在哪,結尾指路回 `/build`:

```bash
python <skill dir>/batch.py <<'JSON' | gh issue comment 48 --body-file -
{"mode": "fixing", "number": 48, "numbers": [47, 48, 42], "fixing": [48],
 "titles": {"48": "..."}}
JSON
```

3. **不要在這裡重跑 `/build` 或 `/qa`**。這條 lane 的下一棒是 client 自己決定什麼時候接,批次只負責把它安全地留在原地。

**全部 lane 都沒過 → 一張都不合**:不 merge 任何東西、不 push、主線一個 commit 都不動,每張各自留 worktree + branch + 票上 comment,然後跳到 §9 印收尾那一行就結束 — 不跑 §8,也不指路 demo。留半套(合了一半、或收了工作區卻沒合)比什麼都不做更難救。

## 8. 整批驗證

三個 lane 各自綠不蘊含合起來綠(語意衝突、共用檔案的互相假設)。這是平行化唯一真正新增的風險,所以合完之後在主線上再跑一次:

1. regression suite。
2. 已合併那幾張的「覆蓋驗收項」聯集 — 每張票 body 的 `## 覆蓋驗收項` 段,去重後的清單。這份清單跟 §9 批次總結裡列的是同一份;兩邊對不起來就是有一條沒驗到。

**整批驗證只涵蓋已合併那幾張的覆蓋驗收項** — 還在修那張的不進來。它的東西根本沒上主線,把它的驗收項算進去必定紅,好的那幾張也就跟著收不進去。範圍縮這件事不用自己記:§9 那段 `"mode": "summary"` 吃的是整批 + `fixing`,聯集由 `batch.py` 自己挑,印出來的那份就是這一關要驗的那份。

綠了才往下。紅了停下來報給 client,不要往 demo 送。

## 9. 收尾

整批驗證綠 → 終端機印最後一行:

```bash
python <skill dir>/batch.py <<'JSON'
{"mode": "merged", "numbers": [47, 48, 42], "spec": 51, "fixing": [48],
 "titles": {"48": "..."}}
JSON
```

`fixing` 空著就是全綠那一行(「3 張已合併,下一步 demo」);有東西就變成「2 張已合併可以 demo,#48 還在修」,後面接那張的工作區、branch 與它的下一棒。全部都沒過的時候它印的是「一張都沒合、主線沒動」,而且不指路 demo — 沒東西可以 demo。

每張票上的產出紀錄由 lane 內的 `/build` 自己寫完了(它本來就會 push 完再貼 commit link),這裡不重複寫。spec 票上再留一則批次總結:

```bash
python <skill dir>/batch.py <<'JSON' | gh issue comment 51 --body-file -
{"mode": "summary", "numbers": [47, 48, 42], "spec": 51, "fixing": [48],
 "titles": {"47": "...", "48": "...", "42": "..."},
 "coverage": {"47": ["#47 覆蓋的驗收項原句"],
              "48": ["#48 覆蓋的驗收項原句"],
              "42": ["#42 覆蓋的驗收項原句"]}}
JSON
```

`coverage` 拿票號當 key、整批的都給 — 哪幾條算進聯集由 `fixing` 決定,不用自己先把還在修那張的挑掉(挑漏了就是 §8 驗到一條沒上主線的東西)。有 lane 沒過時這則總結會自己分「已收 / 還在修」兩段。

`<<'JSON'` 寫在 `|` 之前,整段連結尾的 `JSON` 一起複製。

已收那幾張的工作區在 §7 一張一張回收掉了,還在修那幾張照 §7.5 留著,這裡都不用再動。要確認收得對不對,母體只有 `.git/batch-worktrees/` 底下這幾個(路徑同 §7)— 只問這個母體,順便確認 branch 照 §7 留著:

```bash
git worktree list --porcelain | grep -F /.git/batch-worktrees/   # 只剩「還在修」那幾張
git branch --list 'batch/*'                                      # 應該還列得出來
```

第一行印出來的那幾列要**正好**是「還在修」那幾張(全綠時就是沒有輸出,`grep` 回 exit 1,正常):多出來的是沒走完 §7 的 lane,照 §7 的 `git worktree remove` 收掉再往下;少掉的更糟 — 那是把 client 要接著修的 checkout 收掉了,照 §6 的 `git worktree add` 重開一份。第二行反過來要**有**輸出 — `batch/*` 空掉表示有人連 branch 一起刪了,§7 明寫 branch 留著到票結案。兩行合起來才是「worktree 移除、branch 保留」這條驗收原句的判準,只跑第一行等於只驗了一半。

判準只看 `.git/batch-worktrees/` 這個母體、不看 `git worktree list` 的列數,因為完整輸出是整個 repo 的所有 worktree,包含別人開的 — 例如 Claude Code 給 subagent 常駐的 `.claude/worktrees/agent-*`,跟 `/build-batch` 無關卻一直住在這裡。#53 的 QA 實錄(步驟 6):0 個 lane 殘留,`git worktree list` 還是印 4 列(1 列主 repo + 3 列 subagent worktree),拿「只剩主 repo」判就是紅的;反過來真的殘留 1 條時,那一列混在同樣的 4 列裡也認不出來(#61)。

也不要退回 `ls .git/batch-worktrees`:在 linked worktree 底下 `.git` 是檔案不是目錄,`ls` 直接報錯(被 `2>/dev/null` 一吃就是假綠),而「註冊還在、目錄先沒了」的 lane 它根本看不到。問 git 的版本這兩種都答得對,而且 git 自己失敗(cwd 不在 repo 裡)會把 `fatal:` 印在 stderr 上,看得見 — 不像被重導掉的 `ls`。

## Codex 端

`$build-batch` 走完全一樣的 §1–§4,印完名單與建議順序就結束 — **不開 worktree、不平行**。Codex 端拿到的是「這幾張彼此不卡,順序是 #A → #B → #C,一張一張跑 `$build #A`」,不是半殘的平行版。
