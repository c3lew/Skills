# #105 QA 報告

## 結論

**PASS — blocking 0，known issue 0。** Dashboard 的「小毛病」tile、現行「帶著走」清單與 live issue 狀態一致。

## Bug scenario

| 判準 | 判定 | 本輪實測 |
| --- | --- | --- |
| 移除或改寫 6 列過期內容 | PASS | 修前 14 列，修後 8 列，差額正好 6 列。 |
| #67 只呈現為規則邊界 | PASS | #67 仍 OPEN，但畫面標成「規則邊界／不是等著修的項目」，未列入「帶著走」。 |
| tile 與現行清單都對到 8 個 live issues | PASS | tile=8、清單=8；對應 #42/#47/#48/#50/#59/#63/#103/#104，逐張皆 OPEN。 |
| CLOSED issue 不再列為「帶著走／已開單子」 | PASS | #60/#74/#76/#77/#78 逐張為 CLOSED，已不在現行清單。 |

## Browser walkthrough

- `http://127.0.0.1:8765/dashboard.html` 回應 HTTP 200。
- Playwright a11y snapshot 顯示「小毛病(帶著走)」數字為 8，#67 顯示為「規則邊界／不是等著修的項目」。
- 全頁實錄：`docs/qa/105/demo/dashboard.png`。
- 唯一 console 訊息是瀏覽器索取不存在的 `favicon.ico`（404）；不影響 dashboard 內容或本票判準。

一鍵重開：

```text
python -m http.server 8765 --directory .
```

開啟 `http://127.0.0.1:8765/dashboard.html`。

## Regression

以下命令均在本輪重新執行並以 exit 0 結束：

```text
python docs/qa/105/check_dashboard.py
python scripts/validate.py
python scripts/validate.py --self-check
```

獨立檢查器不依賴 dashboard 自報數字：它同時讀修前 HTML、修後 HTML 與 live GitHub issue 快照，核對 14→8 的差額、8 張現行票、5 張 CLOSED 票及 #67 邊界。

## 獨立 judge

乾淨 judge 只讀驗收原句與 QA 證據，逐條判定 6 PASS / 0 FAIL / 0 works-but-wrong；blocking 0，known issue 0。

## 證據

- `docs/qa/105/check_dashboard.py`：可重跑的獨立檢查器。
- `docs/qa/105/issues-live.json`：live GitHub issue 快照。
- `docs/qa/105/dashboard-evidence.json`：tile、修前／修後列、移除列與 issue 狀態。
- `docs/qa/105/runs/`：三條命令的 literal output 與 exit status。
- `docs/qa/105/demo/snapshot.txt`、`find-known-issues.txt`、`dashboard.png`：瀏覽器 walkthrough 證據。
- `docs/qa/105/judge.md`：獨立 judge 判定。

下一步：`/close #105`(Codex: `$close #105`)；結案後重跑 `/qa #99`(Codex: `$qa #99`)。
