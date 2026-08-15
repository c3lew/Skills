# Spec: `client-demo`

**類型**:自建 skill(HITL)。

## 職責

QA 過後的驗收點:client **親手操作**切片、處理「不對」、判定過關。UAT 本質需要人 — 看錄影會漏操作感,agent 不代答。

## 觸發與入口

`qa` 綠(blocking 清零)後,ticket comment 指路「下一步:`/client-demo #N`」。

## 輸入

- 可點的 link(跑起來的切片)。
- 驗收清單 + QA 報告摘要。
- Known issues 清單。

## 行為

1. **Demo checkpoint**:給 client 可點的 link + 一頁照驗收清單走的白話 demo script + QA 報告摘要;開頭白話告知 known issues。
2. Client 說「不對」→ agent 當場提**四分類**建議(白話解釋差別,client 確認,agent 只建議不硬拍):
   - spec 理解錯 → 回 pm-intake 改 spec
   - 實作錯 → bug ticket 走 QA loop
   - 新想法 → 新 feature ticket 排優先
   - 技術拍板錯 → 依 `tech-decisions.md` 修正回路重拍,不重訪 client
3. 修完只 re-demo 受影響的驗收項,不整片重走;client 說「不對」的點要 client 點頭才閉環。
4. **Known issues 收尾**:agent 給每條建議處置(現在修 / 開 ticket 之後修 / 不修留紀錄),client 整批確認、有意見才挑出來。
5. **過關判定**(全部成立才算):client 親口 OK + blocking 清零 + 每條 known issue 都有處置決定 + regression suite 全綠 + 高價值 scenarios 已固化。

## 產出與交棒

- 過關 → regression 固化(交 `qa` 執行)、ticket 關閉、dashboard 更新。
- 「不對」→ 對應分類的回流 ticket。

## 引用

`docs/disciplines/pm-interview.md`(對 client 語言)、`docs/disciplines/tech-decisions.md`(拍板錯回路);依賴 `qa` 的報告。
