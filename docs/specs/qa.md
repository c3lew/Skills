# Spec: `qa`

**類型**:自建 skill(AFK)。

## 職責

agent 扮演使用者、拿驗收清單實測切片:五階段 pipeline + regression + 抓 works-but-wrong + 開 ticket。QA 全綠只代表「可以 demo」,不代表過關 — agent 不當 gatekeeper。

## 觸發與入口

`/build`(wrap 原件 `/implement`)完成後,ticket comment 指路「下一步:`/qa #N`」。維護產線的 bug fix 也走這裡(regression + 該 bug 的重現 scenario)。

## 輸入

- Spec 的驗收清單(唯一 oracle,pm-intake 收斂回合已拍板 — QA 不另生 scenarios)。
- 拍板 prototype(視覺 oracle,如有)。
- 既有 regression suite。

## 行為

1. **先跑 regression suite**,再走新切片 walkthrough。
2. 五階段 pipeline(承 #4 research):spec→Gherkin scenarios(已在驗收清單定稿)→ Playwright MCP a11y snapshot walkthrough → 獨立 LLM judge 對 spec 原句覆核抓 works-but-wrong → 報告。Walkthrough 同時錄 **demo 實錄**(每條驗收項一段 video / 截圖序列)— client-demo 的預設素材,在 QA 階段免費產出。
3. Fail 直接開 ticket、標 severity:**blocking**(驗收清單 fail,修完才 demo)/ **known issue**(非 blocking,帶著 demo)。
4. 切片過關後(client-demo 判定)把高價值 scenarios 固化成 Playwright regression test。

## Desktop app(Tauri)路線

QA 環境 = **Vite dev server + injected fakes 在瀏覽器跑**,給 Playwright 測(前提:UI 是 pure reducer + injected seams,如 Quacket)。Tauri 原生殼行為(tray、global hotkey、updater)不進 QA pipeline — 由 client-demo 親手操作把關。

## 產出與交棒

- QA 報告(白話摘要 + blocking / known issues 清單)寫回 ticket,**附 demo 實錄**(每條驗收項一段)與 **QA 環境一鍵重開指令**(單一 script,起 dev server + 灌 fakes;第一次跑 QA 時建好,技術決策系統自拍)。
- 綠 → comment「下一步:`/client-demo #N`」;blocking → 開 bug tickets 回 `/build`,修完重跑。

## 引用

`docs/disciplines/tech-decisions.md`(決策投影格式);Playwright MCP;被 client-demo、maintain 依賴。
