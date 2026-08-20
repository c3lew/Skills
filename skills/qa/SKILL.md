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

**Oracle 獨立性**:受測物本身就是判準的時候(lint、守門、validator、任何「自己判自己對不對」
的東西),不准只跑受測物 — 它綠只證明它同意自己。要另寫一支**刻意寫寬、不套受測規則**的
獨立掃描當第二把尺,兩邊對照;寬的那支撈出來的多餘項逐筆判讀,判成誤報也要寫進報告。
同理,拍板依據若來自上游文件,QA 要有一次在乾淨環境的實跑,不拿文件的句子當證據。

## 2. Regression 先跑

跑既有 regression suite,再走新切片 walkthrough。紅的每一條記為 blocking,照樣走完後續階段 — 一次跑完、一份完整報告。

**改判準的票要跑修前對照**:這張票動的是判斷邏輯(守門規則、篩選條件、分類判準)時,除了
跑現況,還要用**修之前那個 commit** 跑同一份母體,列出差額。新出現的誤判一律當成「本輪
引入」,在報告與票上標明是 regression、不是舊天花板。

只驗「這次要修的那一面」會漏掉另一面:放寬會多放、收緊會多擋,而多出來的那批在修之前
是好的。沒有修前對照,這批要等下一輪才被當成新 bug 開票。

## 3. Walkthrough(Playwright MCP)

起 QA 環境,逐條驗收項照原句描述的情境操作,每步取 a11y snapshot 當證據;有視覺 oracle 就同場對照 prototype。同場開錄影(Playwright video / 逐步截圖),**每條驗收項存一段 demo 實錄** — 這是 client-demo 的預設素材,存到專案 repo 的 QA artifacts 目錄(位置第一次跑時拍板,之後沿用)。

QA 環境的啟動做成**一鍵重開**:單一 script / 指令(起 dev server + 灌 fakes)。還沒有就本次順手建好 — 這是技術決策,照規則書自拍留投影;之後每輪 QA 與 client-demo 的「client 想摸」都用同一個指令。

- **Web 切片**:專案 dev server。
- **Desktop(Tauri)切片**:Vite dev server + injected fakes 在瀏覽器跑(前提:UI 是 pure reducer + injected seams)。原生殼行為(tray、global hotkey、updater)不進本 pipeline,由 `client-demo` 親手操作把關 — 報告註明未涵蓋。

## 4. 獨立 judge

開一個乾淨 subagent 當 judge:只餵 spec 驗收原句 + walkthrough 證據(snapshots),不餵實作脈絡與本 session 的判斷。judge 逐條判 pass / fail / **works-but-wrong**(功能會動但不是 spec 說的那件事)— works-but-wrong 一律算 fail。

## 5. 分類與開票

**同型全掃**:抓到一條 fail,先把它當成一把尺,掃過同一份 artifact 的**所有**同型句子 / 數字 / 值,一次全部列進報告再開票 — 不是只回報眼前撞到的那一條。修一條、下一輪換個 reader 再抓一條同形狀的,那是同一個 bug 被拆成 N 輪,不是 N 個 bug。

散文本身就是交付物的切片(凍結例外清單的理由、研究文件的結論),判準見 [`references/written-evidence.md`](references/written-evidence.md)。

每條 fail 開 bug ticket(重現步驟 + 對應驗收原句 + 證據)並標 severity:

- **blocking** — 驗收清單 fail,修完才能 demo。ticket comment「下一步:`/build #N`(Codex: `$build #N`)」。
- **known issue** — 非 blocking,帶著 demo;處置(現在修 / 之後修 / 不修)由 client 在 demo 收尾整批確認。

## 6. 報告與交棒

QA 報告寫回本 ticket:白話摘要 + blocking / known issues 清單 + 未涵蓋範圍(如 Tauri 原生殼)+ **demo 實錄清單**(每條驗收項對一段,附路徑)+ **一鍵重開指令**(client-demo 直接抄)。

- blocking 清零 → 看票的「覆蓋驗收項」段分流:有可 demo 的驗收項 → comment「下一步:`/client-demo #N`(Codex: `$client-demo #N`)」;標「無 — 由後續票的驗收項間接驗證」(純基礎工程切片,沒東西給 client 看)→ comment「下一步:`/close #N`(Codex: `$close #N`)」,demo 由後續票間接把關。
- 有 blocking → 列出 bug tickets,修完重跑 `/qa #N`。

## 7. 過關後固化

`client-demo` 過關判定前三條(client OK + blocking 清零 + known issues 有處置)成立、指回本 skill 固化時:把該切片高價值 scenarios(核心流程、曾抓到 bug 的)寫成 Playwright regression test 進 suite,跑綠後 comment 固化了哪幾條。期間拍的取捨照 [`references/tech-decisions.md`](references/tech-decisions.md) 的決策投影格式記錄。
