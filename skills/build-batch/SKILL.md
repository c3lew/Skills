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

有 lane 沒過 QA 是接上的(§7.5:好的先收,壞的留在旁邊修),merge 撞車也接上了(§7a–§7c:解得掉 agent 自己解,解不掉停下整個合併階段講清楚哪兩張撞在哪個檔案)。**能開的超過 3 張要排隊** — 這件事還沒接上,遇到就停下來把現況講給 client 聽,不要自己發明處置。

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

### 7a. 撞車:先查出「跟誰撞」

`git merge` 紅了就是撞車。對面只可能是**這批裡、已經合進主線的那幾張**之一 — 還沒輪到的 lane 不在主線上,撞不到;上一批殘留沒合成的 branch 也不在主線上,同樣撞不到。這份名單 agent 手上本來就有(「要開」的順序 + 合到第幾張),不要去問 `git branch --list 'batch/*'`:那是「所有還活著的 branch」,會把還沒合的與上一批殘留的一起撈進來,然後把一張跟這次 merge 無關的票號印給 client。

先問撞在哪些檔案:

```bash
git diff --name-only --diff-filter=U
```

再問**已合的那幾張裡誰自己動過那個檔案**。這是撞法無關的問法:文字、圖檔、刪檔、改名都答得出來,因為它只問「哪條 lane 的工作碰過這個檔案」,不去讀內容:

```bash
merged="47 42"          # 這批已經合進主線的,照 §7 的順序
current=batch/48        # 正在合的那張
file=<撞到的檔案>       # 一次只問一個檔案 — 撞到幾個就跑幾次,一個檔案一則紀錄

first=$(echo $merged | awk '{print $1}')
base=$(git merge-base "batch/$first" "$current")     # 這批共同的起點
# 正在合的那張如果把檔案改名了,對面動的是舊名字 — 兩個名字都要查
old=$(git diff --name-status -M "$base" "$current" | awk -v f="$file" '$1 ~ /^R/ && $3 == f {print $2}')
for n in $merged; do
  if [ -n "$(git diff --name-only -M "$base" "batch/$n" -- "$file" ${old:+"$old"})" ]; then echo "#$n"; fi
done
```

(`base` 是這批共同的起點:同一批的 lane 都從 §6 那一刻的主線開出來,所以任兩條的 merge-base 就是那顆。`base..lane` 只含那條 lane 自己的工作。)

印出來幾張,決定怎麼寫紀錄:

- **一張** → 就是它。(圖檔、刪檔、改名這些「不可能被兩張乾淨共改」的撞法都落在這裡。)
- **零張** → 這批已合的沒人動過它,主線那側是主線自己的 commit 改的(hotfix 之類)。不要猜票號:`conflict-resolved` / `conflict-stopped` 的 `numbers` 只給正在合的那一張,印出來會照實講「跟主線上既有的內容撞」。
- **多張** → 有第三張乾淨地動過同一個檔案(改的是別的段落)。文字檔還可以再問一次「主線那側衝突那一行是誰寫的」:

  ```bash
  git blame HEAD -- <撞到的檔案>                        # 找出衝突那一行的 sha
  git branch --list 'batch/*' --contains <那一行的 sha>   # 換算成 lane
  ```

  `--contains` 印出來的東西**只認候選名單裡的那一條** — 它問的是「哪些 branch 含這顆 commit」,上一批殘留的 branch 也會被列出來。衝突區塊還常常把沒人動過的舊行一起包進去,那時候 blame 回的是這批之前的 commit,`--contains` 就會吐出一整排 branch(QA 第 6 輪 judge 實測),那不是答案。

  分得出來(而且那條在候選名單裡)就用那一張。分不出來(圖檔沒有行可以 blame、blame 回的 commit 不在候選裡)就把候選**全部**放進 `numbers`,印出來會照實講「跟這批裡同樣改過這個檔案的 #A、#B 撞在一起」— 列出候選是誠實的,隨便挑一張講死,client 就會被指去看一張根本沒撞的票。

**不要**用「最近一次動到這個檔案的 merge 是誰」或 `git log -S'<那段內容>'` 去認票:前者會回報中間那張乾淨的票;後者問的是「這個字串的出現次數在哪顆 commit 變了」,兩張票剛好各自加了同一句 boilerplate(`- [ ] 待補說明` 這種)就會回報錯的那張,而且錯得完全看不出來(QA 步驟 5 有並排實測)。上面那個迴圈問的是「已合的哪張碰過這個檔案」,不是內容鑑識,所以沒有這種失手。

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

留置不是終點,但接下去的那一棒不在這次執行裡:client 之後跑 `/build #48` → `/qa #48`,兩個都綠之後**不要直接跳 demo** — 先回到主 repo 照 §7 那三行(`git merge --no-ff batch/48` → `git push` → `git worktree remove`)把它收回來,再照 §8 用它自己的覆蓋驗收項驗一次。沒有這一段,batch/48 跟它的工作區就永遠掛在那裡沒人收。

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
