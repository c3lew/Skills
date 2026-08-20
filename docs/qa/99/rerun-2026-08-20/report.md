# #99 QA 重跑報告

## 結論

**PASS — 7/7 AC 通過，blocking 0，known issue 0，works-but-wrong 0。**

#105 已修正上輪唯一 blocking：dashboard 現在是 8 個小毛病、8 列現行清單，逐張對到
#42/#47/#48/#50/#59/#63/#103/#104；#67 只顯示為規則邊界，不再混入待辦。

## 逐項判定

| AC | 判定 | 本輪實測 |
| --- | --- | --- |
| 16 張判準消失票關閉並統一指回 #96 | PASS | 16/16 CLOSED；逐張 comment 皆同時含 #96 與「這張量的判準在新規則下不存在了」。 |
| 4 張併入 spec 的票關閉並指向落地票 | PASS | #66/#68/#69 → #98；#74 → #97；4/4 CLOSED。 |
| #60 改寫 AC1 並留下拍錯原因 | PASS | body 已改為每個 canonical `__main__` block 第一層 pin；comment 有「當初為什麼拍錯」紀錄。 |
| #67 保留為宣告過的天花板 | PASS | #67 OPEN；title/body 明載「宣告過的天花板」「不是待辦」及 #96 來源。 |
| 12 支歷史 sweep 與 oracle 說明 | PASS | README 明列歷史定位、不進現行 regression、舊 `MISMATCH` 語意與保留 `87-oracle.py`；12/12 可執行且無 traceback。 |
| dashboard 重跑且數字對得上 | PASS | checker exit 0：tile 8、清單 8；live issues 正好是 #42/#47/#48/#50/#59/#63/#103/#104。 |
| #97/#98 關票前已過 QA | PASS | 兩票均有早於結案 comment 的 QA PASS 紀錄。 |

## Regression 與第二把尺

以下本輪重新執行，全部 exit 0：

```text
python scripts/validate.py
python scripts/validate.py --self-check
python scripts/batch.py --self-check
python skills/build-batch/batch.py --self-check
python scripts/install.py --self-check
python scripts/hooks/triage-to-maintain.py --self-check
python scripts/qa/97-mutate.py --run
python scripts/qa/96-newrule-probe.py .
python scripts/qa/87-oracle.py .
python docs/qa/105/check_dashboard.py
```

- mutation：15/15 knob 被 self-check 咬住。
- `87-oracle.py`：母體 84，fixture 與實跑不合 0。
- 12 支 `*-sweep.py`：12/12 無 traceback；2 支 exit 0，10 支因歷史 fixture `MISMATCH` exit 1，符合 README。

## 獨立 judge

乾淨 judge 只收到七項驗收原句與本輪實測證據，判定 **7 PASS / 0 FAIL / 0 works-but-wrong**；
blocking 0，known issue 0。逐項結果見 `judge.md`。

## Demo 與未涵蓋

- 票面「覆蓋驗收項」明列：無，由 #97/#98 間接驗證。
- 沒有新的 client 操作 demo；dashboard 的現行瀏覽器實錄沿用
  `docs/qa/105/demo/dashboard.png`，本輪另以 live tracker 與 checker 重驗內容。
- 一鍵重跑：`python docs/qa/105/check_dashboard.py`。

## 證據索引

- `issues-live.json`、`open-issues-live.json`：本輪 live tracker 快照。
- `regression-summary.json`、`sweep-summary.json`：命令、exit 與輸出位置摘要。
- `runs/`：本輪 literal outputs。
- `baseline-report.md`：上輪 FAIL 報告原文保留。

下一步：`/close #99`(Codex: `$close #99`)。
