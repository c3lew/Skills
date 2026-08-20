# #98 QA 重跑：PASS

**受測 HEAD**：`eadd3c574702e0582acef2ffabf8f9af7e49924a`  
**逐字實錄**：[`98-rerun.txt`](98-rerun.txt)  
**一鍵重開**：`"C:\Program Files\Git\bin\bash.exe" scripts/qa/98-walkthrough.sh "$(mktemp -d)/qa98"`

## 白話摘要

#102 修好 mutation 台的控制組後，#98 三條驗收原句與票面其餘 AC 全部重跑通過。
乾淨 judge 只讀驗收原句與逐字實錄，逐條判定 **PASS**；沒有
works-but-wrong，blocking 為 0。

| 驗收原句 | 本輪直接證據 | 判定 |
| --- | --- | --- |
| 一個檔有幾個 `__main__` 就檢查幾個 | 只釘第一個 `exit 1`；只釘第二個 `exit 1`；兩個都釘 `exit 0`；新版 probe `不合 1`、修前 probe `不合 0` | PASS |
| parse 不動要判 fail | typo 與 cp950 各自輸出檔名及原因並 `exit 1`；修正 typo 後 `exit 0` | PASS |
| `__main__.py` 不得被過濾誤傷 | 未 pin 的 package entry point `exit 1`；補 pin 後 `exit 0`；`__pycache__` / `.venv` / `.hidden.py` 對照仍綠 | PASS |

## Regression 與修前對照

- `python scripts/validate.py` + 五支 self-check：全部 exit 0。
- 同一份 22 格母體：修後 `母體 22,不合 0`。
- 修前差額只有三筆，方向都符合票面：`__main__.py` 修前綠→修後紅、
  SyntaxError 修前綠→修後紅、cp950 修前掛掉→修後紅；修前紅→修後綠為 0。
- 獨立寬尺對 repo 的 7 筆差額，仍是既有刻意寫寬造成的誤紅；另加過濾 fixture
  後多出的 3 筆正是 `.venv`、`.hidden.py`、`__pycache__`，逐筆符合設計。
- `python scripts/qa/97-mutate.py --run`：`15/15 個 knob 被 self-check 咬住`，exit 0。
- `python scripts/qa/98-mutate-control.py`：`控制組綠；完整副本 15/15 個 knob 被咬住`；
  刻意紅控制組在第一格前中止，exit 0。
- `python scripts/qa/96-newrule-probe.py .`：`OK 新規則下全綠`、`不合 0`。

## 分類

### blocking（0）

無。#102 已修復並另經 QA 通過。

### known issues（2，沿用上輪，非本輪新發現）

- #103：`is_source(rel)` 的相對路徑約束尚未由 inline self-check 釘住；本輪 walkthrough
  的 hidden-root 對照仍證明現行行為正確。
- #104：第二把尺 `96-newrule-probe.py` 自身仍沒有 self-check，且 cp950 source 會使它
  traceback；不影響本票產品守門判準。

## 未涵蓋範圍與 demo 實錄

- 這是 CLI 守門規則，沒有 UI / Playwright / a11y snapshot；xtrace 即 demo 實錄。
- 三條驗收分別位於逐字實錄 STEP 2、STEP 3、STEP 4；修前對照、寬尺、mutation、
  probe 分別位於 STEP 5–8。
- repo 本體目前沒有 `__main__.py`，此軸以 fixture 與 22 格母體驗證。

## 獨立 judge

三條驗收與其餘票面 AC 全部 **PASS**；blocking 0。judge 認定控制組已先建立綠基準，
且刻意紅控制組會在 mutation 第一格前中止，因此 15/15 是有效量測，不是無條件假綠。

## 交棒

下一步:`/client-demo #98`(Codex: `$client-demo #98`)
