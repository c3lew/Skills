# CONTEXT

本 repo 的 ubiquitous language。對話與文件用繁體中文,術語保留英文原文。

## Glossary

- **Client**:委託開發的使用者本人。系統對他只談使用者看得到的行為與現實取捨,不談技術。
- **驗收清單 (acceptance checklist)**:spec 的一部分 — 從 spec 生成的 Gherkin scenarios 的白話版,在 pm-intake 收斂回合由 client 拍板。QA 的唯一 oracle。
- **QA**:agent 扮演使用者、拿驗收清單實測切片的 AFK 流程。QA 全綠只代表「可以 demo」,不代表過關。
- **Works-but-wrong**:程式能動、但不是 client 要的東西。靠獨立 judge 對 spec 原句覆核來抓。
- **Blocking issue**:驗收清單直接 fail 的問題。修完才能 demo。
- **Known issue**:非 blocking 的小毛病。帶著 demo,開頭告知,收尾由 client 整批確認處置(現在修 / 之後修 / 不修)。
- **Demo checkpoint**:QA 過後的驗收點 — agent 逐條放 QA 實錄演「什麼情況 → 你會看到什麼」,client 逐條點頭;配可點的 link + 白話 demo script + QA 報告摘要。親手操作是 opt-in(操作感驗收項或 client 想摸)。
- **「不對」四分類**:demo 時 client 否決的四種來源 — spec 理解錯(回 pm-intake)、實作錯(bug ticket 走 QA loop)、新想法(新 feature ticket)、技術拍板錯(重拍,不重訪 client)。agent 提分類建議,client 確認。
- **自動拍板**:兩軸測試判定不需問 client 的技術決策,由系統自行決定並留紀錄;有影響者在收斂回合以白話三行制回報。
- **依據型判準**:自動拍板前的查證 guardrail — 決策依據若是會過時的外部事實(套件 API、版本、價格、平台限制)必先查證再拍;純設計取捨直接拍。
- **白話三行制**:自動拍板決策的回報格式 — 做了什麼選擇 / 對你的影響 / 反悔成本。
- **反悔成本**:決策之後想改是小事還是大工程 — client 分配注意力的依據。
- **決策投影**:決策拍板或更正時同步發到 tracker 的 comment;spec 的 Implementation Decisions 是正本(只留現況),投影是 append-only 的歷史,dashboard 只讀投影。
- **過關 (slice done)**:client 親口 OK + blocking 清零 + known issues 都有處置決定 + regression suite 全綠 + 高價值 scenarios 已固化。
- **Regression 固化**:切片過關後,高價值 scenarios 轉成 Playwright regression test,之後每次 QA 先跑。
- **Prototype 拍板**:client 親手操作可點的 HTML prototype(首見 flow 給 2–3 個 variant)後選定的 UI 原型。發生在 spec 拍板前;拍板後成為 spec 的一部分、QA 的視覺 oracle。
- **Design system 文件**:首個切片 UI 拍板後抽出的輕量樣式慣例(色、字、間距、元件),之後所有 prototype 與實作引用;偏離要過 client。
- **維護進件**:上線後 client 用白話丟給 agent 的問題或想法(bug / 改功能 / 技術債)。agent 追問、分類(「不對」四分類的日常版)、開 ticket 走 /triage 的 state machine;client 自己開的 issue 也收,標 `needs-triage`。
- **Mini-intake**:bug 進件的輕量訪談 — 追問到「能重現 + 期望行為清楚」為止,每輪 ≤3 題、只問 client 看得到的事,複述確認後開 ticket;重現不了標 `needs-info`,不瞎猜。
- **分級閉環**:client 報的 bug 要 client 點頭才閉環(只有他知道「好了沒」);agent 自撿的問題 regression 綠 + 白話回報即結案。
- **兩軸分流(維護版)**:改功能進件用影響 × 把握判定走輕量版(一輪確認 + 只更新動到的驗收項)或完整 pm-intake,agent 提議、client 確認。
- **Tech-debt backlog**:agent 觀察到的技術債開 ticket 掛 `tech-debt` + `needs-triage` 攢批,白話三行制定期報 client,client 只決定「現在做 / 之後 / 不做」;執行 AFK,驗收 = regression 全綠(可見行為不變)。
- **一環節一 session**:生命週期每個環節獨立 session 執行,吃 context smart zone;唯一例外是 pm-intake → to-spec 同 session(spec 收斂吃訪談對話 context)。
- **Ticket 接力棒**:環節間的交棒機制 — session 收尾把產出 link 與「下一步指令」寫回 ticket comment,下一個 session 以 `/skill #N`(Codex: `$skill #N`)冷啟動;下一棒由 client 手動開,dashboard hero 指路。
- **引用規範 (discipline)**:抽成獨立文件的行為規則,多個 skill 引用同一份(PM 訪談紀律、技術決策紀律),改一處全體生效。
- **PM 訪談紀律**:跟 client 談話的規則書 — 兩軸對齊測試、情境問法、每輪 ≤3 題、收斂回合、白話三行制;pm-intake 主用,wayfinder map Notes 引用,mini-intake 為輕量版。
- **歷史對照**:本系統說的「A/B」— 不同 feature 各跑一套或同 feature 跑兩遍都不採;新 feature 只用新系統跑一次,舊做法的 baseline 取自既有 tracker 實績(訪談輪數、rework、漏到 client 的 works-but-wrong),對照痕跡 + client debrief。
- **Refactor 結案儀式**:任何 refactor(含 /improve-codebase-architecture 拍板者)的 invariant — 沒有 ticket + regression 全綠 + 決策投影,就不算做過。grilling 中發現會動到可見行為,即刻分流為改功能 ticket。
- **過關即發**:切片過關的最後一格 — agent build 新版 + 換裝本機(app 重啟一次),dashboard 留一行白話 release note;rollback = 裝回上一版 installer。不開獨立發佈 session。
- **監控掃描**:app 錯誤寫本機結構化 error log,agent 每次維護 session 開頭順掃,新錯開 agent-自撿 ticket(分級閉環);dashboard 顯示新錯數。單機自用場景,換機時升級 Sentry。
- **Retro 餵食口**:solo retro 的三個原料來源 — 拍板錯更正 comment 的「當初為什麼拍錯」、tech-debt backlog、demo 抓到的 QA 漏抓(「不對」分類 comment)。
- **Solo retro**:攢批觸發的全 AFK 檢討 — 餵食口累積到門檻 dashboard 提示,client 說跑才跑;agent 找 pattern 產白話報告 + amendment 提案,client 逐條點頭才改 disciplines/skills。系統自我升級的唯一入口。
