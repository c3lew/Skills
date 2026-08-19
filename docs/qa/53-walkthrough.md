# QA walkthrough — #53 build-batch 2/6:平行開工 → 全綠 → 依序合回主線 → 整批再驗一次

第 1 輪。證據重跑四次 — 獨立 judge 連三輪把「摺疊過的實錄」「跨輪殘留的 sha」「宣稱跑過但
證據在別處」「argv 事後 render 出來、不是終端機原始輸出」逐條打回,本檔是第四次重跑後的版本。
每一輪打回的是**證據品質**,不是受測物的行為。

環境:`D:/Self Project/Skills`,HEAD = `67619b5`,working tree 乾淨(唯一異動就是本檔)。
`python -c "import sys;print(sys.stdout.encoding)"` → `cp950`。
本票是 CLI 純函式 + skill 文件 + 一串 client 端真的會貼進終端機的 git 指令,沒有 UI、
沒有視覺 oracle,不走 Playwright;本檔是終端實錄。

**三個地方,分清楚:**

- **CLI 輸出**(步驟 1、2、3、4)跑在本 repo `D:/Self Project/Skills`,只讀不寫。
- **git 那一整套**(步驟 3a)跑在 scratchpad 的 clone(`…/scratchpad/qa53`),origin 指向
  scratchpad 的 bare repo(`…/scratchpad/qa53-remote.git`)。本 repo 沒被開過 worktree、
  沒多出 branch、沒被 push,清場見步驟 6。
- **`gh` 那一段**(步驟 5)打的是真的 GitHub,真的在 #53 上留下一則 comment。

**實錄的呈現規則**:步驟 3a 是一支 script 一次跑完的輸出,**指令那幾行是 bash 自己的
xtrace 印的**(`PS4='+ '`,`set -x`),不是我事後照著寫的 — 所以引號、glob 展開、`cd`、
`printf` 的參數全部照實出現,順序就是真的執行順序(stdout 與 stderr 合流)。**一個已知限制:
xtrace 不印重導向**,所以 `printf … >> docs/qa/lane-47.md` 的 `>>` 那半看不到,寫進哪個檔要
靠下一行的 `git add docs/qa/lane-47.md` 與 commit 的 `create mode 100644` 反推。整段原封不動貼上,
沒有摺疊、沒有省略號、沒有補寫的摘要行。唯一的改動是把 scratchpad 的長路徑統一縮寫成
`…/scratchpad`(整份檔一致)。其他步驟是逐段手跑,指令與輸出成對貼出。

判定 oracle = 票上「覆蓋驗收項」三條原句:

1. Client 點頭 → 三張各自在獨立工作區開工,終端機每張各報一行「開工」。
2. 三張都綠 → 合回主線,合完整批再驗一次,終端機報「3 張已合併,下一步 demo」。
3. 整批結束 → 每張票上都有產出紀錄,spec 票上留一則批次總結 + 下一步指令。

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

## 步驟 1 — regression suite(本 repo)

```text
$ python scripts/validate.py --self-check
OK validate self-check green
$ python scripts/validate.py
OK validate green
$ python scripts/batch.py --self-check
OK batch self-check green
$ python skills/build-batch/batch.py --self-check
OK batch self-check green
$ python scripts/install.py --self-check
[fixture] FAIL skills/bad: missing SKILL.md
OK install self-check green
$ python scripts/hooks/triage-to-maintain.py --self-check
OK triage-to-maintain self-check green
```

全綠。兩個都印 `OK batch self-check green` 的是不同的兩支檔,**但跑的是同一組斷言** —
`scripts/batch.py` 是 repo 層的入口,把 `skills/build-batch` 加進 `sys.path` 之後
`from batch import self_check` 再叫它。所以這兩行是同一套 self-check 用兩種路徑跑,
不是兩組獨立的測試:

```text
$ md5sum scripts/batch.py skills/build-batch/batch.py
05371b9d7168b6d0067e06267fc27c9b *scripts/batch.py
670a2bd5b96c89e63c1fc5d92b21d50c *skills/build-batch/batch.py
$ wc -c scripts/batch.py skills/build-batch/batch.py
  737 scripts/batch.py
23557 skills/build-batch/batch.py
$ grep -n "import\|self_check" scripts/batch.py
9:import sys
10:from pathlib import Path
12:sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "build-batch"))
13:from batch import self_check  # noqa: E402
17:    if "--self-check" in sys.argv:
18:        self_check()
```

(`[fixture] FAIL` 是 install self-check 自己的負向 fixture,預期輸出。)

## 步驟 2 — 驗收項 1:終端機每張各報一行「開工」(本 repo)

跑的是 SKILL.md §6 的這段(原文照抄,`skills/build-batch/SKILL.md` 第 71-75 行):

> ```bash
> python <skill dir>/batch.py <<'JSON'
> {"mode": "start", "numbers": [47, 48], "titles": {"47": "...", "48": "..."}}
> JSON
> ```

`<skill dir>` 代入 `skills/build-batch`,票號換成三張。`PYTHONIOENCODING=cp950` 是我另外加的
— 用來證明連把環境釘成 cp950 都蓋不掉 `__main__` 的 UTF-8 pin(#58 的形狀)。title 裡留
emoji,Big5 沒有它。

```text
$ cd skills/build-batch
$ PYTHONIOENCODING=cp950 python batch.py <<'JSON'
{"mode": "start", "numbers": [47, 48, 42],
 "titles": {"47": "登入頁 → 🔑", "48": "點頭", "42": "導向"}}
JSON
開工 #47 登入頁 → 🔑 — 工作區 .git/batch-worktrees/47(branch batch/47)
開工 #48 點頭 — 工作區 .git/batch-worktrees/48(branch batch/48)
開工 #42 導向 — 工作區 .git/batch-worktrees/42(branch batch/42)
```

三張、各一行、各自不同的工作區與 branch。

貼回票上那條路的 pipe 端是 UTF-8(`gh` 端見步驟 5):

```text
$ echo '{"mode": "start", "numbers": [47], "titles": {"47": "登入頁 → 🔑"}}' | PYTHONIOENCODING=cp950 python batch.py | od -c | head -2
0000000 351 226 213 345 267 245       #   4   7     347 231 273 345 205
0000020 245 351 240 201     342 206 222     360 237 224 221     342 200
```

`351 226 213` = `開` 的 UTF-8。

**這一條驗到的範圍**:程式寫進 pipe 的 bytes 是 UTF-8,而且 `PYTHONIOENCODING=cp950` 蓋不掉
它。真的主控台(`sys.stdout` 直接接 console handle)是另一條路徑 — 那條在 #58 修完之後由
`__main__` 的同一行 `reconfigure` 管,本輪沒有再拿實體 console 重驗一次。

這條指令只是**印**,不會動檔案系統 — 前後各夾一次 `test -d`:

```text
$ cd "D:/Self Project/Skills"        # 先回 repo root,下面三行的相對路徑都以它為準
$ test -d .git/batch-worktrees && echo EXISTS || echo 不存在
不存在
$ echo '{"mode":"start","numbers":[47,48,42],"titles":{}}' | PYTHONIOENCODING=cp950 python skills/build-batch/batch.py
開工 #47 — 工作區 .git/batch-worktrees/47(branch batch/47)
開工 #48 — 工作區 .git/batch-worktrees/48(branch batch/48)
開工 #42 — 工作區 .git/batch-worktrees/42(branch batch/42)
$ test -d .git/batch-worktrees && echo EXISTS || echo 不存在
不存在
```

所以「開工」這一行是**指示**,不是動作;真的開工作區的是 §6 接在後面那兩行 git 指令
(步驟 3a 實跑)。

## 步驟 3 — 驗收項 2 的兩個 CLI 輸出(本 repo)

每張綠了各報一行(§6):

```text
$ PYTHONIOENCODING=cp950 python batch.py <<'JSON'
{"mode": "done", "numbers": [47], "titles": {"47": "登入頁 → 🔑"}}
JSON
完成 #47 登入頁 → 🔑 — build + QA 綠
$ PYTHONIOENCODING=cp950 python batch.py <<'JSON'
{"mode": "done", "numbers": [48], "titles": {"48": "點頭"}}
JSON
完成 #48 點頭 — build + QA 綠
$ PYTHONIOENCODING=cp950 python batch.py <<'JSON'
{"mode": "done", "numbers": [42], "titles": {"42": "導向"}}
JSON
完成 #42 導向 — build + QA 綠
```

**這一行是照 lane 結果印的字串,不是 gate。**「lane 真的綠了沒」由 lane 內的 `/build` +
`/qa` 決定,本輪 lane 的「綠」是 QA 拿 self-check 代打的(步驟 3a)。「綠了才准合」這個把關
本輪沒有被測到 — 見未涵蓋範圍第 2 條。

整批合併完的最後一行(§9):

```text
$ PYTHONIOENCODING=cp950 python batch.py <<'JSON'
{"mode": "merged", "numbers": [47, 48, 42], "spec": 51}
JSON
3 張已合併,下一步:`/client-demo #51`(Codex: `$client-demo #51`) — 一次 demo 這批
```

**「3 張」同樣是把輸入 `numbers` 的長度回吐,不查證任何 merge 真的發生過** — 跟上面的
「完成」行同一個性質。真的有沒有合進去看步驟 3a 的 sha 鏈。

## 步驟 3a — 工作區、upstream、依序合併、整批驗證(scratchpad clone,xtrace)

下面整段是一支 script 一次跑完的原始輸出:開三個工作區 → 每條 lane 在自己的工作區裡
`printf` 新增一個 `docs/qa/lane-<N>.md`(**是新增檔,不是改既有的 tracked 檔** — 實錄裡是
`create mode 100644`)+ commit + 跑 self-check + push → 反例(沒 `push -u` 會怎樣)→
依序 merge、每張合完當場收自己的工作區 → 合完的主線上跑整批驗證。

`+ ` 開頭的行是 bash xtrace 印的指令,其餘是該指令的輸出。**注意 `git branch` 的輸出裡也有
`+`**:那是 git 自己的標記,表示該 branch 正 checkout 在某個 linked worktree 裡 — 三條 lane
在跑的時候是 `+ batch/47`,全部合完收掉工作區之後變回 `  batch/47`,這本身就是「工作區真的
存在過、也真的被收掉」的旁證。

```text
+ git worktree add .git/batch-worktrees/47 -b batch/47
Preparing worktree (new branch 'batch/47')
HEAD is now at 67619b5 feat: build-batch 平行開工 → 依序合回主線 → 整批再驗一次 (#53)
+ git push -u origin batch/47
To …/scratchpad/qa53-remote.git
 * [new branch]      batch/47 -> batch/47
branch 'batch/47' set up to track 'origin/batch/47'.
+ git worktree add .git/batch-worktrees/48 -b batch/48
Preparing worktree (new branch 'batch/48')
HEAD is now at 67619b5 feat: build-batch 平行開工 → 依序合回主線 → 整批再驗一次 (#53)
+ git push -u origin batch/48
To …/scratchpad/qa53-remote.git
 * [new branch]      batch/48 -> batch/48
branch 'batch/48' set up to track 'origin/batch/48'.
+ git worktree add .git/batch-worktrees/42 -b batch/42
Preparing worktree (new branch 'batch/42')
HEAD is now at 67619b5 feat: build-batch 平行開工 → 依序合回主線 → 整批再驗一次 (#53)
+ git push -u origin batch/42
To …/scratchpad/qa53-remote.git
 * [new branch]      batch/42 -> batch/42
branch 'batch/42' set up to track 'origin/batch/42'.
+ git status --short
+ git worktree list
…/scratchpad/qa53                         67619b5 [main]
…/scratchpad/qa53/.git/batch-worktrees/42 67619b5 [batch/42]
…/scratchpad/qa53/.git/batch-worktrees/47 67619b5 [batch/47]
…/scratchpad/qa53/.git/batch-worktrees/48 67619b5 [batch/48]
+ cd .git/batch-worktrees/47
+ pwd
…/scratchpad/qa53/.git/batch-worktrees/47
+ printf '\n# lane 47 touched\n'
+ git add docs/qa/lane-47.md
+ git commit -m 'lane 47 work'
[batch/47 e58c19a] lane 47 work
 1 file changed, 2 insertions(+)
 create mode 100644 docs/qa/lane-47.md
+ python skills/build-batch/batch.py --self-check
OK batch self-check green
+ git push
To …/scratchpad/qa53-remote.git
   67619b5..e58c19a  batch/47 -> batch/47
+ git log --oneline -1 origin/batch/47
e58c19a lane 47 work
+ ls docs/qa/lane-47.md
docs/qa/lane-47.md
+ cd …/scratchpad/qa53
+ cd .git/batch-worktrees/48
+ pwd
…/scratchpad/qa53/.git/batch-worktrees/48
+ printf '\n# lane 48 touched\n'
+ git add docs/qa/lane-48.md
+ git commit -m 'lane 48 work'
[batch/48 b7d1529] lane 48 work
 1 file changed, 2 insertions(+)
 create mode 100644 docs/qa/lane-48.md
+ python skills/build-batch/batch.py --self-check
OK batch self-check green
+ git push
To …/scratchpad/qa53-remote.git
   67619b5..b7d1529  batch/48 -> batch/48
+ git log --oneline -1 origin/batch/48
b7d1529 lane 48 work
+ ls docs/qa/lane-48.md
docs/qa/lane-48.md
+ cd …/scratchpad/qa53
+ cd .git/batch-worktrees/42
+ pwd
…/scratchpad/qa53/.git/batch-worktrees/42
+ printf '\n# lane 42 touched\n'
+ git add docs/qa/lane-42.md
+ git commit -m 'lane 42 work'
[batch/42 06a5f23] lane 42 work
 1 file changed, 2 insertions(+)
 create mode 100644 docs/qa/lane-42.md
+ python skills/build-batch/batch.py --self-check
OK batch self-check green
+ git push
To …/scratchpad/qa53-remote.git
   67619b5..06a5f23  batch/42 -> batch/42
+ git log --oneline -1 origin/batch/42
06a5f23 lane 42 work
+ ls docs/qa/lane-42.md
docs/qa/lane-42.md
+ cd …/scratchpad/qa53
+ git branch -v --list 'batch/*'
+ batch/42 06a5f23 lane 42 work
+ batch/47 e58c19a lane 47 work
+ batch/48 b7d1529 lane 48 work
+ git worktree add .git/batch-worktrees/99 -b batch/99
Preparing worktree (new branch 'batch/99')
HEAD is now at 67619b5 feat: build-batch 平行開工 → 依序合回主線 → 整批再驗一次 (#53)
+ cd .git/batch-worktrees/99
+ printf 'x\n'
+ git add L99.txt
+ git commit -m 'lane 99 work'
[batch/99 feb5bf1] lane 99 work
 1 file changed, 1 insertion(+)
 create mode 100644 L99.txt
+ git push
fatal: The current branch batch/99 has no upstream branch.
To push the current branch and set the remote as upstream, use

    git push --set-upstream origin batch/99

To have this happen automatically for branches without a tracking
upstream, see 'push.autoSetupRemote' in 'git help config'.

+ echo exit=128
exit=128
+ cd …/scratchpad/qa53
+ git worktree remove --force .git/batch-worktrees/99
+ git branch -D batch/99
Deleted branch batch/99 (was feb5bf1).
+ git branch --list 'batch/*'
+ batch/42
+ batch/47
+ batch/48
+ git merge --no-ff -m 'merge batch/47' batch/47
Merge made by the 'ort' strategy.
 docs/qa/lane-47.md | 2 ++
 1 file changed, 2 insertions(+)
 create mode 100644 docs/qa/lane-47.md
+ git push
To …/scratchpad/qa53-remote.git
   67619b5..aa64641  main -> main
+ git worktree remove .git/batch-worktrees/47
+ ls .git/batch-worktrees
42
48
+ ls docs/qa/lane-47.md
docs/qa/lane-47.md
+ git merge --no-ff -m 'merge batch/48' batch/48
Merge made by the 'ort' strategy.
 docs/qa/lane-48.md | 2 ++
 1 file changed, 2 insertions(+)
 create mode 100644 docs/qa/lane-48.md
+ git push
To …/scratchpad/qa53-remote.git
   aa64641..e9cc37b  main -> main
+ git worktree remove .git/batch-worktrees/48
+ ls .git/batch-worktrees
42
+ ls docs/qa/lane-47.md docs/qa/lane-48.md
docs/qa/lane-47.md
docs/qa/lane-48.md
+ git merge --no-ff -m 'merge batch/42' batch/42
Merge made by the 'ort' strategy.
 docs/qa/lane-42.md | 2 ++
 1 file changed, 2 insertions(+)
 create mode 100644 docs/qa/lane-42.md
+ git push
To …/scratchpad/qa53-remote.git
   e9cc37b..2309187  main -> main
+ git worktree remove .git/batch-worktrees/42
+ ls .git/batch-worktrees
+ ls docs/qa/lane-42.md docs/qa/lane-47.md docs/qa/lane-48.md
docs/qa/lane-42.md
docs/qa/lane-47.md
docs/qa/lane-48.md
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
+ git log --oneline -10
2309187 merge batch/42
e9cc37b merge batch/48
aa64641 merge batch/47
06a5f23 lane 42 work
b7d1529 lane 48 work
e58c19a lane 47 work
67619b5 feat: build-batch 平行開工 → 依序合回主線 → 整批再驗一次 (#53)
04e143f docs: dashboard 更新 — #52 結案,下一棒 /build-batch #51
25d00b1 docs: release note — #52 名單上線,已換裝本機
1d1d65a test: 固化 #52 — §4/§5 給 client 的兩句咬進 self-check
+ git branch --list 'batch/*'
  batch/42
  batch/47
  batch/48
+ git worktree list
…/scratchpad/qa53 2309187 [main]
+ set +x
```

這段 transcript 直接對上的幾件事:

- **隔離**:三條 lane 各自 commit(`e58c19a` / `b7d1529` / `06a5f23`)、各自 push。
  隔離的證據是 xtrace 裡的 **glob 展開**:script 寫的是 `ls docs/qa/lane-*.md`,bash 展開後
  印出來的是 `+ ls docs/qa/lane-47.md` — 也就是在 lane 47 的工作區裡,`lane-*.md` 只 match
  到一個檔,48 與 42 的檔在那個工作區裡根本不存在(不是我只 ls 了一個已知路徑,是 shell
  自己掃出來只有一個)。三條 lane 都是同樣的形狀。
- **工作區不進 `git status`**:三個 worktree 都開好之後那次 `git status --short` 沒有輸出。
  這條旁證很弱 — 當下 lane 檔都還沒建,本來就沒東西可報;而且 `.git/` 底下不進 status 是
  git 的定義,不是這次量出來的。真正被證到的只有「`worktree add` 到 `.git/` 底下不會讓主
  repo 的 status 髒掉」,`LANE_ROOT` 註解宣稱的就是這件事。
- **`push -u` 的必要性**:三條 lane 開完就 `push -u`,後面 lane 內第一次 `git push`
  (完全不帶參數)都成功推上去(`67619b5..e58c19a` 等)。反例那條 lane 沒跑 `push -u`,
  同樣一句 `git push` 當場 `fatal: … has no upstream branch`、`exit=128`。`/build` 的完工
  標準是 `git rev-list --count origin/<branch>..HEAD` 為 `0`,沒有 upstream 這步連跑都跑
  不到。反例的 commit 是 `feb5bf1`,用完當場 `worktree remove --force` + `branch -D` 收掉
  (`Deleted branch batch/99 (was feb5bf1)`),後面的 `git branch --list` 只剩 42/47/48 —
  它沒有留到後面污染任何一份 listing。
- **依序**:三次 merge 的 `git push` 首尾相接 — `67619b5..aa64641` → `aa64641..e9cc37b`
  → `e9cc37b..2309187`。每張合完主線多一個 lane 檔(`ls docs/qa/lane-*.md` 的 glob 展開
  由 1 個 → 2 個 → 3 個),而且**當場只收自己那一份工作區**,另外兩份還在
  (`ls .git/batch-worktrees` 由 `42 48` → `42` → 沒有輸出)。
- **整批驗證**:六個 self-check 跑在 `2309187`(三張都合完)之上,全綠;`git log --oneline
  -10` 完整貼出,三個 merge commit 與三個 lane commit 都在。
- **branch 保留、工作區回收**:`git branch --list 'batch/*'` 還是三條;`git worktree list`
  在這份 clone 裡只剩主 repo。

## 步驟 4 — 驗收項 3 後半的內容:批次總結長什麼樣(本 repo)

故意餵重複的覆蓋驗收項,看去重有沒有做:

```text
$ PYTHONIOENCODING=cp950 python batch.py <<'JSON'
{"mode": "summary", "numbers": [47, 48, 42], "spec": 51,
 "titles": {"47": "登入頁 → 🔑", "48": "點頭", "42": "導向"},
 "coverage": [["Client 點頭 → 三張各自在獨立工作區開工。", "整批結束 → 每張票上都有產出紀錄。"],
              ["整批結束 → 每張票上都有產出紀錄。", "三張都綠 → 合回主線。"],
              []]}
JSON
## 批次總結(3 張)

- #47 登入頁 → 🔑 — 已合併(batch/47)
- #48 點頭 — 已合併(batch/48)
- #42 導向 — 已合併(batch/42)

整批驗證:regression + 下列覆蓋驗收項聯集,全綠。

- Client 點頭 → 三張各自在獨立工作區開工。
- 整批結束 → 每張票上都有產出紀錄。
- 三張都綠 → 合回主線。

下一步:`/client-demo #51`(Codex: `$client-demo #51`)
```

三張都列到、聯集列到、重複那條只出現一次、結尾是交棒行。

## 步驟 5 — 「留在票上」真的做一次(真的 GitHub)

步驟 4 只證明它**印得出來**;原句要的是「票上留一則」。所以把同一段 stdout 直接 pipe 進
`gh issue comment`,貼到真的 issue 上,再從 GitHub API 撈回來逐字元比對。

```text
$ cd skills/build-batch
$ { printf '### QA 證據(#53 walkthrough 步驟 5)— 這不是真的批次總結\n\n下面整段是 `skills/build-batch/batch.py` `mode=summary` 的 stdout,直接 pipe 進 `gh issue comment 53 --body-file -`,用來驗「終端機字串 → 票上」這條路真的走得通(含中文與 emoji)。票號、標題、覆蓋驗收項都是 QA 造的樣本。\n\n---\n\n'; PYTHONIOENCODING=cp950 python batch.py <<'JSON'
{"mode": "summary", "numbers": [47, 48, 42], "spec": 51,
 "titles": {"47": "登入頁 → 🔑", "48": "點頭", "42": "導向"},
 "coverage": [["Client 點頭 → 三張各自在獨立工作區開工。", "整批結束 → 每張票上都有產出紀錄。"],
              ["整批結束 → 每張票上都有產出紀錄。", "三張都綠 → 合回主線。"],
              []]}
JSON
} | gh issue comment 53 --body-file -
https://github.com/c3lew/Skills/issues/53#issuecomment-5338114051
```

(那份 JSON 與步驟 4 的逐字元相同 — 兩處都貼全,可以自己對。)

從 GitHub 撈回來、裁掉標頭、逐字元比對 — 這一段同樣由 bash xtrace 印指令
(`+ ` 開頭的是指令,其餘是輸出;cwd 是 `D:/Self Project/Skills/skills/build-batch`):

```text
+ PYTHONIOENCODING=cp950
+ python batch.py                      # heredoc 與上面那份逐字元相同,輸出導進 local.txt
+ wc -l …/scratchpad/local.txt
13 …/scratchpad/local.txt
+ gh api repos/c3lew/Skills/issues/comments/5338114051 -q .body
+ wc -l …/scratchpad/readback-full.txt
20 …/scratchpad/readback-full.txt
+ head -8 …/scratchpad/readback-full.txt
### QA 證據(#53 walkthrough 步驟 5)— 這不是真的批次總結

下面整段是 `skills/build-batch/batch.py` `mode=summary` 的 stdout,直接 pipe 進 `gh issue comment 53 --body-file -`,用來驗「終端機字串 → 票上」這條路真的走得通(含中文與 emoji)。票號、標題、覆蓋驗收項都是 QA 造的樣本。

---

## 批次總結(3 張)

+ tail -n +7 …/scratchpad/readback-full.txt
+ wc -l …/scratchpad/readback-body.txt
14 …/scratchpad/readback-body.txt
+ cat …/scratchpad/readback-body.txt
## 批次總結(3 張)

- #47 登入頁 → 🔑 — 已合併(batch/47)
- #48 點頭 — 已合併(batch/48)
- #42 導向 — 已合併(batch/42)

整批驗證:regression + 下列覆蓋驗收項聯集,全綠。

- Client 點頭 → 三張各自在獨立工作區開工。
- 整批結束 → 每張票上都有產出紀錄。
- 三張都綠 → 合回主線。

下一步:`/client-demo #51`(Codex: `$client-demo #51`)

+ set +x
```

行數對得起來:GitHub 存的整則 body 是 20 行 = QA 的標頭 6 行(標題、空行、說明、空行、
`---`、空行,`head -8` 看得到前 8 行)+ `batch.py` 的 13 行 + 結尾空行。`tail -n +7` 裁掉
標頭之後是 14 行(13 行內容 + 結尾空行)。

最後逐字元比對這兩個檔:

```text
++ PYTHONIOENCODING=utf-8
++ python -
本機 stdout 行數: 13
GitHub 撈回行數 : 13
逐字元相同      : True
emoji 那一行    : - #47 登入頁 → 🔑 — 已合併(batch/47)
```

跑的是這支(`strip("
")` 吃掉結尾空行的差、`replace` 吃掉 CRLF 的差):

```python
import pathlib
norm = lambda f: pathlib.Path(f).read_text(encoding="utf-8").replace("
", "
").strip("
")
local, back = norm("local.txt"), norm("readback-body.txt")
print("本機 stdout 行數:", len(local.splitlines()))
print("GitHub 撈回行數 :", len(back.splitlines()))
print("逐字元相同      :", local == back)
for line in back.splitlines():
    if "🔑" in line:
        print("emoji 那一行    :", line)
```

`--body-file -` 這條路真的走得通,中文與 emoji 存回 GitHub 一字不差。

**這一則貼在 #53 上、標頭寫明是 QA 樣本**,票號 / 標題 / 覆蓋驗收項都是造的。**貼到真的
spec 票 #51、內容是真的一批票的總結**,本輪沒做(要有真的批次才有真的內容)— 見未涵蓋
範圍第 4 條。

## 步驟 6 — 清場(本 repo)

```text
$ rm -rf …/scratchpad/qa53 …/scratchpad/qa53-remote.git
$ cd "D:/Self Project/Skills"
$ git log --oneline -1
67619b5 feat: build-batch 平行開工 → 依序合回主線 → 整批再驗一次 (#53)
$ git branch --list 'batch/*'
(空)
$ test -d .git/batch-worktrees && echo EXISTS || echo 不存在
不存在
$ git worktree list
D:/Self Project/Skills                                           67619b5 [main]
D:/Self Project/Skills/.claude/worktrees/agent-a1774032b0e17d127 5192e47 [research/context-smart-zone] locked
D:/Self Project/Skills/.claude/worktrees/agent-a1ce94f5bd5097fdc efd5016 [research/company-vs-solo-agent] locked
D:/Self Project/Skills/.claude/worktrees/agent-aa8443950469b0c07 de7d72d [research/agent-user-pov-qa] locked
```

本票開的東西沒有殘留(`batch/*` 空、`.git/batch-worktrees` 不存在、HEAD 沒動)。

**但 `git worktree list` 是 4 列,不是 1 列** — 那 3 列是 Claude Code 給 subagent 用的
worktree(`.claude/worktrees/agent-*`,`locked`),長期住在這個 repo 裡,跟本票無關。
SKILL.md §9 寫「`git worktree list` 應該只剩主 repo — 沒剩乾淨就是有 lane 沒走完 §7,
回頭查」:在這台機器上,0 個 lane 殘留的情況下這句照樣是紅的。→ **known issue A**。

另外:`git worktree remove` 收掉最後一份之後,空的 `.git/batch-worktrees/` 目錄會留著
(步驟 3a 最後一次 `ls .git/batch-worktrees` 印出空的,目錄本身還在)。藏在 `.git/` 底下、
不進 `git status`,無害,不開票。

## Known issues(非 blocking,帶著 demo)

**A(#61). §9 的清場檢查在這台機器上永遠誤報。** SKILL.md §9 最後一句拿「`git worktree list` 只剩
主 repo」當「lane 有沒有走完 §7」的判準。實測:本票 0 個 lane 殘留,那行照樣印 4 列,因為
Claude Code 自己的 subagent worktree(`.claude/worktrees/agent-*`)常駐在同一個 repo。判準
要縮到 `.git/batch-worktrees/` 這個範圍才有鑑別力。證據見步驟 6。

**B(#62). §9 貼批次總結那段沒給可以直接貼的指令。** §6 的兩處都給了完整的
`… | gh issue comment <N> --body-file -`,§9 只給 `python … <<'JSON'` 的 heredoc,再用散文說
「印出來的整段當 comment body 貼上去(`gh issue comment 51 --body-file -`)」— heredoc 要
怎麼跟 pipe 接起來留給 agent 自己拼。同一份文件裡三處同型指令,兩處給全、一處沒給。

## 未涵蓋範圍

1. **§5 的點頭 gate、以及 lane 內真正跑 `/build #N` + `/qa #N`** — 需要三張真的 ready 票 +
   client 真的點頭 + 三個 subagent 真的跑完整條 build/QA。那就是 `/build-batch` 正式跑的
   樣子,QA 生不出等價物。本輪 lane 的內容是 QA 造的(改一個 md 檔 + 跑 self-check),
   驗到的是它腳下的機制層。
2. **「綠了才准合」這個把關沒被測** — 步驟 3 的「完成」行是照參數印的字串;本輪沒有製造
   「某條 lane 紅了」的情況看它會不會擋住 merge(本版也明說 fail 路徑不在範圍)。
3. **每張票上的產出紀錄** — 由 lane 內的 `/build` 貼(§9 明寫這裡不重複寫)。本輪沒實跑
   `/build`,這半沒有本輪實錄。
4. **真的 spec 票上真的批次總結** — 步驟 5 驗到「`batch.py` 的輸出貼得上 GitHub 且一字不
   差」,但貼的是 QA 造的樣本、貼在 #53 而不是 spec 票 #51。
5. **`gh issue comment` 貼「開工 / 完成」兩行到真的票上** — 會在真票留下假資料,沒做;用的
   是同一條 pipe 加同一個旗標(步驟 5 已驗)。
6. **CLI 的字串與 git 的動作沒有在同一次執行裡連起來(兩側都是)** —
   *開工側*:`batch.py` 只印字串(步驟 2 尾巴的 `test -d` 前後夾證),worktree 是步驟 3a
   在 scratchpad clone 裡照那個字串手打 git 開的;兩邊字面值相同
   (`.git/batch-worktrees/47` / `batch/47`),但「跑這個 skill 就會得到那個工作區」這條因果
   沒被驗到。*合併側*:merge 發生在 scratchpad clone,「3 張已合併」印在本 repo,而那個
   數字是回吐輸入的長度、不查證 merge — 同型斷點。兩側都要等 §5 點頭之後的真跑才連得上,
   和第 1 條同一個缺口。
7. **fail / 撞車 / 超過 3 張排隊三條路徑** — SKILL.md §5、§7 明寫不在本版範圍,遇到停下來
   交給 client,是後面各自獨立的票。

第 1、3 兩條是同一個缺口的兩面(lane 內的 `/build` + `/qa` 從沒跑過),**由
`/client-demo #53` 親手跑一次把關**。
