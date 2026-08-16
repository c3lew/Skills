---
name: pm-intake
description: 把 client 的 feature 需求訪談成可拍板的 spec:兩軸分流問題、自動拍板留紀錄、收斂回合定案,同 session 接 /to-spec。當 client 白話描述一個清楚的 feature 需求,或 wayfinder map 交棒某個 feature 要進 spec 時使用;大而模糊的 idea 先走 /wayfinder 建圖。
---

# pm-intake

把使用者當 **client**,不當工程師:只訪談他看得到的行為(功能、長相、操作感)與現實取捨,技術決策系統自己拍、自己留紀錄。走完設計樹、收斂回合定案,同 session 接 `/to-spec` 產 spec。

規則書(開工前先讀完,全程遵守):

- [`references/pm-interview.md`](references/pm-interview.md) — 訪談紀律:兩軸對齊測試、問法節奏、收斂回合。
- [`references/tech-decisions.md`](references/tech-decisions.md) — 自動拍板:依據型查證、白話三行制、決策投影、修正回路。

## 1. 定輸入

- 直接進來:client 的白話需求描述。
- 從 wayfinder 來:先讀 map 的 Decisions so far 與相關 ticket resolutions — 已定案的**不重問**,訪談只補 map 沒切到的細節。
- 既有 spec、CONTEXT.md、design system 文件(如有)一併讀。

## 2. 訪談 loop

展開這個 feature 的完整設計樹 — 功能、長相、操作感、資料、失敗情境 — 每個待決節點過兩軸對齊測試分流:

- **必須問** → 排進下一輪,照問法節奏出題。
- **自動拍板** → 照 tech-decisions 拍:依據型判準決定要不要先丟 `/research` 查證;拍板當下發決策投影 comment 到 tracker。
- **長相/操作感分岔、沒把握 client 會怎麼選** → inline 呼叫 `/ui-mockup`,client 拍板的 prototype 入 spec。

輪替直到設計樹每個節點都問過或拍過,沒有懸空節點。

## 3. 收斂回合

照 pm-interview 的「收斂回合」四步一次做完:自動拍板白話清單 → devil's advocate → 相對成本標注(不給時數)→ 驗收清單拍板。完成標準:四步每一步都拿到 client 的明確回應;清單被否決的項目照 tech-decisions 的修正回路當場改拍重報。

## 4. 產 spec + 交棒

原件 user-invoked,agent 不能代叫 — 請 client 同 session 打 `/to-spec`(「一環節一 session」的唯一例外 — to-spec 要吃訪談對話 context)。Spec issue 必含:Implementation Decisions(正本)、拍板的驗收清單(QA 的唯一 oracle)、拍板 prototype link(如有)。

收尾在 ticket 留 comment:產出 link +「下一步:`/slice-tickets #N`」。
