---
name: tracking-viz
description: 讀 GitHub Issues 產一頁全白話靜態 HTML dashboard — hero「現在在哪 + 下一步指令」+ 功能進度/品質現況/最近決定/驗收點四宮格。當 client 想看專案現況、環節收尾要更新 dashboard、或 ticket/skill 指路「/tracking-viz」時使用。AFK 隨時可跑。
---

# tracking-viz

從 GitHub Issues 讀資料,產給 client 看的一頁靜態 HTML dashboard。讀者是非技術 client:每個欄位都要他一眼看懂,dashboard 上任何技術術語都算違規。

## 1. 收資料(`gh` CLI)

Hero 與四宮格各有固定資料來源,只讀 tracker,不讀 spec 正本、不讀 code:

| 區塊 | 來源 |
|------|------|
| Hero「現在在哪 + 下一步」 | 進行中切片 ticket 的最新交棒 comment(產線慣例:收尾寫「下一步:`/skill #N`」)。找不到交棒 comment 才自己從切片狀態推下一棒指令。 |
| 功能進度 | 每張 slice ticket 一列:標題 + 狀態 + 進度。 |
| 品質現況 | bug tickets 的 blocking / known issue 標記數、QA 報告 comment 的 regression 綠燈數、待 client 決定的 known issue 處置。 |
| 最近幫你做的決定 | 決策投影 comments(白話三行制:選擇/影響/反悔成本)— 只讀這裡,取最近幾則,濃縮成「日期 + 決策 + 取捨」一行。 |
| 接下來的驗收點 | demo checkpoint 排程(client-demo 相關 comments / open demo tickets)。 |

## 2. 翻成白話

切片狀態從 ticket state + 產線進度推,badge 用固定詞:

| 切片在哪 | badge |
|----------|-------|
| ticket closed(client 點頭過關) | 你已驗收 |
| QA / demo 階段 | 測試中 |
| implement 進行中 | 開發中 |
| 還沒動 | 還沒開始 |

進度條寬度照同一張表推,不假裝精確:還沒開始 0%、開發中 30%、測試中 70%、你已驗收 100%。

品質三 tile 的詞:blocking →「必須先修」、known issue →「小毛病(帶著走)」、regression 綠燈 →「既有功能全數正常」。切片名稱用 client 聽得懂的功能描述,ticket 標題帶術語就改寫。

## 3. 產 HTML

照 [`references/dashboard.template.html`](references/dashboard.template.html)(client 拍板的版面)填真資料:版面與 CSS 照抄,示意內容整份換掉。規則:

- 單檔靜態 HTML、無 server、無外部資源;icon 用 template 內建的 inline SVG,不用 emoji。
- Hero 的「下一步」含可複製的下一棒指令(`<code>/skill #N</code>`)— 這是產線交棒的指路牌,只指路,不自動 spawn 下一環節。
- 沒資料的區塊留著並寫白話空狀態(例:「還沒有幫你做過決定」),讓版面穩定。例外:「等你決定」callout 是提醒不是常駐區塊,沒有待決事項就整塊拿掉。
- 其他環節掛在 dashboard 的一句話資訊(release note 目前版本、監控新錯數、retro 提示)放副標列或品質卡,一樣白話。
- 寫到目標專案 repo 根的 `dashboard.html`;已存在就整份覆蓋更新。
- 資訊過載、一頁塞不下時的退路(#7 落選取向):功能進度可借看板「卡片往右走」的心智模型分欄,或借旅程圖的敘事感排時間軸 — 版面主體仍是拍板的儀表板。

## 4. 白話自查

產完逐欄重讀一遍:每個 client 看得到的字,想像唸給沒寫過程式的人聽 — 出現 QA、regression、blocking、ticket、merge 這類詞就換白話再存檔。全部欄位過了才算完成。

## 5. 收尾

回報 dashboard 檔案路徑 + hero 一句話(現在在哪 + 下一步指令)。由呼叫脈絡決定要不要寫回 ticket。
