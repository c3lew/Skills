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

本版只走全綠路徑。**有票 QA 沒過、merge 撞車、能開的超過 3 張要排隊** — 這三件事都還沒接上,遇到就停下來把現況講給 client 聽,不要自己發明處置。

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

撞車不在本版範圍 — 停下來把哪兩張撞在哪個檔案講給 client 聽,不要硬推。

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

工作區已經在 §7 一張一張回收掉了,這裡不用再收。`git worktree list` 應該只剩主 repo — 沒剩乾淨就是有 lane 沒走完 §7,回頭查。

## Codex 端

`$build-batch` 走完全一樣的 §1–§4,印完名單與建議順序就結束 — **不開 worktree、不平行**。Codex 端拿到的是「這幾張彼此不卡,順序是 #A → #B → #C,一張一張跑 `$build #A`」,不是半殘的平行版。
