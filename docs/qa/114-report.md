# #114 QA 報告

受測物:`batch/113` @ `30570d3`(交付版)。
walkthrough 實錄:[`114-walkthrough.md`](114-walkthrough.md)。

## 白話摘要

#113 交出去的那版,`skills/build/SKILL.md` 裡那條「怎麼確認自己做完了」的指令寫壞了
—— 它把票號寫成 `#113` 這種形式,而 `#` 在 bash 跟 PowerShell 裡都是「這行後面是註解」
的意思。所以照著複製貼上的人,實際跑到的是一條沒帶參數的空指令,而回來的錯誤訊息
(`accepts 1 arg(s), received 0`)看起來像工具壞了,不像指令抄錯 —— 人只會去查工具。

這次把那行改對了,而且把「照抄的指令貼下去要跑得動」這件事**變成機器會自動檢查的
規則**,而不是靠下一個人記得。QA 這關做的是:真的把那行指令從檔案裡挖出來、代換、
貼進兩種 shell 跑一次(bash 跟 PowerShell 各一次),然後另外寫一把**不看新規則怎麼寫**
的獨立尺,問真正的 shell「這行有沒有東西被吃掉」,兩邊答案要一致。

結果:四條驗收全過,獨立 judge 也判全過,**沒有 blocking**。有一條 known issue 跟
兩條已知取捨要 client 收尾時決定。

## 判定

| # | 驗收原句(#114 完工定義) | judge 判定 |
| --- | --- | --- |
| 1 | `skills/build/SKILL.md:37` 的指令代換後照字面貼上去跑得動 | **pass** |
| 2 | 改完之後對交付版再走一次 `/writing-for-agents`,結果寫進票(逐條 finding) | **pass** |
| 3 | `python scripts/validate.py` 綠 | **pass** |
| 4 | 重跑 `/qa #113` | **pass** |

judge 第一輪把第 4 條判 works-but-wrong(「只複驗三條 finding,沒拿 #113 的驗收清單
實測」)。那是 QA 少餵了一塊證據 —— #113 的完工定義除了三條 finding,還要求**兩份**
SKILL.md 各留走查紀錄。補上 `skills/qa/SKILL.md` 的 md5 對照(交付版與走查當時那版
逐位元相同,所以那份走查天然走在交付內容上)之後,judge 改判 pass。

## Blocking

**無。**

## Known issues(非 blocking,處置由 client 在 demo 收尾決定)

### K1 —— 新守門的母體漏掉 `docs/agents/` 與 `README.md`,而排除理由沒寫

`pasteable_command_issues` 的母體是 `skills/` + `docs/specs/`。`AGENTS.md` 的
「受檢範圍」只寫了 `docs/qa/` 為什麼不在內(QA 紀錄要逐字引用壞掉的指令當證據)。
母體外還有:

| 位置 | 給人照抄的指令 | 目前壞的 | 排除理由有寫嗎 |
| --- | --- | --- | --- |
| `docs/agents/` | 8 條 | 0 | **沒有** |
| `README.md` | 2 條 | 0 | **沒有** |
| `AGENTS.md` | 10 條 | 1(`:101` 是故意的反例) | **沒有**,但理由與 `docs/qa/` 同型 |

`docs/agents/issue-tracker.md:8` 就是 `AGENTS.md` 跟 `skills/build/SKILL.md:37`
一起指過去的 canonical form 來源(`gh issue view <number> --comments`)—— 定義正確
寫法的那個檔,自己不在守門範圍內。

現在那 8 條都是好的,所以不 blocking。但這正是 #114 的 root cause 原封不動的形狀:
**沒有守門的位置會被反覆改壞,而 validate 全程報綠。** 沒寫下來的排除,下一輪讀起來
就像「已經蓋到了」。

**建議觸發點**:下一張碰 `AGENTS.md` 受檢範圍那一節、或碰 `docs/agents/` 的票。
兩個處置方向(擇一即可,不用兩個都做):把 `docs/agents/` + `README.md` 收進母體
(那 10 條現在都是好的,收進去當下就綠);或把排除理由補寫進「受檢範圍」那一段。

### K2 —— `/writing-for-agents` 走查的 minor finding(build `:3` identity 重複)

票上走查表第 2 列:frontmatter `:3` 的「tdd、typecheck、測試、commit 全依原件」與
`:8` 同一個意思寫兩次,照走查判準該剪,但判定不動。理由是這行剛在前一手被
code-review 定案回原句型,第三次重寫同一行就是來回震盪。

QA 覆核:理由成立,且不影響任何驗收句。**建議觸發點**:下一張為別的理由動
`skills/build/SKILL.md` frontmatter 的票,順手併掉。

### K3 —— #113 那輪 `qa/SKILL.md` 走查帶出、明確不在 #113 範圍的 5 條

`qa/SKILL.md:63`(pointer 沒 target)、`:96`(報告契約沒列 judge 逐條判定)、
`:50` 與 `:30` 逐字重複、`:75` 與 §3 標題重複、`:42` vs `:73`(judge 開的時機含糊)。

#113 票上已明寫「不在完工定義內,建議另開票」,#114 也沒有涵蓋。**建議觸發點**:
開一張獨立的 `skills/qa/SKILL.md` 走查 finding 票 —— 這 5 條已經跨兩輪沒有票號綁著,
再放一輪就會變成「看起來像已知風險、實際上沒人負責」的那種殘留。

## 未涵蓋範圍(每條都有下文)

| 未涵蓋 | 下文 |
| --- | --- |
| ` ```bash ` 圍籬區塊裡的指令 | **接受不蓋**。`AGENTS.md:111-118` 已宣告為天花板,QA 步驟 4 實測確認它是「少咬」不是「多咬」,靠 review 擋。要收進來得寫 shell parser,不划算 |
| 命令字表(`gh`/`git`/`python`/`bash`/`sh`/`ls`/`grep`)外的指令(`curl`、`npm`) | **接受不蓋**。同上,已宣告且實測為 false negative。repo 現在一條 `curl`/`npm` 都沒有 |
| 指令裡未配對的單撇號會吞掉後面的 `#` | **接受不蓋**。同上,實測確認少咬 |
| 母體外的 `docs/agents/` / `README.md` / `AGENTS.md` | **綁 K1**,見上 |
| Tauri 原生殼(tray / global hotkey / updater) | **不適用**。這片是散文 + Python 守門,沒有原生殼 |
| Web UI / Playwright a11y snapshot | **不適用**。這片沒有 web UI。等價證據見 walkthrough 的可重跑 transcript |
| `scripts/qa/*-sweep.py` 那 12 支 | **接受不跑**。`scripts/qa/README.md` 已明訂它們釘的是 #96 之前的舊判準,留作歷史紀錄,不列入 regression |

## Demo 實錄清單(每條驗收項一段)

一鍵重跑整套:

```
bash scripts/qa/114-walkthrough.sh "$(mktemp -d)/qa114"
```

| 驗收項 | 實錄段落 | 路徑 |
| --- | --- | --- |
| 1 指令貼上去跑得動 | A1(交付版)+ A2(修前對照組) | `docs/qa/114/walkthrough-transcript.txt` |
| 1 PowerShell 那一面 | A2b | `docs/qa/114/powershell-transcript.txt` |
| 2 交付版走過 writing-for-agents | 步驟 3(md5 + 13 個行號逐一比對) | `docs/qa/114-walkthrough.md` 步驟 3、`docs/qa/114/delivered-md5.txt` |
| 3 validate 綠 | A3 + A4(修前對照) | `docs/qa/114/walkthrough-transcript.txt` |
| 3 第二把尺(oracle 獨立) | A5 | `docs/qa/114/wide-delivered.txt`、`docs/qa/114/wide-prefix.txt` |
| 4 重跑 `/qa #113` | A6 | `docs/qa/114/walkthrough-transcript.txt`、`docs/qa/114-walkthrough.md` 步驟 2 A6 |

## QA 這輪自己踩到的兩個坑(留給下一輪)

兩個都是「工具沒在跑,而輸出跟全綠一模一樣」:

1. 修前對照第一次跑回「0 筆」。不是守門失效 —— Windows 的 Python 把 MSYS 的 `/tmp`
   解成 `C:\tmp`,對照組整個沒讀到檔。**沒讀到檔**跟**真的沒問題**都印 0。
   `114-walkthrough.sh` 現在用 `cygpath -w` 轉原生路徑,並在讀之前 assert 檔案存在。
2. 第二把尺第一版是啞的。PATH 上的 `bash` 在這台解到壞掉的 WSL bash
   (`execvpe(/bin/bash) failed`),659 個 span 全落進「沒送進 bash」桶,而報表印
   「被吃掉 0 筆」。`114-paste.py` 現在開頭用已知壞 / 已知好的兩條指令自檢,
   兩面都對才承認那支 bash 能當尺,不然直接死。
