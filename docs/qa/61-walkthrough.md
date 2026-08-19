# QA walkthrough — #61 build-batch:§9 清場檢查的母體選錯(bug fix)

Bug fix ticket,範圍 = 該 bug 的重現 scenario + regression suite。

判定 oracle(票上「對應驗收原句」):

> 「整批結束 → 每張票上都有產出紀錄,spec 票上留一則批次總結 + 下一步指令。」的收尾段;
> 以及 #53 acceptance 的「Lane 結束後 worktree 自動移除,branch 保留」。
> 回收行為本身是對的(實測見 `docs/qa/53-walkthrough.md` 步驟 6),**錯的是驗證它的那句判準**。

所以這輪判的不是「worktree 有沒有被收掉」,是「那句判準看不看得出來收乾淨了沒」。

**兩條原句的分工先講清楚**:原句 2(worktree 移除 / branch 保留)是本票直接動到的判準,本輪逐條實測。
原句 1(票上產出紀錄 + spec 票批次總結)本票**沒有碰到** — 它的判準在 §9 前半段,是同批 #62 的範圍;
本檔不宣稱它 pass,證據包裡也沒有它的東西。

環境:lane worktree `D:/Self Project/Skills/.git/batch-worktrees/61`,branch `batch/61`,
working tree 乾淨。本票是 skill 文件 + shell 判準,沒有 UI,不走 Playwright;本檔是終端實錄。

**實錄的呈現規則**:步驟 3 是一支 script 一次跑完的輸出,**指令那幾行是 bash 自己的 xtrace 印的**
(`PS4` 設成 `+ `,`set -x`),不是事後照著寫的 — `cd`、pipe 拆成兩行、參數展開全部照實出現,順序就是
真的執行順序(stdout / stderr 合流)。exit code 是寫在 `echo` 參數裡的 `$?`,xtrace 印的是**展開後**的
值,所以直接讀 `+ echo` 那一行就是真的 exit code。整段原封不動貼上,沒有摺疊、沒有省略號。唯一的改動是
把 scratchpad 的長路徑統一縮寫成 `…/scratchpad`(整份檔一致)。

**一個讀 log 的陷阱**:`git branch --list` 的輸出裡,行首的 `+` 是 **git 自己的標記**(這條 branch 正
被別的 worktree checkout 著),不是 xtrace 的 `+ ` 前綴 — 兩者長得一樣。狀態 B 印 `+ batch/47`
(worktree 還在),狀態 A' 印 `  batch/47`(worktree 收掉了、branch 留著),差的那個 `+` 是真訊息。

一鍵重開(沿用既有 CLI QA 入口 + 本輪新增的重現 script):

```bash
cd "D:/Self Project/Skills"
python scripts/validate.py
python scripts/validate.py --self-check
python scripts/batch.py --self-check
python skills/build-batch/batch.py --self-check
python scripts/install.py --self-check
python scripts/hooks/triage-to-maintain.py --self-check
# 重現 script(六種狀態,造在 scratchpad,不碰本 repo):
SP=<scratchpad dir> bash <scratchpad dir>/qa61.sh
```

`qa61.sh` 全文收在本檔附錄,照著存下來就能重跑。

## 步驟 1 — regression suite

```text
$ python scripts/validate.py
OK validate green
exit 0

$ python scripts/validate.py --self-check
OK validate self-check green
exit 0

$ python scripts/batch.py --self-check
OK batch self-check green
exit 0

$ python skills/build-batch/batch.py --self-check
OK batch self-check green
exit 0

$ python scripts/install.py --self-check
[fixture] FAIL skills/bad: missing SKILL.md
OK install self-check green
exit 0

$ python scripts/hooks/triage-to-maintain.py --self-check
OK triage-to-maintain self-check green
exit 0
```

6 支全綠。(`install.py` 那行 `[fixture] FAIL` 是預期輸出 — 刻意壞掉的 fixture,見 #43。)

## 步驟 2 — 重現:兩種母體在真實 repo 上長什麼樣

在開票那台機器的主 repo 跑。這次把**新判準也真的跑一次**(不是從列數用人腦推):

```text
$ cd "D:/Self Project/Skills"
$ git worktree list
D:/Self Project/Skills                                           5a6527c [main]
D:/Self Project/Skills/.claude/worktrees/agent-a1774032b0e17d127 5192e47 [research/context-smart-zone] locked
D:/Self Project/Skills/.claude/worktrees/agent-a1ce94f5bd5097fdc efd5016 [research/company-vs-solo-agent] locked
D:/Self Project/Skills/.claude/worktrees/agent-aa8443950469b0c07 de7d72d [research/agent-user-pov-qa] locked
D:/Self Project/Skills/.git/batch-worktrees/61                   5a6527c [batch/61]
D:/Self Project/Skills/.git/batch-worktrees/62                   5a6527c [batch/62]

$ git worktree list --porcelain | grep -F /.git/batch-worktrees/
worktree D:/Self Project/Skills/.git/batch-worktrees/61
worktree D:/Self Project/Skills/.git/batch-worktrees/62
exit 0

$ git branch --list 'batch/*'
+ batch/61
+ batch/62
exit 0
```

(`+` 是 git 標「這條 branch 正被別的 worktree checkout 著」— 兩條 lane 都還開著,合理。)

6 列裡:1 列主 repo、3 列 Claude Code 給 subagent 常駐的 worktree、2 列本批的 lane。舊判準
(「應該只剩主 repo」)在這裡對不上,而且要人工從 6 列裡挑出哪 2 列是 lane;新判準直接印出那 2 列。

票上寫的「0 個 lane 殘留照樣印 4 列」那組數字**不是本輪量的** — 它出自 `docs/qa/53-walkthrough.md`
步驟 6(當時 batch 沒在跑,4 列 = 1 主 repo + 3 subagent)。本輪這台機器正在跑 batch,所以是 6 列 /
2 條 lane。兩組數字量的是同一個現象的兩個時點,SKILL.md 定稿引的是 #53 那組,並在文字裡註明出處。

## 步驟 3 — 六種狀態的對照實測(scratchpad 乾淨 repo)

不動本 repo。在 scratchpad 造一個乾淨 repo,先鋪三個干擾項:兩個「別人的」worktree
(`.claude/worktrees/agent-aaaa` / `agent-bbbb`,模擬 subagent 常駐)、一個 **decoy**
(`decoy/batch-worktrees/x` — 路徑含 `batch-worktrees` 但不在 `.git/` 底下),再走六種狀態。

```text
+ PS4='+ '
+ R=…/scratchpad/qa61
+ rm -rf …/scratchpad/qa61
+ mkdir -p …/scratchpad/qa61
+ cd …/scratchpad/qa61
+ git init -q -b main .
+ git config user.email qa@example.com
+ git config user.name QA
+ echo hi
+ git add README.md
warning: in the working copy of 'README.md', LF will be replaced by CRLF the next time Git touches it
+ git commit -qm init
+ git worktree add -q -b research/fake-a .claude/worktrees/agent-aaaa
+ git worktree add -q -b research/fake-b .claude/worktrees/agent-bbbb
+ mkdir -p …/scratchpad/qa61/decoy/batch-worktrees
+ git worktree add -q -b decoy/x …/scratchpad/qa61/decoy/batch-worktrees/x
+ git worktree list
…/scratchpad/qa61                              a5d9bfa [main]
…/scratchpad/qa61/.claude/worktrees/agent-aaaa a5d9bfa [research/fake-a]
…/scratchpad/qa61/.claude/worktrees/agent-bbbb a5d9bfa [research/fake-b]
…/scratchpad/qa61/decoy/batch-worktrees/x      a5d9bfa [decoy/x]
+ git worktree list
+ wc -l
4
+ git worktree list --porcelain
+ grep -F /.git/batch-worktrees/
+ echo '第一行 exit=1'
第一行 exit=1
+ git worktree list --porcelain
+ grep -F /batch-worktrees/
worktree …/scratchpad/qa61/decoy/batch-worktrees/x
+ echo '未錨定版 exit=0(decoy 被算進母體)'
未錨定版 exit=0(decoy 被算進母體)
+ git branch --list 'batch/*'
+ git worktree add -q -b batch/47 .git/batch-worktrees/47
+ git worktree list
+ wc -l
5
+ git worktree list --porcelain
+ grep -F /.git/batch-worktrees/
worktree …/scratchpad/qa61/.git/batch-worktrees/47
+ echo '第一行 exit=0'
第一行 exit=0
+ git branch --list 'batch/*'
+ batch/47
+ cd …/scratchpad/qa61/.git/batch-worktrees/47
+ ls -l .git
-rw-r--r-- 1 user 197121 142 Aug 19 14:38 .git
+ ls .git/batch-worktrees
+ echo 'ls 寫法 exit=2(無輸出 = 假綠)'
ls 寫法 exit=2(無輸出 = 假綠)
+ git worktree list --porcelain
+ grep -F /.git/batch-worktrees/
worktree …/scratchpad/qa61/.git/batch-worktrees/47
+ echo '第一行 exit=0'
第一行 exit=0
+ cd …/scratchpad/qa61
+ rm -rf .git/batch-worktrees/47
+ ls .git/batch-worktrees
+ echo 'ls 看到的 exit=0(無輸出 = 假綠)'
ls 看到的 exit=0(無輸出 = 假綠)
+ git worktree list --porcelain
+ grep -F /.git/batch-worktrees/
worktree …/scratchpad/qa61/.git/batch-worktrees/47
+ echo '第一行 exit=0'
第一行 exit=0
+ git worktree remove --force .git/batch-worktrees/47
+ git worktree list --porcelain
+ grep -F /.git/batch-worktrees/
+ echo '第一行 exit=1'
第一行 exit=1
+ git branch --list 'batch/*'
  batch/47
+ echo '第二行 exit=0'
第二行 exit=0
+ git branch -D batch/47
Deleted branch batch/47 (was a5d9bfa).
+ git worktree list --porcelain
+ grep -F /.git/batch-worktrees/
+ echo '第一行 exit=1(還是綠)'
第一行 exit=1(還是綠)
+ git branch --list 'batch/*'
+ echo '第二行 無輸出 = branch 被刪掉了,紅'
第二行 無輸出 = branch 被刪掉了,紅
+ cd …/scratchpad
+ git worktree list --porcelain
+ grep -F /.git/batch-worktrees/
fatal: not a git repository (or any of the parent directories): .git
+ echo '不在 repo 裡 exit=1'
不在 repo 裡 exit=1
```

整理成表(判準第一行 = `git worktree list --porcelain | grep -F /.git/batch-worktrees/`,
第二行 = `git branch --list 'batch/*'`):

| 狀態 | 現場 | 舊判準(`git worktree list` 只剩主 repo) | 定稿判準 |
|---|---|---|---|
| A | 0 lane 殘留,2 subagent worktree + 1 decoy | 4 列 → 判「有殘留」**誤報** | 第一行無輸出 exit 1 → 乾淨 ✅ |
| A-decoy | 同上,但 grep 沒錨定 `.git/` | — | 未錨定版 exit 0,把 `decoy/batch-worktrees/x` 算進母體 → **誤報**;錨定版不會 ✅ |
| B | 1 lane 沒走完 §7 | 5 列 → 判對,但哪一列是 lane 要人挑 | 第一行只印那 1 列 lane 的路徑 ✅ |
| C | 從 linked worktree 裡跑(`.git` 是**檔案**) | — | `ls … 2>/dev/null` exit 2 無輸出 = **假綠**;第一行正確印出 lane ✅ |
| D | 註冊還在、目錄先被 `rm -rf` 掉 | — | `ls` exit 0 無輸出 = **假綠**;第一行抓得到 ✅ |
| A' | 照 §7 `git worktree remove` 收掉,branch 留著 | 4 列 → 一樣誤報 | 第一行無輸出(乾淨)+ 第二行印 `batch/47`(branch 還在)✅ |
| E | 有人把 branch 也一起 `-D` 掉了 | — | 第一行**照樣綠** — 只跑第一行會漏判;第二行無輸出 → 抓到 ✅ |
| — | cwd 不在 repo 裡 | — | `fatal: not a git repository` 印在 stderr,看得見(exit 是 grep 的 1)⚠️ 見 known issue B |

- 狀態 A = 票上寫的**誤報**,狀態 B = 票上寫的**漏報**(「混在既有的 3 列裡看不出來」),兩條都重現、
  都被定稿判準修掉。
- 狀態 A-decoy、C、D 是 code-review 抓到的初稿洞(初稿寫 `ls .git/batch-worktrees 2>/dev/null`、
  grep 沒錨定 `.git/`),定稿一起收掉。
- 狀態 E 是獨立 judge 抓到的:原句 2 是「worktree 移除**且** branch 保留」兩件事,只驗前半就是
  works-but-wrong。定稿補上第二行,E 才紅得起來。

## 步驟 4 — 同型全掃

**尺**:一句判準有沒有把「母體是什麼」寫出來。整份 `skills/build-batch/SKILL.md` 帶母體的判準句:

| 行 | 判準 | 母體 | 判 |
|---|---|---|---|
| 51 | blocker 還開著、或 blocker 不在資料裡的一律留在「還卡著」 | 「這份資料」 | 有界 ✅ |
| 128 | 整批驗證要對「這批**所有票**的覆蓋驗收項聯集」 | 「這批」 | 有界 ✅ |
| 157 | 清場檢查 | 「`.git/batch-worktrees/` 底下」(本次修的) | 有界 ✅ |

3/3。修之前是 2/3。

開票時做過另一把尺(絕對詞)的全掃,5 句命中 1(就是 §9 這句);本輪換成「母體」這把尺重掃,
結論一致 — 另外兩句(§開頭「點頭之前什麼都不動」、§6「不可能互相把對方寫到一半的東西吃進去」)
是敘述 / 設計理由,不是拿來判綠紅的判準,不在這把尺的範圍。

跨 skill 掃,關鍵字比開票時放寬(加了「應該沒有 / 不該還有 / 是空的 / `wc -l` / empty / 沒有殘留 /
沒有東西」,就是 judge 點名沒掃到的那幾種同型寫法):

```text
$ grep -rnE "應該只|只剩|沒剩|應該沒有|不該還有|是空的|應該是空|wc -l|empty|沒有殘留|沒有東西" \
    skills/ docs/disciplines/ AGENTS.md CONTEXT.md README.md
skills/build-batch/batch.py:44        ← self-check 的斷言字串,母體是 §5 那句,有界
skills/build-batch/SKILL.md:8         ← 「說不就乾淨結束,沒有殘留」承諾句,不是判準
skills/build-batch/SKILL.md:157       ← 本次修的判準(「應該沒有輸出」)
skills/build-batch/SKILL.md:163       ← 本次修的理由段(引用舊寫法在解釋為什麼不用)
skills/client-demo/references/pm-interview.md:30
skills/maintain/references/pm-interview.md:30
skills/pm-intake/references/pm-interview.md:30
docs/disciplines/pm-interview.md:30

$ grep -rn "worktree" skills/ --include=SKILL.md | grep -v build-batch
(無)
```

`pm-interview.md` 那 4 筆是同一份 discipline 的正本 + 3 份 skill 複本,句子是「問題設計不能只剩採納」
— 意思無關、不是判準,不動。worktree 只有 `build-batch` 一個 skill 在講,沒有第二處同型判準。

## 步驟 5 — 獨立 judge

開了一個乾淨 subagent,只餵驗收原句 + 步驟 1–4 的證據,不餵實作脈絡。它判:

- **原句 1 fail** — 證據零覆蓋。**採納**,但改成「不在本票範圍」:原句 1 的判準在 §9 前半段(貼批次
  總結那段),是同批 #62 的範圍,本票只動清場那句。本檔開頭已明講不宣稱它 pass。
- **原句 2 works-but-wrong** — 判準只看 worktree、不看 branch,§7 哪天被改成 `remove` + `branch -D`
  照樣全綠。**採納並修掉**:定稿補第二行 `git branch --list 'batch/*'`,新增狀態 E 實測(見步驟 3)。
- **證據 B 標題說「同一時刻兩種判準」但新判準沒真的跑** — **採納**,步驟 2 重跑,新判準的 raw output
  補上了。
- **文件寫「4 列」但貼出來的證據是 6 列** — **採納**,定稿改成註明出處(#53 的 QA 實錄步驟 6),
  步驟 2 也說明兩組數字是同一現象的兩個時點。
- **同型全掃的關鍵字太窄** — **採納**,步驟 4 放寬關鍵字重掃,結論不變。
- **grep 沒錨定 `.git/`,母體比宣稱的大** — **採納**,定稿改成 `grep -F /.git/batch-worktrees/`,
  並加了 decoy 狀態實測(狀態 A-decoy)。
- **pipeline 把 git 的失敗吃掉,exit code 是 grep 的** — **部分採納**,見 known issue B。
- **`grep` exit 1 在 `set -e` 的 script 裡會掛** — 見 known issue C。

## Known issues(非 blocking,帶著 demo)

**A. 沒有自動化 guard。** 這條判準是散文,寫得出來的 guard 只能禁某個字面字串,換一種絕對詞講法就
繞過去 — `docs/disciplines/written-evidence.md` 要求 guard 兩種 mutation 都咬得到,這裡第二種咬不到。
現在靠的是理由段 + `(#61)` 票號防回改,跟 §6 `-u` 那段同型。真要固化,合理形狀是「skill 文件裡的
清場 / 驗證判準必須指名母體」這條 lint,那是另一張票。

**B. `git worktree list --porcelain | grep …` 的 exit code 是 grep 的,不是 git 的。** git 失敗
(cwd 不在 repo、repo 壞了)時 stdout 空 → grep exit 1 → 判準讀成「收乾淨了」。實測見步驟 3 最後一段:
`fatal: not a git repository` 有印在 stderr 上、人看得見,所以不是靜默假綠(這點跟被 `2>/dev/null`
吃掉的 `ls` 不同,定稿的措辭已經改成講這個差別);但如果哪天有人把這行塞進 script 只看 exit code,
它就會假綠。修法是 `set -o pipefail` 或先把 git 輸出存起來再 grep,不在本票範圍。

**C. `grep` 回 exit 1 在 `set -e` 的 script 裡會直接中斷。** 文件把 exit 1 當正常,那是給人 / agent
讀 checklist 的語境;抄進 script 的話乾淨狀態會變成 script 失敗。跟 B 同一個修法、同一張後續票。

## 未涵蓋範圍

1. **`/build-batch` 真跑一輪把 §9 走到。** 本輪驗的是判準本身在六種 worktree 狀態下的行為,不是
   「跑完一整批之後 §9 印出來的樣子」。那需要 client 點頭 + 三個 lane 真的跑完,跟 #53 QA 的第 1 條
   未涵蓋範圍是同一個缺口。
2. **原句 1(票上產出紀錄 + spec 票批次總結)。** 判準在 §9 前半段,同批 #62 的範圍,本票沒碰。
3. **非 Windows / 非 Git-for-Windows 的路徑分隔符。** `--porcelain` 在本機印 forward slash
   (步驟 2、3 兩處都證實),`grep -F /.git/batch-worktrees/` 因此成立;別的 shell 環境沒測。

## 附錄 — `qa61.sh` 全文

```bash
set -x
PS4='+ '
R="$SP/qa61"
rm -rf "$R"; mkdir -p "$R"; cd "$R"
git init -q -b main .
git config user.email qa@example.com
git config user.name QA
echo hi > README.md
git add README.md
git commit -qm init
git worktree add -q -b research/fake-a .claude/worktrees/agent-aaaa
git worktree add -q -b research/fake-b .claude/worktrees/agent-bbbb
mkdir -p "$R/decoy/batch-worktrees"
git worktree add -q -b decoy/x "$R/decoy/batch-worktrees/x"
# ===== 狀態 A:0 個 lane 殘留 =====
git worktree list
git worktree list | wc -l
git worktree list --porcelain | grep -F /.git/batch-worktrees/
echo "第一行 exit=$?"
git worktree list --porcelain | grep -F /batch-worktrees/
echo "未錨定版 exit=$?(decoy 被算進母體)"
git branch --list 'batch/*'
# ===== 狀態 B:1 條 lane 沒走完 §7 =====
git worktree add -q -b batch/47 .git/batch-worktrees/47
git worktree list | wc -l
git worktree list --porcelain | grep -F /.git/batch-worktrees/
echo "第一行 exit=$?"
git branch --list 'batch/*'
# ===== 狀態 C:從 linked worktree 裡跑(.git 是檔案)=====
cd "$R/.git/batch-worktrees/47"
ls -l .git
ls .git/batch-worktrees 2>/dev/null
echo "ls 寫法 exit=$?(無輸出 = 假綠)"
git worktree list --porcelain | grep -F /.git/batch-worktrees/
echo "第一行 exit=$?"
# ===== 狀態 D:註冊還在、目錄先沒了 =====
cd "$R"
rm -rf .git/batch-worktrees/47
ls .git/batch-worktrees
echo "ls 看到的 exit=$?(無輸出 = 假綠)"
git worktree list --porcelain | grep -F /.git/batch-worktrees/
echo "第一行 exit=$?"
# ===== 狀態 A':照 §7 收掉 worktree、branch 留著 =====
git worktree remove --force .git/batch-worktrees/47
git worktree list --porcelain | grep -F /.git/batch-worktrees/
echo "第一行 exit=$?"
git branch --list 'batch/*'
echo "第二行 exit=$?"
# ===== 狀態 E:branch 也被誤刪(原句 2 後半的紅路徑)=====
git branch -D batch/47
git worktree list --porcelain | grep -F /.git/batch-worktrees/
echo "第一行 exit=$?(還是綠)"
git branch --list 'batch/*'
echo "第二行 無輸出 = branch 被刪掉了,紅"
# ===== git 自己失敗時看不看得見 =====
cd "$SP"
git worktree list --porcelain | grep -F /.git/batch-worktrees/
echo "不在 repo 裡 exit=$?"
```
