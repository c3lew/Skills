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
- **「不對」三分類**:demo 時 client 否決的三種來源 — spec 理解錯(回 pm-intake)、實作錯(bug ticket 走 QA loop)、新想法(新 feature ticket)。agent 提分類建議,client 確認。
- **過關 (slice done)**:client 親口 OK + blocking 清零 + known issues 都有處置決定 + regression suite 全綠 + 高價值 scenarios 已固化。
- **Regression 固化**:切片過關後,高價值 scenarios 轉成 Playwright regression test,之後每次 QA 先跑。
