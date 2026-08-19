# QA walkthrough — #52 build-batch 1/6:算出誰能同時開,列名單等 client 點頭

第 2 輪(第 1 輪判 works-but-wrong,開 #58「名單在 cp950 主控台是壞碼」;#58 已修完結案)。

環境:`D:/Self Project/Skills`,HEAD = `dd9675a`,跑 QA 時 working tree 乾淨(唯一的異動就是本檔)。
`python -c "import sys;print(sys.stdout.encoding)"` → `cp950` — 跟第 1 輪、跟開 #58 時同一台、同一個 codepage。
本票是 CLI 純函式 + skill 文件,沒有 UI、沒有視覺 oracle,不走 Playwright;本檔是終端實錄。

判定 oracle = 票上「覆蓋驗收項」三條原句:

1. 有 4 張票、其中 3 張彼此不卡、1 張卡在別人後面 → 跑指令,名單**只列那 3 張**,卡住的那張不在名單裡,並停下來等 client 點頭。
2. 只有 1 張票能跑時跑這指令 → 直接告訴 client「沒必要開批次,用 `/build #N`(Codex: `$build #N`)就好」。
3. 能跑的超過 3 張 → 只開 3 張,其餘排隊。

一鍵重開(沿用既有 CLI QA 入口):

```bash
cd "D:/Self Project/Skills"
python scripts/validate.py
python scripts/validate.py --self-check
python scripts/batch.py --self-check
python skills/build-batch/batch.py --self-check
python scripts/install.py --self-check
python scripts/hooks/triage-to-maintain.py --self-check
```

## 步驟 1 — regression suite

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

全綠。(`[fixture] FAIL` 是 install self-check 自己的負向 fixture,預期輸出。)

## 步驟 2 — 驗收項 1:4 張票、3 張不卡、1 張卡著

照 SKILL.md §3 那段指令**逐字**跑,環境是開 #58 那張票時的同一台、同一個 shell
(`sys.stdout.encoding` = `cp950`)。指令前面再加 `PYTHONIOENCODING=cp950`,是要證明
**連刻意把環境釘成 cp950 都蓋不掉修法** — `batch.py` 的 `__main__` 把 stdout 釘成 UTF-8,
env 蓋不過去。這一段的 bytes 實測見步驟 2b。

```text
$ cd skills/build-batch
$ PYTHONIOENCODING=cp950 python batch.py <<'JSON'
{"tickets": [{"number": 60, "state": "open", "blocked_by": []},
             {"number": 61, "state": "open", "blocked_by": []},
             {"number": 62, "state": "open", "blocked_by": []},
             {"number": 63, "state": "open", "blocked_by": [60]}],
 "titles": {"60": "登入頁", "61": "設定頁", "62": "通知", "63": "登入後導向"}}
JSON
要開(3 張):
  #60 登入頁
  #61 設定頁
  #62 通知
排隊(0 張):
  (無)
還卡著(1 張):
  #63 登入後導向 — 卡在 #60
```

「要開」只有 #60 #61 #62 三張,#63 不在名單裡、被列在「還卡著」並寫明卡在 #60。
三段標題(要開 / 排隊 / 還卡著)、「張」、「(無)」、「卡在」全部讀得出來 — 第 1 輪
的壞碼(`�n�}(3 �i):`)沒有再出現。

停下等點頭的部分見步驟 6。

## 步驟 2b — 輸出的原始 bytes 是什麼

上一段是「畫面讀得出來」。這一段直接抓 bytes,證明可讀不是終端機幫忙猜對的:

```text
$ PYTHONIOENCODING=cp950 python batch.py > out.bin <<'JSON'
{"tickets": [{"number": 60, "state": "open", "blocked_by": []},
             {"number": 63, "state": "open", "blocked_by": [60]}],
 "titles": {"60": "登入頁 🔑", "63": "導向"}}
JSON
exit 0

raw bytes head: b'è¦é(1 å¼µ):

  #60 ç'
utf-8 decodes:  要開(1 張):
cp950 decode:   'cp950' codec can't decode byte 0x81 in position 2: illegal multibyte sequence
```

`è¦` = 「要」的 UTF-8。也就是:**`PYTHONIOENCODING=cp950` 沒生效,是預期的** —
`batch.py` 的 `__main__` 把 stdout 釘死 UTF-8,環境變數蓋不過去,這正是 #58 的修法。
emoji title 也在同一份輸入裡,exit 0,沒有 `UnicodeEncodeError`。

**這段證據不涵蓋**:真的開一個 `chcp 950` 的原生主控台(非本 shell)去看渲染。
#58 的 `/client-demo` 已由 client 親手在真主控台確認過那一格,本輪不重複。

## 步驟 3 — 驗收項 2:只有 1 張能跑

```text
$ PYTHONIOENCODING=cp950 python batch.py <<'JSON'
{"tickets": [{"number": 70, "state": "open", "blocked_by": []},
             {"number": 71, "state": "open", "blocked_by": [70]},
             {"number": 72, "state": "open", "blocked_by": [70]}],
 "titles": {"70": "地基", "71": "頁面", "72": "設定"}}
JSON
要開(1 張):
  #70 地基
排隊(0 張):
  (無)
還卡著(2 張):
  #71 頁面 — 卡在 #70
  #72 設定 — 卡在 #70
```

「要開」= 1 張 → SKILL.md §4 第一條岔路:印「沒必要開批次,用 `/build #70`
(Codex: `$build #70`)就好」,結束、不問點頭。這句話的**實錄**在步驟 6b(a)(真實資料)。

## 步驟 4 — 驗收項 3:能跑的超過 3 張

```text
$ PYTHONIOENCODING=cp950 python batch.py <<'JSON'
{"tickets": [{"number": 80, "state": "open", "blocked_by": []},
             {"number": 81, "state": "open", "blocked_by": []},
             {"number": 82, "state": "open", "blocked_by": []},
             {"number": 83, "state": "open", "blocked_by": []},
             {"number": 84, "state": "open", "blocked_by": []},
             {"number": 85, "state": "open", "blocked_by": [84]}],
 "titles": {"80": "一", "81": "二", "82": "三", "83": "四", "84": "五", "85": "六 🔑"}}
JSON
要開(3 張):
  #80 一
  #81 二
  #82 三
排隊(2 張):
  #83 四
  #84 五
還卡著(1 張):
  #85 六 🔑 — 卡在 #84
```

5 張能跑 → 只開 3 張,#83 #84 排隊。cap 寫死 3(`batch.py` 的 `CAP = 3`,
SKILL.md 也對 client 這樣寫,self-check 兩邊互咬)。
順帶驗 #58 的第二半:title 有 emoji(cp950 編不出的字元)照樣印得出來,沒有
`UnicodeEncodeError` 中斷。

## 步驟 5 — 真實資料端到端(§1 → §2 → §3)

照 SKILL.md §1 抓票、§2 解 `## Blocked by`,餵進 §3:

```text
$ gh issue list --state all --limit 200 --json number,state,body,labels,title
spec #51 family: [52, 53, 54, 55, 56, 57, 58, 59]
open ready-for-agent: [52, 53, 54, 55, 56, 57]

$ PYTHONIOENCODING=cp950 python skills/build-batch/batch.py < plan.json
要開(1 張):
  #52 build-batch 1/6:算出誰能同時開,列名單等 client 點頭
排隊(0 張):
  (無)
還卡著(5 張):
  #53 build-batch 2/6:平行開工 → 全綠 → 依序合回主線 → 整批再驗一次 — 卡在 #52
  #54 build-batch 3/6:一張沒過 QA — 好的先收,壞的留在旁邊修 — 卡在 #53
  #55 build-batch 4/6:撞車 — agent 自己解,解不掉停下來講清楚 — 卡在 #53
  #56 build-batch 5/6:排隊補位 — 維持 3 個 lane,做完一張補一張 — 卡在 #53
  #57 build-batch 6/6:接進產線 — /next 推薦、切票守門、藍圖同步 — 卡在 #52
```

§2 的解析(body 的 `## Blocked by` → `blocked_by`)逐字實錄,含 `None` 那種寫法:

```text
#52  Blocked by 段: '- None — can start immediately.'  ->  []
#53  Blocked by 段: '- #52'                            ->  [52]
#54  Blocked by 段: '- #53'                            ->  [53]
#59  Blocked by 段: '- None — can start immediately.'  ->  []
```

closed 的 #58 沒進名單,但留在餵進去的資料裡當 blocker 狀態依據。
真實資料現在正好是「只有 1 張能跑」→ agent 端照 §4 印:
「沒必要開批次,用 `/build #52`(Codex: `$build #52`)就好」,結束。

## 步驟 6 — 點頭前什麼都不動 / 說不乾淨結束

跑完上面全部情境後:

```text
$ git status --porcelain
(空)
$ git worktree list
D:/Self Project/Skills                         dd9675a [main]
D:/Self Project/Skills/.claude/worktrees/...   (3 個 research worktree,QA 前就在)
```

沒有新 worktree、沒有檔案變更、沒有票被動。`/build-batch` 這一版從頭到尾只有
`gh issue list`(讀)+ `batch.py`(純算純印)兩個動作,說不就是不跑下一步,
沒有東西要回收。

## 步驟 6b — agent 端實錄:client 螢幕上真正出現的字

名單以外的字是 agent 產的,不是 python 印的。這一段是我扮 agent 照 SKILL.md 跑完
之後**實際輸出給 client 的原文**,不是引用文件。

### (a) 真實資料 `/build-batch #51` → 只有 1 張能跑(驗收項 2)

接續步驟 5 的名單,agent 端輸出:

```text
沒必要開批次,用 `/build #52`(Codex: `$build #52`)就好。
```

輸出完就結束,不問點頭 — 對照 SKILL.md §4 第一條岔路。這句話出現在 client 螢幕上,
名單也在(§3 印完才走 §4),兩者一起看到。

### (b) 合成資料 4 張票 → 停下等點頭(驗收項 1 後半)

接續步驟 2 的名單,agent 端輸出:

```text
這幾張要一起推嗎?
```

然後**停手**:輸出這行之後沒有再執行任何指令。本輪 QA 是 AFK,由我扮 client 回「不」,
agent 端輸出:

```text
好,那就這樣,沒有開任何工作區、沒有改任何檔案。
```

之後的 `git status --porcelain` 為空、`git worktree list` 沒有新項目(步驟 6),
兩邊對得起來:說不之後沒有東西要回收。

**這段不涵蓋**:真人按鍵的手感(agent 停在那裡等多久、client 打字回覆),留給
`/client-demo`。

## 步驟 7 — agent 端文字逐字走查(SKILL.md §4 / §5)

名單以外的行為是 agent 照 SKILL.md 做的,不是 python 印的,逐字對照:

| 驗收原句 | SKILL.md 出處 | 逐字內容 |
|---|---|---|
| 只有 1 張 → 指路單張 | §4 | 「**只有 1 張能跑** → 印「沒必要開批次,用 `/build #47`(Codex: `$build #47`)就好」,結束,不問點頭。」 |
| 停下等點頭 | §5 | 「名單印完停下來,明確問 client:「這幾張要一起推嗎?」」 |
| 說不 → 乾淨結束 | §5 | 「**說不** → 乾淨結束。什麼都沒開、什麼都沒改,不用回收。」 |
| 點頭前不開 worktree | 開頭 | 「**點頭之前什麼都不動** — 不開 worktree、不改任何檔案、不碰票。」 |
| Codex 端不平行 | Codex 端 | 「印完名單與建議順序就結束 — **不開 worktree、不平行**。」 |

## 步驟 8 — 純函式與文件-程式咬合

`plan_batch` 不碰 `gh` / git / 檔案系統;`batch.py --self-check` 的斷言涵蓋:全部互不相卡、
卡在 open 票後面、卡在已關票後面(放行)、混合 blocker、鏈狀、互卡、超過 cap、cap 參數化、
只有 1 張、0 張、`blocked_by` 指向不存在的票、同輸入跑兩次結果相同且輸入沒被改。

另有兩條守 #58 的斷言:(a) 子行程把 stdout/stdin 都釘成 cp950 跑一次,比對原始 bytes;
(b) `skill_command_issue` 咬 SKILL.md — §3 那段指令必須把 JSON 餵進 `batch.py`,
不准換回 inline `python -c`(印跑到所有測試與所有 pin 外面,就是 #58 出廠的樣子)。

## 已知的、本輪沒動的

- **#59**(known issue,`/client-demo #58` 已判「之後修」):SKILL.md §3 只給 bash heredoc
  的呼叫法,Windows 原生 shell(cmd / PowerShell)照抄不了。本輪的實錄全走 Git Bash,
  所以沒有踩到它,也沒有替它翻案。
- **#60**(known issue,同上):`validate.py` 的守門豁免太寬。與本票 client 看到的東西無關,
  只影響下一支 script 會不會無聲繞過 #58 立的規矩。
- SKILL.md §3 寫的是 `python <skill dir>/batch.py`,`<skill dir>` 要自己代換成真路徑
  (文件下一行有講「`<skill dir>` 就是本 SKILL.md 所在的目錄」)。這是 #59 的同一片,
  不另開票。
