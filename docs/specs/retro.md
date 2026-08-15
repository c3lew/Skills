# Spec: `retro`

**類型**:自建 skill(AFK + 點頭把關)。solo retro — 系統自我升級的唯一入口。

## 職責

消化系統留下的紀錄,產出白話 retro 報告 + amendment 提案清單;client 逐條點頭後,
把 amendment 落到 Skills repo 的 disciplines / skills(改一處全體生效)。
不是對話式檢討 — 原料全來自紀錄,不從 client 腦袋挖素材。

## 觸發

不排程,攢批:餵食口累積到門檻時 dashboard 提示「該 retro 了」,client 說跑才跑。
門檻值是技術決策,系統自拍(留紀錄)。

## 餵食口(feeds)

1. **拍板錯更正 comment** 的固定一行「當初為什麼拍錯」(見 `disciplines/tech-decisions.md`)。
2. **Tech-debt backlog**(`tech-debt` tickets 的累積 pattern)。
3. **QA 漏抓**:demo 時被 client 抓到的「實作錯」= QA 該抓沒抓,「不對」分類 comment 即紀錄。

## 流程

1. AFK 掃三個餵食口,找 pattern(單一事件不成案,重複才是 signal)。
2. 產出白話 retro 報告:發現了什麼 pattern → 建議改哪份 discipline / skill → 改了之後差在哪。
3. 報告固定留一格「你有沒有要補充的觀察」— 有就聊,沒有就結。
4. Client 逐條「改 / 不改」點頭;點頭才動文件,並發決策投影。
5. 已消化的餵食項標記處理過,下次 retro 不重讀。

## 行為規則

- Amendment 只動 Skills repo 的 `docs/disciplines/` 與 skills 文件,不動專案 spec(那是 pm-intake / maintain 的事)。
- 提案用白話三行制格式報(做什麼修改 / 對流程的影響 / 反悔成本)。
- 沒 pattern 就老實說「這批料不足以成案」,不硬擠提案。

## 引用

`docs/disciplines/tech-decisions.md`(決策投影、修正回路);讀 tracker comments 與
`tech-debt` backlog;寫 `docs/disciplines/` 與 skills 文件(經 client 點頭)。
