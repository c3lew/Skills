# Spec: `pm-intake`

**類型**:自建 skill(HITL)。取代 grilling 面對 client 的位置;grilling 保留給 engineer-mode 與 wayfinder 建圖。

## 職責

把 client 的 feature 級需求訪談成可拍板的 spec:設計樹走完、兩軸分流問題、收斂回合定案,同 session 呼叫 `/to-spec` 產 spec。

## 觸發與入口

- 已經清楚的 feature 級需求 → 直接 `/pm-intake`。
- 大模糊 idea → 先 `/wayfinder` 建圖;map 的 Decisions so far 是 pm-intake 的輸入,**不重問**,訪談只補 map 沒切到的細節。

## 輸入

- Client 的需求描述(白話)。
- 若來自 wayfinder:map 的 Decisions so far + 相關 ticket resolutions。
- 既有 spec / CONTEXT.md / design system 文件(如有)。

## 行為

1. 引用 `docs/disciplines/pm-interview.md` 全套:兩軸對齊測試、每輪 ≤3 題、開放情境題優先。
2. 完整設計樹(保留 grilling/wayfinder 的深度),每個節點過兩軸測試分流「問 client / 自動拍板」。
3. 自動拍板依 `docs/disciplines/tech-decisions.md`:依據型查證、決策投影、三行制。
4. 訪談中遇到長相/操作感分岔且沒把握 → inline 呼叫 `ui-mockup`(見其 spec),拍板 prototype 入 spec。
5. 收斂回合(一次做完):自動拍板白話清單 → devil's advocate pass → 相對成本標注 → 驗收清單拍板。
6. 請 client 同 session 打 `/to-spec` 收斂(原件 user-invoked,agent 不能代叫)(to-spec 吃訪談對話 context — 這是「一環節一 session」的唯一例外)。

## 產出與交棒

- Spec issue:含 Implementation Decisions(正本)、驗收清單(QA oracle)、拍板 prototype link(如有)。
- 決策投影 comments 發到 tracker。
- Ticket comment 交棒:「下一步:`/slice-tickets #N`」。

## 引用

`docs/disciplines/pm-interview.md`、`docs/disciplines/tech-decisions.md`;呼叫原件 `/to-spec`、`/research`(查證),薄層 `ui-mockup`。
