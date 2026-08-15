# Spec: `tracking-viz`

**類型**:自建 skill(AFK,隨時可跑)。

## 職責

從 GitHub Issues 讀資料,產生一頁全白話、client POV 的靜態 HTML dashboard —「隨時看得懂整個專案現在在哪」。

## 輸入

GitHub Issues tracker(`gh` CLI):切片 ticket 狀態與 labels、決策投影 comments、QA 報告、demo checkpoint 排程。

## 版面(#7 prototype 拍板,資產:`docs/prototypes/tracking-viz.prototype.html` @ `prototype/tracking-viz` branch)

1. **Hero**:「現在在哪」一句話 +「下一步」callout(含下一步指令,複製貼上即走 — ticket 接力棒的指路牌)。
2. **功能進度**:每切片一列 — 白話名稱 + 狀態 badge(你已驗收 / 測試中 / 開發中 / 還沒開始)+ 進度條。
3. **品質現況**:三個數字 tile — 必須先修(blocking)/ 小毛病(known issues)/ 既有功能全數正常(regression 綠燈數)+「等你決定」callout。
4. **最近幫你做的決定**:日期 + 白話決策 + 取捨 — **只讀決策投影 comments**,不讀 spec 正本。
5. **接下來的驗收點**:demo checkpoints 排程。

## 行為規則

- 全白話:任何欄位出現技術術語即違規。
- 靜態 HTML,無 server;icon 用 inline SVG 不用 emoji。
- 落選取向參考:看板的「卡片往右走」心智模型、旅程圖的敘事感 — dashboard 資訊過載時可回頭參考。

## 產出與交棒

靜態 HTML 檔(repo 內或 client 可開處)。Dashboard hero 的「下一步指令」就是產線交棒的入口 — 不自動 spawn 下一環節。
