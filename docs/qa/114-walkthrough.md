# #114 QA walkthrough

受測物:`batch/113` @ `30570d3`(交付版),`skills/build/SKILL.md` md5
`8273504c9126b23d1ca0c62c837adb47`。

範圍 = #114 的四條完工定義(bug fix 票:重現 scenario + regression suite)。

一鍵重跑:

```
bash scripts/qa/114-walkthrough.sh "$(mktemp -d)/qa114"
```

exit 0 = 六格全對。完整 transcript 存在 `docs/qa/114/walkthrough-transcript.txt`。

這片沒有 web UI —— 交付物是散文(`skills/build/SKILL.md`)+ 守門
(`scripts/validate.py`)。所以「a11y snapshot」的等價物是每格一段**可重跑的實測
transcript**:指令 + 真實輸出 + 引用到的散文原文行號。

---

## 步驟 1 — Regression 先跑

| lane | 結果 |
| --- | --- |
| `python scripts/validate.py` | exit 0,`OK validate green` |
| `python scripts/validate.py --self-check` | exit 0,含新的 30-span mutation 層 |
| `python scripts/qa/97-mutate.py --run` | 15/15 knob 被咬住 |
| `python scripts/qa/107-mutate.py --run` | 8/8 knob 被咬住 |
| `python scripts/qa/96-newrule-probe.py .` | `OK 新規則下全綠`,不合 0 |

全綠,沒有 blocking regression。

`scripts/qa/README.md` 列的 12 支 `*-sweep.py` 照該檔說明**不列入目前的
regression**(fixture 釘的是 #96 之前的舊判準),本輪沿用。

---

## 步驟 2 — Walkthrough(六格)

### A1 —— 完工定義 1:交付版的指令代換後照字面貼進 bash

指令**不是手打的**:用程式從交付檔第 37 行原地抽出反引號 span,把 `<N>` 代換成
`113`,再直接丟進 bash。手打測的是我打了什麼,不是檔案寫了什麼。

```
抽出的指令(代換 <N> -> 113):gh issue view 113 --comments
OK   A1 貼進 bash 跑得動 (0)
author:	c3lew
association:	owner
```

有真實 stdout,不是只有 exit code。

`skills/build/SKILL.md:37` 原文逐字:

> 完成標準:未 push 的 commit 數是 `0`,`gh issue view <N> --comments` 兩則 comment(產出、交棒)都看得到,且 §4 適用時交付物的散文照它走過一次,才結束 session。

同檔 `:31` 另外兩條指令一併照字面貼過:`git push` → `Everything up-to-date`
(exit 0);`git rev-list --count origin/batch/113..HEAD` → `0`(exit 0)。

### A2 —— 對照組:修前那版走同一條路

```
抽出的指令:gh issue view #113 --comments
accepts 1 arg(s), received 0
```

這格證明 A1 的 pipeline 抓得到這個 bug,不是「怎麼跑都綠」。

### A2b —— PowerShell 7 同兩條(手動,存在 `docs/qa/114/powershell-transcript.txt`)

```
PS> gh issue view 113 --comments      -> author: c3lew …
PS> gh issue view #113 --comments     -> accepts 1 arg(s), received 0
```

兩個 shell 都覆蓋到,對上票上「bash 與 PowerShell 都被當註解吃掉」的宣稱。

### A3 —— 完工定義 3:regression(同步驟 1)

### A4 —— 修前對照(`/qa` §2 要求:改判準的票要跑修前對照)

新守門 `pasteable_command_issues` 拿去跑**修之前那個 commit**(`0de51ec`)的
`git archive` 副本:

```
修前: 1 筆
    skills/build/SKILL.md: pasteable command `gh issue view #N --comments` has a
    `#`-prefixed argument — bash and PowerShell both read it as a comment, so the
    pasted line runs without it
交付版: 0 筆
```

差額剛好是那一行,**沒有本輪引入的新誤判**。這格也排除「加一條永遠不會 fire 的
規則換綠燈」—— 綠是因為 bug 被修掉,不是因為規則瞎。

> 踩過的坑(留給下一輪):第一次跑這格回「修前 0 筆」,不是守門失效,是 Windows
> 的 Python 把 MSYS 的 `/tmp` 解成 `C:\tmp`,對照組整個沒讀到檔。**沒讀到檔**跟
> **真的沒問題**在輸出上長得一模一樣,都是 0。script 現在用 `cygpath -w` 轉原生
> 路徑,並在讀之前 assert 檔案存在。

### A5 —— 第二把尺(`/qa` §1 的 oracle 獨立性)

受測物就是判準(`pasteable_command_issues`),它綠只證明它同意自己。所以另寫
`scripts/qa/114-paste.py`:**不套**受測守門的任何規則(不用命令字表、不用引號
配對、不用「`#` 前面要有空白」),改把每個反引號 span 交給**真的 bash** 做 word
splitting(`set -- <span>`,只設參數不執行),比對「照空白硬切的 token 數」與
「bash 實際看到的 token 數」,少了就是 shell 吃掉了東西。

母體刻意寫寬:`skills/` + `docs/specs/` + `docs/agents/` + `AGENTS.md`,每一個
反引號 span 都掃,不先篩。

| 樹 | span 數 | 被吃掉 | `build/SKILL.md:37` |
| --- | --- | --- | --- |
| 修前 `0de51ec` | 629 | 63 筆 | **在**(照空白 5 token,bash 只看到 3) |
| 交付版 `30570d3` | 659 | 70 筆 | **不在** |

兩把互相獨立的尺對同一件事給同一個答案。

> 這把尺自己也差點說謊:PATH 上的 `bash` 在這台解到壞掉的 WSL bash
> (`execvpe(/bin/bash) failed`),第一版跑出來 659 個 span 全落進「沒送進 bash」
> 桶,而報表印的是「被吃掉 0 筆」—— 跟全綠一模一樣。現在 `resolve_bash()` 開頭
> 拿已知壞 / 已知好的兩條指令自檢,兩面都對才承認這支 bash 能當尺,不然直接死。

#### 交付版那 70 筆的逐筆判讀(寬尺的多餘項)

| 類別 | 筆數 | 判讀 |
| --- | --- | --- |
| `/qa #N`、`/build #47`、`/client-demo #N` 這種 **Claude Code slash command** | 約 50 | 誤報。不是 shell 指令,不會被貼進 shell |
| markdown / 散文片段:`## Parent`、`## Blocked by`、`# Concept Name`、`#42`、`#<n>`、單獨一個 `#` | 約 12 | 誤報。不是指令 |
| `docs/agents/issue-tracker.md:25` `` `Blocked by: #<n>` `` | 1 | 誤報。issue body 的欄位格式 |
| `skills/tracking-viz/SKILL.md:42` `` `<code>/skill #N</code>` `` | 1 | 誤報。產出的 HTML 片段 |
| `AGENTS.md:101` `` `gh issue view #N` `` | 1 | 誤報。規則文件裡**故意寫的反例**(原文:「不要寫 `gh issue view #N`」) |
| `AGENTS.md:114` `` `git commit -m "fix #113"` `` | 1 | 誤報。引號包住,shell 當字串保留;寬尺的「照空白硬切」比法本來就會多算一個 |

70 筆全部判為誤報,**沒有一筆是真的壞指令**。

### A6 —— 完工定義 4:重跑 `/qa #113`

#113 的完工定義原句只有三個 clause:

> 三條都改完,兩份 SKILL.md 各再走一次 `/writing-for-agents` 並把結果寫進票(AC5 要的是可覆核的紀錄,不是自我宣稱),`python scripts/validate.py` 綠。

逐 clause 複驗:

| clause | 複驗方式 | 結果 |
| --- | --- | --- |
| (a) 三條 finding 改完 | 交付版逐條讀現文 + `113-wide.py` 第二把尺 | pass,`skills/build/SKILL.md` 零筆 |
| (b) **兩份** SKILL.md 各留可覆核走查紀錄 | 見下 | pass |
| (c) `validate.py` 綠 | 步驟 1 | pass |

clause (a) 逐條:

| # | #113 的 finding | 交付版現況 | 判定 |
| --- | --- | --- | --- |
| 1 | `build/SKILL.md:12` 的 `§2` 是 stale | 現文「改照 §2(原件序列的那一步不照跑),跑完接 §3 收尾;寫交付物的當下照 §4」 | pass |
| 2 | `build/SKILL.md:8` 自我描述跟本體打架 | 現文「本檔只補三個 delta」,對上正文三個 `(delta)` 標題 | pass |
| 3 | `qa/SKILL.md:79` 「唯一一條」無界全稱詞 | 整句已刪 | pass |

clause (b) 的「兩份」:

- `skills/build/SKILL.md` —— #114 重走了一次(見步驟 3),走查對象 md5 實測
  `8273504c9126b23d1ca0c62c837adb47` = 交付版。
- `skills/qa/SKILL.md` —— #113 之後沒再被改過(`30570d3` 只動 `AGENTS.md`、
  `scripts/validate.py`、`skills/build/SKILL.md`)。md5 實測:

  ```
  交付版           -> b18a13e2f1f9e82e3798ab1beb644e69
  走查當時(d58a0d5) -> b18a13e2f1f9e82e3798ab1beb644e69
  ```

  逐位元相同 —— 那份走查走的就是現在的交付內容,不存在 #114 finding 2 那種
  「走查跑在舊版上」的問題。

---

## 步驟 3 — 完工定義 2 的獨立查核(不採信票上的句子)

票上的 `/writing-for-agents` 走查 comment 宣告對象 md5 是
`8273504c9126b23d1ca0c62c837adb47`,並列 10 列逐 lever 判定(1 條 minor finding
判定不動 + 附理由,其餘 9 項 pass),沒有寫成一句「已通過」。

QA 實跑查核兩件事:

1. 交付檔實測 md5 = `8273504c9126b23d1ca0c62c837adb47`,與宣告對象一致 ——
   正面關掉「走查跑在舊版」這個失效模式。
2. 走查表引用的 13 個行號(`:3`、`:8`、`:12`、`:16`、`:18`、`:21`、`:24`、`:25`、
   `:31`、`:33`、`:35`、`:37`、`:42`)逐一比對交付檔,**每一個都落在它宣稱的
   內容上** —— 表示這份走查真的讀過這個檔,不是照抄舊版行號。

---

## 步驟 4 — 守門「宣告過的天花板」實測

`AGENTS.md:111-118` 宣告了三條天花板。實測它們是不是真的如所宣稱 ——
關鍵是**少咬(false negative)**,不是多咬(false positive):

| 宣告 | 測試輸入 | 實得 |
| --- | --- | --- |
| ` ```bash ` 圍籬區塊看不到 | 圍籬裡放 `gh issue view #N --comments` | 沒咬到 ✔ 少咬 |
| 命令字表外的看不到 | `` `curl -s #N https://x` ``、`` `npm run #N` `` | 沒咬到 ✔ 少咬 |
| 引號配對是字面比對,單撇號會吞掉後面的 `#` | `` `gh issue view don't #N can't` `` | 沒咬到 ✔ 少咬 |

反面對照(該咬的要咬、不該咬的不咬):

| 輸入 | 實得 |
| --- | --- |
| `` `gh issue view #N --comments` `` | 咬到 ✔ |
| `` `git commit -m "fix #113"` ``(引號內) | 沒咬到 ✔ |
| `` `git log --grep=#113` ``(貼著 token) | 沒咬到 ✔ |

三條天花板全部是「少咬」,**沒有一條是多咬** —— 與 `AGENTS.md` 的宣告一致。

順帶查核票上的量測宣稱:mutation 層實掃 **30 個 span / 9 個檔**,與票上寫的
數字一致。

---

## 步驟 5 — 同型全掃

### 掃法 1:票上那條 grep,今天重跑

```
$ grep -rnoE '`[^`]*\b(gh|git|python|bash|sh|node|npm)\b[^`]*#[A-Za-z0-9<]+[^`]*`' skills/ docs/specs/
(0 hits)
```

母體內零筆,票上「全 repo 1 筆、沒有第二處同形狀」的宣稱在交付版上成立。

### 掃法 2:把尺放大到守門母體**外**

同型不只是「同一份檔案裡的同形狀句子」,還有「同一個 class 但守門看不到的地方」。
`pasteable_command_issues` 的母體是 `skills/` + `docs/specs/`,母體外掃到:

| 位置 | 給人照抄的指令 span | 目前壞的 | 排除理由有沒有寫在 `AGENTS.md` 的「受檢範圍」 |
| --- | --- | --- | --- |
| `docs/qa/` | 多 | — | **有**:「QA 紀錄本來就要逐字引用壞掉的指令當證據」 |
| `AGENTS.md` | 10 | 1(`:101` 是故意的反例) | **沒有**,但理由與 `docs/qa/` 同型(規則文件要引用反例) |
| `docs/agents/` | 8 | 0 | **沒有** |
| `README.md` | 2 | 0 | **沒有** |

`docs/agents/issue-tracker.md:8` 就是 `AGENTS.md` 與 `skills/build/SKILL.md:37`
一起指過去的 **canonical form 來源**(`gh issue view <number> --comments`),而它在
守門母體外。目前那 8 條都是好的,所以這條**不 blocking**;但這正是 #114 的 root
cause 原封不動的形狀 —— 沒有守門的位置會被反覆改壞,而 validate 全程報綠。列為
known issue,見報告。

---

## 步驟 6 — 獨立 judge

乾淨 subagent,只餵 #114 四條驗收原句 + 上面的證據,不餵實作脈絡與本 session 的
判斷。逐條判 pass / fail / works-but-wrong。

判定見 `docs/qa/114-report.md`。
