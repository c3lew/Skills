# QA walkthrough — #54 build-batch 3/6:一張沒過 QA — 好的先收,壞的留在旁邊修

第 1 輪。走查過程抓到一條 works-but-wrong(步驟 3c),當場修掉之後整份證據重跑一次,
本檔是重跑後的版本。

環境:worktree `D:/Self Project/Skills/.git/batch-worktrees/54`,branch `batch/54`,
HEAD = `b3bc2fa`(本檔之外 working tree 乾淨)。
`python -c "import sys;print(sys.stdout.encoding)"` → `cp950`。
本票是 CLI 純函式 + skill 文件 + 一串 client 端真的會貼進終端機的 git 指令,沒有 UI、
沒有視覺 oracle,不走 Playwright;本檔是終端實錄。

**三個地方,分清楚:**

- **CLI 輸出**(步驟 3c、4、5)跑在本 worktree,只讀不寫。
- **git 那一整套**(步驟 3a、3b)跑在 scratchpad 的 clone(`…/scratchpad/qa54`、
  `…/scratchpad/qa54b`),origin 各自指向 scratchpad 的 bare repo。本 repo 與本 worktree
  沒被開過 batch worktree、沒多出 `batch/*` branch(`batch/54` 是這條 lane 自己的)、
  沒被 push 到主線,清場見步驟 6。
- **`gh` 那一段**:本票沒有新的 `gh` 實錄,理由見「未涵蓋」。

**實錄的呈現規則**:步驟 3a、3b 是各一支 script 一次跑完的輸出,**指令那幾行是 bash 自己的
xtrace 印的**(`PS4='+ '`,`set -x`),不是事後照著寫的。已知限制與 #53 相同:xtrace 不印
重導向,所以 `printf … > lane-47.md` 的 `>` 那半看不到,寫進哪個檔要靠下一行的 `git add`
反推;lane 內那三行是 subshell(`( cd … && … )`),xtrace 把它拆成逐個指令印。整段原封不動
貼上,沒有摺疊、沒有省略號。唯一的改動是把 scratchpad 的長路徑統一縮寫成 `…/scratchpad`,
以及把 `python 'D:/…/batch.py'` 縮寫成 `python batch.py`(整份檔一致),並濾掉 git 的
`LF will be replaced by CRLF` 換行警告。

判定 oracle = 票上「覆蓋驗收項」那條原句:

> 其中一張沒過 QA → 另外兩張**照樣**合回主線並告訴 client 可以 demo;沒過那張留在自己
> 工作區繼續修,票上寫著它還在修。

一鍵重開(沿用既有 CLI QA 入口):

```bash
cd "D:/Self Project/Skills"
python scripts/validate.py --self-check
python scripts/validate.py
python scripts/batch.py --self-check
python skills/build-batch/batch.py --self-check
python scripts/install.py --self-check
python scripts/hooks/triage-to-maintain.py --self-check
```

情境重演的兩支 script 留在 scratchpad(`qa54.sh` / `qa54b.sh`),用法:

```bash
bash qa54.sh  <scratchpad dir> <skills/build-batch/batch.py 的絕對路徑>
bash qa54b.sh <scratchpad dir> <skills/build-batch/batch.py 的絕對路徑>
```

---

## 步驟 1 — regression

```
$ python scripts/validate.py --self-check
OK validate self-check green
$ python scripts/validate.py
OK validate green
$ python scripts/batch.py --self-check
OK batch self-check green
$ python skills/build-batch/batch.py --self-check
OK batch self-check green
$ python scripts/install.py --self-check
OK install self-check green
$ python scripts/hooks/triage-to-maintain.py --self-check
OK triage-to-maintain self-check green
```

全綠。(`install.py --self-check` 中間會印一行 `[fixture] FAIL skills/bad: missing SKILL.md`
—— 那是它自己的 fixture 輸出,不是真的紅,#38 已經記過。)

## 步驟 2 — 情境設定

驗收原句講的是「三張裡有一張沒過」。scratchpad 開一個 bare remote + clone,照 SKILL.md §6
開三條 lane(#47、#48、#42),每條在自己的工作區做一片、push;然後宣告 **#47 綠、#42 綠、
#48 沒過 QA** —— 這就是本票要驗的那個岔路。

## 步驟 3a — 好的先收,壞的留在旁邊修(驗收原句正面)

```
+ python batch.py   (mode: start)
開工 #47 名單 — 工作區 .git/batch-worktrees/47(branch batch/47)
開工 #48 點頭 — 工作區 .git/batch-worktrees/48(branch batch/48)
開工 #42 整批 — 工作區 .git/batch-worktrees/42(branch batch/42)
+ git worktree add .git/batch-worktrees/47 -b batch/47
Preparing worktree (new branch 'batch/47')
HEAD is now at 879b264 seed
+ git push -u origin batch/47
 * [new branch]      batch/47 -> batch/47
branch 'batch/47' set up to track 'origin/batch/47'.
+ git worktree add .git/batch-worktrees/48 -b batch/48
Preparing worktree (new branch 'batch/48')
HEAD is now at 879b264 seed
+ git push -u origin batch/48
 * [new branch]      batch/48 -> batch/48
branch 'batch/48' set up to track 'origin/batch/48'.
+ git worktree add .git/batch-worktrees/42 -b batch/42
Preparing worktree (new branch 'batch/42')
HEAD is now at 879b264 seed
+ git push -u origin batch/42
 * [new branch]      batch/42 -> batch/42
branch 'batch/42' set up to track 'origin/batch/42'.
+ cd .git/batch-worktrees/47
+ printf 'lane 47\n'
+ git add lane-47.md
+ git commit -qm 'feat: 47'
+ git push -q
+ cd .git/batch-worktrees/48
+ printf 'lane 48\n'
+ git add lane-48.md
+ git commit -qm 'feat: 48'
+ git push -q
+ cd .git/batch-worktrees/42
+ printf 'lane 42\n'
+ git add lane-42.md
+ git commit -qm 'feat: 42'
+ git push -q
+ python batch.py   (mode: done)
完成 #47 名單 — build + QA 綠
完成 #42 整批 — build + QA 綠
+ python batch.py   (mode: split)
已收(2 張)— 照這個順序 merge:
  #47 名單
  #42 整批
還在修(1 張)— worktree 與 branch 都留著,不 remove:
  #48 點頭
+ git merge --no-ff -q -m 'Merge batch/47' batch/47
+ git push -q
+ git worktree remove .git/batch-worktrees/47
+ git merge --no-ff -q -m 'Merge batch/42' batch/42
+ git push -q
+ git worktree remove .git/batch-worktrees/42
+ git ls-tree --name-only origin/main
README.md
lane-42.md
lane-47.md
+ git log --oneline origin/main
a0430b5 Merge batch/42
882304e Merge batch/47
7d5208a feat: 42
00c3050 feat: 47
879b264 seed
+ python batch.py   (mode: fixing)
QA 沒過 — #48 點頭 還在修,另外 2 張已經合回主線。

工作區 `.git/batch-worktrees/48`(branch `batch/48`)保留、沒有回收 — 接著在裡面繼續修。

下一步:`/build #48`(Codex: `$build #48`)
+ python batch.py   (mode: summary)
## 批次總結(2 張已收 / 1 張還在修)

### 已收

- #47 名單 — 已合併(batch/47)
- #42 整批 — 已合併(batch/42)

### 還在修

- #48 點頭 — QA 沒過,工作區 .git/batch-worktrees/48(branch batch/48)保留,下一步:`/build #48`(Codex: `$build #48`)

整批驗證:regression + 下列覆蓋驗收項聯集(只含已收的票),全綠。

- #47 覆蓋:名單只列不卡的那 3 張
- #42 覆蓋:整批驗證合完再驗一次

下一步:`/client-demo #51`(Codex: `$client-demo #51`)
+ python batch.py   (mode: merged)
2 張已合併可以 demo,#48 還在修
還在修 #48 點頭 — QA 沒過,工作區 .git/batch-worktrees/48(branch batch/48)保留,下一步:`/build #48`(Codex: `$build #48`)
下一步:`/client-demo #51`(Codex: `$client-demo #51`) — 先 demo 已收的 2 張
+ git worktree list --porcelain
+ grep -F /.git/batch-worktrees/
worktree …/scratchpad/qa54/.git/batch-worktrees/48
+ git branch --list 'batch/*'
  batch/42
  batch/47
+ batch/48
+ ls .git/batch-worktrees/48
lane-48.md
README.md
```

餵給 `mode: summary` 的 `coverage` **三張票都給了**:

```json
{"47": ["#47 覆蓋:名單只列不卡的那 3 張"],
 "48": ["#48 覆蓋:沒過那張留在自己工作區"],
 "42": ["#42 覆蓋:整批驗證合完再驗一次"]}
```

印出來的聯集只有 #47 與 #42 那兩條 —— #48 那條沒混進去。這是「整批驗證只涵蓋已合併票」
的實跑證據:輸入端故意把 fail 那張的驗收項也塞進去,由程式自己挑掉,不是靠呼叫端先挑乾淨。

## 步驟 3b — 三條 lane 全部沒過(驗收原句的極端側)

```
+ python batch.py   (mode: split)
已收(0 張)— 照這個順序 merge:
  (無)
還在修(3 張)— worktree 與 branch 都留著,不 remove:
  #47 名單
  #48 點頭
  #42 整批
+ python batch.py   (mode: merged)
3 張都沒過 QA,沒有東西合併 — 主線沒動,沒有半套狀態
還在修 #47 名單 — QA 沒過,工作區 .git/batch-worktrees/47(branch batch/47)保留,下一步:`/build #47`(Codex: `$build #47`)
還在修 #48 點頭 — QA 沒過,工作區 .git/batch-worktrees/48(branch batch/48)保留,下一步:`/build #48`(Codex: `$build #48`)
還在修 #42 整批 — QA 沒過,工作區 .git/batch-worktrees/42(branch batch/42)保留,下一步:`/build #42`(Codex: `$build #42`)
+ python batch.py   (mode: summary)
## 批次總結(0 張已收 / 3 張還在修)

### 已收

- (無)

### 還在修

- #47 名單 — QA 沒過,工作區 .git/batch-worktrees/47(branch batch/47)保留,下一步:`/build #47`(Codex: `$build #47`)
- #48 點頭 — QA 沒過,工作區 .git/batch-worktrees/48(branch batch/48)保留,下一步:`/build #48`(Codex: `$build #48`)
- #42 整批 — QA 沒過,工作區 .git/batch-worktrees/42(branch batch/42)保留,下一步:`/build #42`(Codex: `$build #42`)

主線沒動,整批驗證沒有跑 — 沒有東西合上去可以驗。
+ git worktree list --porcelain
+ grep -F /.git/batch-worktrees/
worktree …/scratchpad/qa54b/.git/batch-worktrees/42
worktree …/scratchpad/qa54b/.git/batch-worktrees/47
worktree …/scratchpad/qa54b/.git/batch-worktrees/48
+ git branch --list 'batch/*'
+ batch/42
+ batch/47
+ batch/48
+ set +x
--- 主線有沒有被動過(origin/main 的 sha 應該一模一樣)
before: c01d6862b3e89a9bc63d29e945c4264436b345a5
after : c01d6862b3e89a9bc63d29e945c4264436b345a5
c01d686 seed
README.md
```

`origin/main` 的 sha 前後一模一樣、樹上只有 `README.md` —— 三片 lane 一片都沒上主線。
兩則輸出都沒有 `client-demo` 的交棒(沒東西可以 demo),總結也**沒有**宣稱整批驗證跑過。

## 步驟 3c — 打錯的時候會不會靜靜吃掉(走查中抓到的 works-but-wrong)

四個「不猜、當場停」的入口逐個餵壞資料。**第一次跑的結果是 works-but-wrong**:每一條都
正確地停了(`rc=1`),但訊息在 cp950 主控台是壞碼 ——

```
fixing �̦����b�o�媺����:#4 �X �����@�ӼƦr...
```

`SystemExit` 的訊息印在 **stderr**,而這支檔只釘了 stdout。停得對、client 看不懂,等於沒停;
跟 #58 是同一個形狀,只是換了一條 stream。當場修掉(`__main__` 補釘 stderr,self-check
逐個停法跑真的子行程比對 stderr,commit `b3bc2fa`),重跑:

```
$ echo '{"mode":"split","numbers":[47,48,42],"fixing":[4]}' | python batch.py
fixing 裡有不在這批的票號:#4 — 打錯一個數字就是把沒過 QA 的那張合上主線,不猜
rc=1
$ echo '{"mode":"summary","numbers":[47,42],"spec":51,"coverage":{"47":["a"]}}' | python batch.py
coverage 少了這幾張已合併的票:#42 — 少一張就是它的覆蓋驗收項整批沒人驗到,而總結看起來全綠
rc=1
$ echo '{"mode":"summary","numbers":[47],"spec":51,"coverage":{"#47":["a"]}}' | python batch.py
coverage 的 key 要是票號,拿到 '#47' — 寫 47 不是 '#47'
rc=1
$ echo '{"mode":"fixing","number":47,"numbers":[47,48],"fixing":[48]}' | python batch.py
#47 不在 fixing 裡,這則 comment 會貼到一張已收的票上
rc=1
$ echo '{"mode":"nope"}' | python batch.py
unknown mode: 'nope' (want one of plan, start, done, split, merged, fixing, summary)
rc=1
```

## 步驟 4 — 文件護欄的 mutation

SKILL.md 那三句「一張沒過時該做什麼」的處置,程式端一個 assert 都碰不到(程式只認得
「誰在 fixing 裡」,認不得「所以 agent 該做什麼」)。逐句刪掉再跑 self-check:

```
--- 拿掉:沒過 QA 那張的 worktree 與 branch 都留著,不 remove
AssertionError: SKILL.md: 沒過 QA 那張的工作區與 branch 要保留、不回收的那句不見了 — agent 會照 §7 把它一起 remove 掉,client 回頭沒東西可以接著修
--- 拿掉:整批驗證只涵蓋已合併那幾張的覆蓋驗收項
AssertionError: SKILL.md: 整批驗證要縮到已合併那幾張的那句不見了 — 含 fail 那張就必定紅,好的幾張也收不進去
--- 拿掉:全部 lane 都沒過 → 一張都不合
AssertionError: SKILL.md: 全部 lane 都沒過就不 merge 任何東西的那句不見了 — 剩下的是一個沒人看得懂的半套狀態
```

三句都咬得到,而且各咬各的(拿掉 A 咬 A、拿掉 B 咬 B)。三次 mutation 後 SKILL.md 都還原,
`git status` 乾淨。

## 步驟 5 — 獨立 judge

開一個乾淨 subagent,只餵驗收原句 + ticket 的 8 條 Acceptance criteria + 上面的原始終端輸出,
不餵實作脈絡、不給它讀原始碼。判決見本票的 QA 報告 comment。

## 步驟 6 — 清場

```
$ cd "D:/Self Project/Skills/.git/batch-worktrees/54"
$ git worktree list --porcelain | grep -F /.git/batch-worktrees/
worktree D:/Self Project/Skills/.git/batch-worktrees/54
worktree D:/Self Project/Skills/.git/batch-worktrees/55
worktree D:/Self Project/Skills/.git/batch-worktrees/56
$ git branch --list 'batch/*'
* batch/54
+ batch/55
+ batch/56
  batch/61
  batch/62
$ git status --short
?? docs/qa/54-walkthrough.md
```

母體裡的 `54`/`55`/`56` 是**這一批的三條 lane**(#54 是本 lane,#55、#56 是同批平行跑的
另外兩張),由 `/build-batch` 開著、整批收尾時才照 §7 回收 —— 不是本次 QA 留下的殘留。
`batch/61`、`batch/62` 是前一批留著的 branch(§7 明寫 branch 留到票結案),沒有對應的
worktree,所以第一行撈不到它們。

本次 QA 一條 worktree 都沒有在本 repo 開過:scratchpad 的兩個情境 repo 與它們的 remote 是
獨立的 clone,跟本 repo 沒有共用的 worktree 註冊表;證據裡那幾行
`worktree …/scratchpad/qa54…` 的前綴就是它們住在別的 repo 的證明。工作樹唯一的異動是本檔。

## 未涵蓋

- **`| gh issue comment` 的實際張貼**:本票新增的是 `mode: fixing` 產出的 comment **內容**;
  把它送進 `gh` 的那半是 §6 早就在跑的同一條 pipe,活證據就是本票自己那則「開工 #54 …」
  comment(由 `/build-batch` 透過同一條 pipe 貼上)。為了不在 #54 上留一則寫著「#48 沒過
  QA」的假紀錄,本輪沒有再打一次真的 GitHub。內容端的 cp950 往返由 self-check 的子行程
  斷言蓋住。
- **真的三條 subagent 平行跑 `/build` + `/qa`**:情境 3a/3b 是把「lane 綠 / 沒綠」當成輸入
  直接宣告的,沒有真的讓一條 lane 的 QA 失敗。lane 內怎麼跑是 #53 的範圍,本票治的是
  「拿到 fail 名單之後怎麼處置」。
- **merge 撞車**:#55 的範圍,SKILL.md §7 仍明寫遇到就停下來講給 client 聽。
- **獨立 judge 另外點名的兩處**(照抄,不是我改寫的):步驟 4 的三條 mutation 擋的是
  「文件裡那句不見了」,不是「程式行為變成會 remove 掉 fail 那張」— 行為端的證據是
  步驟 3a/3b 的實跑,沒有 negative-path mutation;以及 `coverage` **多**給一張不在
  已合併名單裡的票會被靜靜丟掉(只有**少**給才報錯),以驗收句「只涵蓋已合併票」來說
  行為是對的,但兩邊不對稱。兩條都不影響本票的驗收判定。
