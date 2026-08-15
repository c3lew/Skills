---
name: qa
description: 扮演使用者拿驗收清單實測切片,獨立 judge 抓 works-but-wrong,fail 開票標 blocking/known issue。當 implement 完成後 ticket 指路「/qa #N」、維護產線 bug fix 要驗證、或 client-demo 過關後要固化 regression scenarios 時使用。
---

# qa

扮演使用者、拿驗收清單實測切片,全程 AFK。QA 全綠只代表「可以 demo」,過關由 `client-demo` 判定 — 本 skill 產證據,不當 gatekeeper。

## 1. 定輸入

- **測試範圍 oracle**:ticket 的「覆蓋驗收項」段(slice-tickets 標注)。walkthrough 只測這幾條;段落缺失就停下回報,指路回 `slice-tickets` 補,不要自己編 scenarios。
- **判定 oracle**:spec issue 裡驗收清單的**原句**(Gherkin scenarios 的白話版,pm-intake 收斂回合 client 已拍板 — 直接用,不重寫)。
- **視覺 oracle**(如有):spec 裡拍板的 prototype。
- **既有 regression suite**。

Bug fix ticket 的範圍 = 該 bug 的重現 scenario + regression suite。

## 2. Regression 先跑

跑既有 regression suite,再走新切片 walkthrough。紅的每一條記為 blocking,照樣走完後續階段 — 一次跑完、一份完整報告。

## 3. Walkthrough(Playwright MCP)

起 QA 環境,逐條驗收項照原句描述的情境操作,每步取 a11y snapshot 當證據;有視覺 oracle 就同場對照 prototype。

- **Web 切片**:專案 dev server。
- **Desktop(Tauri)切片**:Vite dev server + injected fakes 在瀏覽器跑(前提:UI 是 pure reducer + injected seams)。原生殼行為(tray、global hotkey、updater)不進本 pipeline,由 `client-demo` 親手操作把關 — 報告註明未涵蓋。

## 4. 獨立 judge

開一個乾淨 subagent 當 judge:只餵 spec 驗收原句 + walkthrough 證據(snapshots),不餵實作脈絡與本 session 的判斷。judge 逐條判 pass / fail / **works-but-wrong**(功能會動但不是 spec 說的那件事)— works-but-wrong 一律算 fail。

## 5. 分類與開票

每條 fail 開 bug ticket(重現步驟 + 對應驗收原句 + 證據)並標 severity:

- **blocking** — 驗收清單 fail,修完才能 demo。ticket comment「下一步:`/implement #N`」。
- **known issue** — 非 blocking,帶著 demo;處置(現在修 / 之後修 / 不修)由 client 在 demo 收尾整批確認。

## 6. 報告與交棒

QA 報告寫回本 ticket:白話摘要 + blocking / known issues 清單 + 未涵蓋範圍(如 Tauri 原生殼)。

- blocking 清零 → comment「下一步:`/client-demo #N`」。
- 有 blocking → 列出 bug tickets,修完重跑 `/qa #N`。

## 7. 過關後固化

`client-demo` 判定過關、指回本 skill 時:把該切片高價值 scenarios(核心流程、曾抓到 bug 的)寫成 Playwright regression test 進 suite,跑綠後 comment 固化了哪幾條。期間拍的取捨照 [`references/tech-decisions.md`](references/tech-decisions.md) 的決策投影格式記錄。
