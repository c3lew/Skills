---
name: maintain
description: 上線後的進件入口:薄層 wrap /triage,client 白話報的 bug / 改功能 / 想法走原件 state machine 分類,補四 delta(tech-debt 攢批、改功能兩軸分流、分級閉環、refactor 結案儀式)+ bug mini-intake + session 開頭 error log 順掃。當上線後 client 丟問題或想法、client 自開 issue、或 client 說要清 tech-debt backlog 時使用;執行不在此 — 分類完指路 /implement。
---

# maintain

薄層 wrap 原件 `/triage`:state machine、roles、agent brief、verify-before-grill 全依原件,本檔只補維護情境的 deltas。本 skill 只做進件與分類,執行一律走 `/implement` → `/qa`。

規則書(開工前先讀完):

- [`references/pm-interview.md`](references/pm-interview.md) — 訪談紀律;mini-intake(§3)與兩軸分流(§4)是它的輕量應用。
- [`references/tech-decisions.md`](references/tech-decisions.md) — 白話三行制、決策投影。

## 1. Session 開頭:error log 順掃

先掃本機結構化 error log(位置見專案 CONTEXT.md / spec)。上次掃描後的新錯,每個開一張 agent-自撿 ticket(bug + `needs-triage`,票上註明「agent-自撿」)。找不到 log 檔就回報一句、繼續往下。

## 2. 進件分類

用「不對」四分類的日常版分流:**bug** ≈ 實作錯、**改功能** ≈ 新想法;agent 觀察到的技術債 → **tech-debt**(§5)。client 自開的 issue 標 `needs-triage` 一併收進 `/triage` 的 buckets。分不清是 bug 還是改功能時,以驗收清單為準:違反已拍板驗收項的是 bug,其餘是改功能。

## 3. Bug:mini-intake → 開票

`/triage` 的 verify-before-grill 沿用:先照 client 描述重現。追問到「能重現 + 期望行為清楚」為止 — 每輪 ≤3 題、只問 client 看得到的事;複述確認後開票。重現不了 → `needs-info`,票上寫已確立事實 + 還缺什麼,等 client 補,不瞎猜。

票上標**分級閉環**,close 條件由誰報的決定:

- **client 報的** → fix 過 `/qa` 後要 client 點頭才 close(好了沒只有他知道)。
- **agent 自撿的** → regression 綠 + 白話回報即 close。

Spec 永遠是正本:bug fix 通常不動 spec;bug 暴露 spec 漏洞(驗收清單沒擋住它)就補驗收項。

## 4. 改功能:兩軸分流

過兩軸對齊測試(影響 × 把握,見 `references/pm-interview.md`),提議走哪條、client 確認:

- **輕量版**(影響小或有把握):一輪確認(≤3 題)+ 只更新動到的驗收項,開票。
- **完整版**(影響大且沒把握):指路 `/pm-intake`;長相/操作感分岔再由它接 `/ui-mockup`。

無論哪條,改功能一律回寫 spec + 驗收清單。

## 5. Tech-debt:攢批

agent 觀察到的技術債開票掛 `tech-debt` + `needs-triage` 攢批,不打斷 client。client 丟下一件事時順帶、或明說「清 backlog」時,把攢的票用白話三行制(見 `references/tech-decisions.md`)整批報,client 只決定「現在做 / 之後 / 不做」。拍「現在做」的執行 AFK,驗收 = regression 全綠(可見行為不變)。

## 6. Refactor 結案儀式

Invariant:任何 refactor — 含 `/improve-codebase-architecture` 拍板的 — 要有 **ticket + regression 全綠 + 決策投影**三樣才算做過。

- 小的:當場做,事後補 ticket + 投影。
- 大的:開票掛 `tech-debt` + `ready-for-agent` 進 backlog(拍板時已 grilling 過,不重跑 `needs-triage`)。
- 改動會動到可見行為 → 那不是 refactor,回 §4 當改功能分流。

`/improve-codebase-architecture` 是系統唯一 engineer-mode 入口,保持原樣,僅受本 invariant 約束;決策投影照它的格式發即可,不用對 client 白話重講。

## 7. 節奏與交棒

Client 報的即到即修;agent 自撿的照 §5 攢批,不搞排程。分類完的票進對應產線,每張票 comment 下一步指令當接力棒:

- bug → 「下一步:`/implement #N`」,票上附重現 scenario(`/qa` 要跑 regression + 這個 scenario)。
- 改功能 → 輕量票同上;完整版寫「下一步:`/pm-intake`」。
- tech-debt → 留在 backlog,等 §5 的批次拍板。
