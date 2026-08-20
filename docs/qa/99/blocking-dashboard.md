## severity

**blocking** — 直接違反 #99 AC6「dashboard 重跑，數字對得上」。

## 驗收原句

> `python scripts/tracking-viz` 那份 dashboard 重跑，數字對得上。

## 重現

1. 開啟 `dashboard.html`。
2. 品質現況 tile 顯示「小毛病（帶著走）= 7」。
3. 計算 HTML 內 `<span class="when">帶著走</span>`：實際 14 列。
4. 逐列對回 live GitHub issue 狀態。

## 實際結果

- 5 列仍把已 CLOSED 的 #77/#78/#76/#74/#60 寫成「帶著走／已開單子」。
- 1 列把 #67 寫成「等你決定什麼時候修」，但 #67 的 title/body 已明定「宣告過的天花板（不是待辦）」。
- 移除這 6 列後，仍有 8 個現行小毛病：#42/#47/#48/#50/#59/#63/#103/#104。
- 因此 tile 的 7、14 列清單、以及 live tracker 三者互相不一致。

## 預期結果

- 移除或改寫 6 列過期內容；#67 只能呈現為明講的規則邊界，不得寫成待辦。
- 「小毛病」tile 與現行「帶著走」清單都對到 8 個 live issues。
- 同型全掃後，不再有 CLOSED issue 被寫成「帶著走／已開單子」。

## 證據

- `docs/qa/99/report.md`
- `docs/qa/99/judge-evidence.json`
- `docs/qa/99/open-issues-live.json`
- 獨立 judge：AC6 FAIL；blocking 1；known issue 0。

下一步：`/build #105`(Codex: `$build #105`)
