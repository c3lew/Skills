# CONTEXT

本 repo 的 ubiquitous language。對話與文件用繁體中文,術語保留英文原文。

## Glossary

- **Client**:委託開發的使用者本人。系統對他只談使用者看得到的行為與現實取捨,不談技術。
- **驗收清單 (acceptance checklist)**:spec 的一部分 — 從 spec 生成的 Gherkin scenarios 的白話版,在 pm-intake 收斂回合由 client 拍板。QA 的唯一 oracle。
- **QA**:agent 扮演使用者、拿驗收清單實測切片的 AFK 流程。QA 全綠只代表「可以 demo」,不代表過關。
- **Works-but-wrong**:程式能動、但不是 client 要的東西。靠獨立 judge 對 spec 原句覆核來抓。
- **Blocking issue**:驗收清單直接 fail 的問題。修完才能 demo。
- **Known issue**:非 blocking 的小毛病。帶著 demo,開頭告知,收尾由 client 整批確認處置(現在修 / 之後修 / 不修)。
- **Demo checkpoint**:QA 過後 client 親手操作切片的驗收點 — 可點的 link + 白話 demo script + QA 報告摘要。
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
