# Spec: `maintain`

**類型**:自建薄層 skill,wrap 原件 `/triage`。維護 / brownfield 的進件入口。

## 職責

上線後 client 白話丟來的問題或想法(bug / 改功能 / 技術債)走 `/triage` 的 state machine 進件,補四個 delta。不重造 state machine、不另造維護執行 skill(執行一律 `/build`(wrap `/implement`)→ `/qa`)。

## 觸發與入口

Client 白話進件為主;client 自開 issue 也收(標 `needs-triage`)。分類重用「不對」四分類的日常版:bug ≈ 實作錯、改功能 ≈ 新想法。

## 四個 delta(相對 `/triage` 原件)

1. **`tech-debt` 類別**:agent 觀察到的技術債開 ticket 掛 `tech-debt` + `needs-triage` 攢批,白話三行制定期報,client 只決定「現在做 / 之後 / 不做」;執行 AFK,驗收 = regression 全綠(可見行為不變)。
2. **改功能兩軸分流**:agent 用影響 × 把握提議走輕量版(一輪確認 + 只更新動到的驗收項)或完整 pm-intake(+需要時 ui-mockup),client 確認。
3. **分級閉環**:client 報的 bug 要 client 點頭才閉環(只有他知道「好了沒」);agent 自撿的 regression 綠 + 白話回報即結。
4. **Refactor 結案儀式**:任何 refactor(含 `/improve-codebase-architecture` 拍板者)的 invariant — 沒有 ticket + regression 全綠 + 決策投影就不算做過。小的當場做、事後補 ticket;大的開 `tech-debt` + `ready-for-agent` 進 backlog(已 grilling 過不重跑 needs-triage)。改動會動到可見行為 → 不是 refactor,分流為改功能 ticket。

## Bug mini-intake

追問到「能重現 + 期望行為清楚」為止,每輪 ≤3 題、只問 client 看得到的事;複述確認後開 ticket。重現不了標 `needs-info`,不瞎猜。`/triage` 的 verify-before-grill(先重現再談)直接沿用。

## 行為規則

- **Spec 永遠是正本**:bug fix 通常不動 spec;bug 暴露 spec 漏洞就補驗收項;改功能一律回寫 spec + 驗收清單。
- **節奏**:client 報的即到即修;agent 自撿的攢批,client 丟下一件事時順帶清或明說「清 backlog」時跑,不搞排程。
- **`/improve-codebase-architecture`** 是系統唯一 engineer-mode 入口,保持原樣,僅受結案儀式 invariant 約束;決策投影照格式發,不用再對 client 白話重講。

## 產出與交棒

分類完的 tickets 進對應產線(每張票 comment 留交棒行,雙寫格式見 `docs/blueprint.md` 接力棒):bug → `/build` → `/qa`(regression + 重現 scenario)→ 分級閉環;改功能 → 輕量確認或 pm-intake;技術債 → backlog。

## 引用

`docs/disciplines/pm-interview.md`(mini-intake 是輕量版)、`docs/disciplines/tech-decisions.md`;呼叫原件 `/triage`、`/implement`、`/qa`、`ui-mockup`。
