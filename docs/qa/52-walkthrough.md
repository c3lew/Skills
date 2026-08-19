# QA walkthrough — #52 build-batch 1/6:算出誰能同時開,列名單等點頭

驗收 oracle(票上「覆蓋驗收項」原句):

1. 有 4 張票、其中 3 張彼此不卡、1 張卡在別人後面 → 跑指令,名單**只列那 3 張**,卡住的那張不在名單裡,並停下來等 client 點頭。
2. 只有 1 張票能跑時跑這指令 → 直接告訴 client「沒必要開批次,用 `/build #N`(Codex: `$build #N`)就好」。
3. 能跑的超過 3 張 → 只開 3 張,其餘排隊。(本票只到「只開 3 張、其餘排隊」)

環境:`D:/Self Project/Skills`,HEAD = `7cb2be2`,working tree 乾淨。
本票是 CLI 純函式 + skill 文件,沒有 UI,不走 Playwright;本檔是每條驗收項共用的終端實錄。

一鍵重開(沿用既有 CLI QA 入口):

```bash
cd "D:/Self Project/Skills"
python scripts/validate.py --self-check
python scripts/validate.py
python scripts/batch.py --self-check
python scripts/hooks/triage-to-maintain.py --self-check
```

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

$ python scripts/hooks/triage-to-maintain.py --self-check
OK triage-to-maintain self-check green
exit 0
```

既有 regression 全綠。

## 步驟 2 — 驗收 1:4 張票、3 張不卡、1 張卡著

照 SKILL.md §3 的指令逐字跑(`<skill dir>` = `skills/build-batch`):

```text
$ python -c "
import json,sys; sys.path.insert(0,'skills/build-batch')
from batch import plan_batch, format_plan
data=json.load(sys.stdin)
print(format_plan(plan_batch(data['tickets']), {int(k):v for k,v in data['titles'].items()}))
" <<'JSON'
{"tickets": [{"number": 60, "state": "open", "blocked_by": []},
             {"number": 61, "state": "open", "blocked_by": []},
             {"number": 62, "state": "open", "blocked_by": []},
             {"number": 63, "state": "open", "blocked_by": [60]}],
 "titles": {"60": "登入頁", "61": "設定頁", "62": "通知", "63": "登入後導向"}}
JSON
```

實際輸出(終端逐字,`cp950` 主控台):

```text
�n�}(3 �i):
  #60 登入頁
  #61 設定頁
  #62 通知
�ƶ�(0 �i):
  (�L)
�٥d��(1 �i):
  #63 登入後導向 �X �d�b #60
```

同一份輸入,加 `PYTHONIOENCODING=utf-8` 後的輸出:

```text
要開(3 張):
  #60 登入頁
  #61 設定頁
  #62 通知
排隊(0 張):
  (無)
還卡著(1 張):
  #63 登入後導向 — 卡在 #60
```

分段內容正確:「要開」3 張是 #60/#61/#62,#63 不在裡面、落在「還卡著」且寫得出卡在 #60。
但**照 SKILL.md 逐字跑出來的那份**,三段標題與「卡在」字樣是壞碼(見 QA 報告 blocking #1)。

## 步驟 3 — 驗收 2:只有 1 張能跑

```text
$ (同上指令,輸入改為)
{"tickets": [{"number": 70, "state": "open", "blocked_by": []},
             {"number": 71, "state": "open", "blocked_by": [70]},
             {"number": 72, "state": "open", "blocked_by": [70]}],
 "titles": {"70": "地基", "71": "接 UI", "72": "接 API"}}

要開(1 張):
  #70 地基
排隊(0 張):
  (無)
還卡著(2 張):
  #71 接 UI — 卡在 #70
  #72 接 API — 卡在 #70
```

`plan_batch` 回 `ready` 長度 1,SKILL.md §4 第一條規定此時印
「沒必要開批次,用 `/build #47`(Codex: `$build #47`)就好」並結束、不問點頭。
逐字現況:

```text
- **只有 1 張能跑** → 印「沒必要開批次,用 `/build #47`(Codex: `$build #47`)就好」,結束,不問點頭。
```

措辭與 dual-write baton 都在(`python scripts/validate.py` 綠已覆蓋 baton 檢查)。

## 步驟 4 — 驗收 3:能跑的超過 3 張

輸入 8 張:5 張互不相卡(#80–#84)、1 張卡在 open 票後面(#85→#80)、
1 張已關(#86)、1 張卡在已關票後面(#87→#86,應放行)。

```text
要開(3 張):
  #80 a
  #81 b
  #82 c
排隊(3 張):
  #83 d
  #84 e
  #87 g(卡在已關的 86)
還卡著(1 張):
  #85 f — 卡在 #80
```

「要開」剛好 3 張、其餘進「排隊」、已關 blocker 放行、closed 票 #86 本身不出現在任何一段。

## 步驟 5 — 真實資料端到端(§1 → §2 → §3)

`gh issue list --state all --limit 200 --json number,state,body,labels,title`,
篩 `## Parent` 指向 #51 的票,解 `## Blocked by`,餵進 `plan_batch`:

```text
候選票數: 6
  57 OPEN ['ready-for-agent'] [52]
  56 OPEN ['ready-for-agent'] [53]
  55 OPEN ['ready-for-agent'] [53]
  54 OPEN ['ready-for-agent'] [53]
  53 OPEN ['ready-for-agent'] [52]
  52 OPEN ['ready-for-agent'] []

要開(1 張):
  #52 build-batch 1/6:算出誰能同時開,列名單等 client 點頭
排隊(0 張):
  (無)
還卡著(5 張):
  #53 build-batch 2/6:… — 卡在 #52
  #54 build-batch 3/6:… — 卡在 #53
  #55 build-batch 4/6:… — 卡在 #53
  #56 build-batch 5/6:… — 卡在 #53
  #57 build-batch 6/6:… — 卡在 #52
```

(6 張候選全列,無截斷。)

## 步驟 6 — 「點頭前什麼都不動」

純函式(不碰 gh / git / 檔案系統)的可重跑檢查:

```text
$ grep -nE "^import|^from|subprocess|os\.|open\(|shutil|Popen" skills/build-batch/batch.py
17:import sys
18:from pathlib import Path
exit 0

$ sed -n '/^def plan_batch/,/^def format_plan/p' skills/build-batch/batch.py     | grep -nE "subprocess|os\.|open\(|shutil|Popen|Path|gh |git "
(無輸出)
exit 1   # grep 沒撈到 = plan_batch 函式體內完全沒有這些呼叫

$ python -c "import sys;sys.path.insert(0,'skills/build-batch');import batch,inspect;  src=inspect.getsource(batch.plan_batch);  print('Path' in src, 'open(' in src, 'subprocess' in src, 'os.' in src)"
False False False False
exit 0
```

`pathlib.Path` 在檔案頂端 import 是給 `self_check()` 讀 SKILL.md 用的(咬合斷言),
`plan_batch` 函式體內沒有它 — 上面第二、三條指令就是在證這件事。
- 跑完上述全部步驟後 `git status --porcelain` 空、`git worktree list` 只有跑之前就在的
  3 個 research worktree(locked,分別在 `research/*` 分支),沒有新增。
- SKILL.md §5 逐字:「**說不** → 乾淨結束。什麼都沒開、什麼都沒改,不用回收。」

## 步驟 7 — agent 端逐字走完 `/build-batch #51`(真實資料,ready = 1)

前面步驟 3 只跑了 `plan_batch`;這一步是**照 SKILL.md §1 → §4 當成 agent 完整走一遍**,
記錄 client 實際會看到的畫面。

```text
$ gh issue list --state all --limit 200 --json number,state,body,labels,title
$ (§1 篩:open + ready-for-agent + ## Parent 指向 #51,closed 票一併餵進去當 blocker 狀態)
$ (§2 解 ## Blocked by → #<n>)
$ (§3 餵進 plan_batch)

ready = [52] queued = [] blocked = [(53, [52]), (54, [53]), (55, [53]), (56, [53]), (57, [52])]

→ len(ready) == 1,走 §4 第一條岔路。agent 對 client 說的話:

  沒必要開批次,用 `/build #52`(Codex: `$build #52`)就好

  (結束,不印三段名單、不問點頭)
```

跑完之後:`git status --porcelain` 只有本 QA 檔一個 untracked,`git worktree list` 4 行
(主線 + 跑之前就在的 3 個 locked `research/*` worktree),沒有新增。

(SKILL.md §4 的字面寫 `/build #47` 是例子裡的票號,agent 代入的是實際的 #52 — 上面的
輸出就是代入後的結果。)

## 步驟 8 — agent 端走「印名單 → 停下等點頭 → client 說不」

用步驟 2 的 4 張票資料,照 §3 印完名單後 agent 實際停在哪:

```text
要開(3 張):
  #60 登入頁
  #61 設定頁
  #62 通知
排隊(0 張):
  (無)
還卡著(1 張):
  #63 登入後導向 — 卡在 #60

→ agent 停在這裡問 client:「這幾張要一起推嗎?」
```

問句印出後控制權交回 client,agent 沒有再往下跑任何一步。
**client 說「不」** → 直接結束;結束後的殘留檢查:

```text
$ git status --porcelain
(除了本 QA 檔 docs/qa/52-walkthrough.md 外沒有異動)

$ git worktree list
D:/Self Project/Skills                                           7cb2be2 [main]
D:/Self Project/Skills/.claude/worktrees/agent-a1774032b0e17d127 [research/context-smart-zone] locked
D:/Self Project/Skills/.claude/worktrees/agent-a1ce94f5bd5097fdc [research/company-vs-solo-agent] locked
D:/Self Project/Skills/.claude/worktrees/agent-aa8443950469b0c07 [research/agent-user-pov-qa] locked
(3 個 locked worktree 是本輪 QA 開始前就在的 research worktree,不是這次產生的)
```

沒有 worktree、沒有檔案異動、沒有票被改 — 無回收動作可做。
本輪 QA 由 agent 扮演 client 走這條路徑(AFK,沒有真人按鍵);真人「說不」的按鍵手感由
`/client-demo` 把關。

## 未涵蓋

- 「說好」之後的平行開工 / worktree / 合併 — 本票明講不做,由 #53–#56 驗。
- 沒有 UI,無視覺 oracle,不走 Playwright。
- 「說不 / 說好」由 agent 扮演 client 走(AFK),真人操作手感留給 `/client-demo`。
