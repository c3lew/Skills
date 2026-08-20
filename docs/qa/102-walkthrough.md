# #102 QA walkthrough

## 判定

**PASS** — blocking 0、known issue 0。

修前同一份 mutation 母體會出現「表 exit 0、未套 knob 控制組 exit 1」的假綠；修後先驗
控制組，紅控制組在第一格前中止，綠控制組才執行 15 格有效 mutation 表。

| 驗收情境 | 實測結果 | 判定 |
| --- | --- | --- |
| 未套 knob 控制組先綠 | 完整 repo 控制組綠，harness exit 0 | PASS |
| 控制組為紅時立即停止 | `control_exit=1`、`mutations_started=0` | PASS |
| 綠控制組才跑 mutation 表 | 15 個具名 knob 各自 `self-check exit=1`，彙總 15/15 | PASS |
| 有效表成功結束 | walkthrough exit 0 | PASS |

乾淨 judge 只讀驗收原句與實錄重審，四項皆 PASS；第一次實錄曾把紅控制組與另一輪有效表
連在一起而判 works-but-wrong，分成 phase A / B 並明列計數後，證據缺口清零。

## 修前對照

- 基準 commit：`4c01110`
- `python scripts/qa/97-mutate.py --run`：exit 0
- 同 harness 未套 knob 控制組：exit 1
- 結論：修前 15/15 是假綠，重現 #102。

## Regression

以下全部 exit 0：

- `python scripts/qa/102-walkthrough.py`
- `python scripts/qa/98-mutate-control.py`
- `python scripts/validate.py --self-check`
- `python scripts/batch.py --self-check`
- `python scripts/install.py --self-check`
- `python scripts/hooks/triage-to-maintain.py --self-check`
- `python skills/build-batch/batch.py --self-check`
- `python scripts/qa/96-newrule-probe.py .`（`不合 0`）
- `python scripts/validate.py`

完整逐字輸出：[`102-walkthrough.txt`](102-walkthrough.txt)。

## Demo 實錄與一鍵重開

這是 CLI 守門，沒有 UI / Playwright / a11y snapshot；逐字 transcript 就是 demo 實錄。

```powershell
python scripts/qa/102-walkthrough.py
```

## 交棒

#102 已清掉 #98 的 blocking；回到上游重跑整張驗收。

下一步:`/qa #98`(Codex: `$qa #98`)
