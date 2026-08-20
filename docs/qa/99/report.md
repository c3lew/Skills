# #99 QA 報告

## 結論

**FAIL — blocking 1，known issue 0。** 7 項 acceptance criteria 有 6 項通過；dashboard 的數字與「帶著走」清單沒有同步，直接違反 AC6。

## 逐項判定

| AC | 判定 | 實測結果 |
| --- | --- | --- |
| 16 張判準消失票關閉並統一指回 #96 | PASS | 16/16 CLOSED；每張最後留言均含「#96 已改判準；這張量的判準在新規則下不存在了」。 |
| 4 張併入 spec 的票關閉並指向落地票 | PASS | #66/#68/#69 → #98；#74 → #97；4/4 CLOSED。 |
| #60 改寫 AC1 並留下拍錯原因 | PASS | #60 CLOSED；body 明定每個正規 `__main__` block 第一層 pin，留言保留「當初為什麼拍錯」。 |
| #67 保留為宣告過的天花板 | PASS | #67 OPEN；title/body 明載「宣告過的天花板（不是待辦）」及 #96 拍板結果。 |
| 12 支歷史 sweep 與 oracle 說明 | PASS | README 五項語意齊全；12/12 腳本可啟動且無 traceback。舊 fixture 造成 10 支 exit 1，與 README 的 `MISMATCH` 說明一致；`87-oracle.py` 保留。 |
| dashboard 重跑且數字對得上 | **FAIL** | tile 顯示 7 個小毛病，但 HTML 有 14 列「帶著走」。其中 #77/#78/#76/#74/#60 已結案，#67 又被寫成「等你決定什麼時候修」，和「不是待辦」衝突。移除這 6 列後，現行小毛病仍有 #42/#47/#48/#50/#59/#63/#103/#104，共 **8** 個，不是 7。 |
| #97/#98 關票前已過 QA | PASS | 兩票均先留 QA PASS、blocking 0，再留下結案留言。 |

## Regression 與獨立第二把尺

以下命令本輪重新執行，均 exit 0：

```text
python scripts/validate.py
python scripts/validate.py --self-check
python scripts/batch.py --self-check
python skills/build-batch/batch.py --self-check
python scripts/install.py --self-check
python scripts/hooks/triage-to-maintain.py --self-check
python scripts/qa/97-mutate.py --run        # 15/15 knob 被咬住
python scripts/qa/96-newrule-probe.py .     # 不合 0
python scripts/qa/87-oracle.py .            # 母體 84，fixture 與實跑不合 0
```

12 支 `*-sweep.py` 也逐支執行；12/12 無 traceback。逐支 literal output 與 exit status 在 `runs/`，摘要在 `sweep-summary.json`。

## 獨立 judge

乾淨 judge 只讀 acceptance criteria 原句與 `judge-evidence.json`，判定 6 PASS / 1 FAIL；dashboard finding 為 blocking，沒有 works-but-wrong 或可降級項目。

## 未涵蓋與 demo 素材

- 覆蓋驗收項：無，由 #97/#98 間接驗證。
- UI walkthrough / demo 實錄：無；本票沒有新的畫面或操作流程。
- 一鍵重開：不適用。重跑命令已列於上節。

## 證據

- `issues-live.json`：28 張相關票的 live body、state、comments 快照。
- `open-issues-live.json`：目前 open issue 快照。
- `judge-evidence.json`：去除實作脈絡後交給獨立 judge 的證據包。
- `regression-summary.json`、`oracle-summary.json`、`sweep-summary.json`：命令、exit 與 literal tail 摘要。
- `runs/`：每支命令的完整輸出。

下一步：先修 blocking，再重跑 `$qa #99`。
