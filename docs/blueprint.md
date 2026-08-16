# 藍圖:逐環節接線圖

本檔是「像軟體公司一樣開發」skills 系統的藍圖 index — 開發生命週期每個環節用哪個
skill、哪些用 matt-pocock 原件、哪些薄層 wrap、哪些自建取代,以及環節之間的交棒點。
各 skill 的 spec 在 `docs/specs/`,引用規範在 `docs/disciplines/`,試點計畫在
`docs/pilot-quacket.md`。

## Skill specs(建置時每個 skill 一個 session,只載自己那份)

| Skill | Spec | 型態 |
|-------|------|------|
| `pm-intake` | [specs/pm-intake.md](specs/pm-intake.md) | 自建(HITL) |
| `ui-mockup` | [specs/ui-mockup.md](specs/ui-mockup.md) | 薄層 wrap `/prototype`(HITL) |
| `slice-tickets` | [specs/slice-tickets.md](specs/slice-tickets.md) | 薄層 wrap `/to-tickets` |
| `qa` | [specs/qa.md](specs/qa.md) | 自建(AFK) |
| `client-demo` | [specs/client-demo.md](specs/client-demo.md) | 自建(HITL) |
| `tracking-viz` | [specs/tracking-viz.md](specs/tracking-viz.md) | 自建(AFK) |
| `maintain` | [specs/maintain.md](specs/maintain.md) | 薄層 wrap `/triage` |
| `retro` | [specs/retro.md](specs/retro.md) | 自建(AFK + 點頭把關) |

**安裝模式**:本 repo 是 source of truth;建置時 copy 到 `~/.claude/skills/`
(user 級,跟 matt-pocock 套件同層並存,全專案生效)。Spec 寫到 spec 級即止 —
SKILL.md 文案由建置 session 撰寫、靠 Quacket 試點實跑打磨。

各角色的設計討論脈絡見對應 issue:pm-intake #5、qa/client-demo #6、tracking-viz #7、
ui-mockup #8、技術決策層 #9、維護流程 #10、接線圖 #11、組裝 #12、發佈/維運/retro #13。

## 三條總原則

1. **一環節一 session**:每個環節獨立 session 跑,吃 context smart zone(#2)。
   唯一例外:pm-intake → to-spec 同 session(to-spec 吃訪談對話 context)。
2. **Ticket 當接力棒**:session 收尾把產出 link +「下一步跑什麼指令」寫回 ticket
   comment,label/state 標記進度;下一個 session 以 `/skill #N` 冷啟動。
3. **手動開下一棒,dashboard 指路**:不自動 spawn 下一環節;dashboard hero 顯示
   「現在在哪 + 下一步指令」,複製貼上即走。

## Greenfield 產線

| # | Session | 用什麼 | 關係 | 交棒(寫回 ticket) |
|---|---------|--------|------|---------------------|
| 0 | 專案起始 | git init → private repo → setup-matt-pocock-skills | 現有 workflow | — |
| 1 | 大模糊 idea | `/wayfinder` | **原件**;map Notes 引用 PM 訪談紀律 | map + decision tickets |
| 2 | 需求訪談 + spec | `pm-intake`(同 session 呼叫 `/to-spec`) | **自建**;to-spec 原件 | spec(Implementation Decisions + 驗收清單 + 拍板 prototype link) |
| 2a | 長相分岔(訪談中 inline) | `ui-mockup` | **自建薄層** wrap `/prototype` | 拍板 prototype → 入 spec、當 QA 視覺 oracle |
| 3 | 切票 | `slice-tickets` | **自建薄層** wrap `/to-tickets` | vertical slice tickets,每張標注覆蓋的驗收項 |
| 4 | 實作(每張 ticket) | `build`(wrap `/implement`:tdd + code-review,補交棒) | **薄層 wrap** | 完成 comment +「下一步:/qa #N」 |
| 5 | QA | `qa` | **自建**(AFK) | 綠 →「下一步:demo」;fail → 開 ticket 回 4(blocking 修完才 demo) |
| 6 | 驗收 | `client-demo` | **自建**(HITL) | 過關 → regression 固化 + **過關即發**(build + 換裝 + release note);「不對」四分類回流 |
| 7 | 追蹤(隨時) | `tracking-viz` | **自建** | 讀 GitHub Issues 產靜態 HTML dashboard |

### 入口分流

- 大而模糊的 idea → `/wayfinder` 建圖,map 的每張 HITL ticket = 一次 PM 式訪談 session。
- 已經清楚的 feature 級需求 → 跳過 wayfinder,直接 `pm-intake`。

### wayfinder ↔ pm-intake 的縫

- **骨架 vs 談話紀律**:wayfinder 管結構(map/tickets/blocking/fog),PM 訪談紀律管
  談話內容;接法是 map `## Notes` 寫「HITL ticket 一律引用 PM 訪談紀律」。
- **出口交棒**:map 走完後每個 feature 仍走 pm-intake → to-spec,但 map 的
  Decisions so far 是 pm-intake 的輸入,**不重問**;訪談只補 map 沒切到的細節。

### QA → demo → 過關 loop

`build` → `qa`(regression 先跑 + 驗收清單 walkthrough + 獨立 judge 抓
works-but-wrong)→ blocking 清零 → `client-demo`(client 親手操作)→
「不對」四分類回流(spec 錯回 pm-intake / 實作錯開 bug ticket / 新想法開 feature
ticket / 技術拍板錯重拍)→ 過關(client 點頭 + blocking 清零 + known issues 有
處置 + regression 全綠 + 高價值 scenarios 固化)。

## 維護產線

| 環節 | 用什麼 | 關係 |
|------|--------|------|
| 維護進件 | `maintain`(wrap `/triage`,補四 delta:tech-debt 類別 / 兩軸分流 / 分級閉環 / refactor 結案儀式) | **自建薄層** |
| Bug | mini-intake → 開票 → `/implement` → `qa` → client 點頭閉環 | 原件 + 自建 |
| 改功能 | 兩軸分流:輕量一輪確認 或 完整 pm-intake(+ui-mockup) | 自建 |
| 技術債 | backlog 攢批,白話三行制定期報;執行 AFK,regression 全綠即結 | 自建慣例 |
| 架構重構 | `/improve-codebase-architecture` | **原件** + 結案儀式 invariant(ticket + regression 全綠 + 決策投影) |
| 監控 | 本機 error log,`maintain` session 開頭順掃 → agent-自撿 ticket | 自建慣例 |
| Solo retro | `retro`(攢批觸發、全 AFK、amendment 經點頭落地) | **自建** |

## 橫切層

- **技術決策紀律**(依據型查證 / 白話三行制 / 決策投影):**引用規範文件**,不是
  skill — pm-intake、implement 收尾、維護層的 SKILL.md 都指向它;查證用 `/research`
  原件 fan-out。
- **PM 訪談紀律**(兩軸對齊測試 / 情境問法 / 每輪 ≤3 題 / 收斂回合 / 白話三行制):
  **引用規範文件** — pm-intake 主用,wayfinder map Notes 引用,mini-intake 是輕量版。

## 引用規範清單(`docs/disciplines/`,內容已定稿)

| 檔案 | 一行 scope |
|------|-----------|
| [`pm-interview.md`](disciplines/pm-interview.md) | 怎麼跟 client 談話:兩軸測試、情境問法、節奏、收斂回合 |
| [`tech-decisions.md`](disciplines/tech-decisions.md) | 技術決策怎麼拍:依據型查證、三行制、決策投影、修正回路 |

## Desktop app 的 QA 路線

Web 切片 QA 走 Playwright MCP;desktop(Tauri)切片 QA 環境 = **Vite dev server +
injected fakes 在瀏覽器跑**(前提:UI 為 pure reducer + injected seams),原生殼行為
(tray / hotkey / updater)由 client-demo 親手操作把關。詳見 `specs/qa.md`。

## 發佈 / 維運 / Solo retro(#13 amendment)

使用者專案形態:desktop app(Tauri)裝在自己 PC 上日用,單機單使用者。
三條線都是重用現有機制,唯一新 skill 是 `retro`。

### 發佈:過關即發

- 發佈不是獨立 session,是 client-demo 過關 checklist 的**最後一格**:agent build
  新版 + 直接換裝本機(app 重啟一次,client 在場)。
- 前提:build/deploy pipeline 全自動化,第一個切片過關前建好(技術決策,系統自拍)。
- Rollback:留上一版 installer,反悔成本 = 裝回去。
- 每次發佈在 dashboard 留一行白話 release note — 維護進件時對版本用。

### 監控:本機 error log + agent 掃

- App 錯誤寫本機結構化 error log;agent 每次 `maintain` session 開頭順掃,
  新錯 → agent-自撿 ticket(分級閉環:regression 綠即結)。
- Dashboard 顯示「上次掃到 N 個新錯誤」。
- 換機 / 多機時升級 Sentry Tauri SDK(反悔成本低)。

### Solo retro:攢批、全 AFK、amendment 出口

- 見 [`specs/retro.md`](specs/retro.md)。餵食口:拍板錯更正的「當初為什麼拍錯」、
  tech-debt backlog、demo 抓到的 QA 漏抓。
- 攢到門檻 dashboard 提示,client 說跑才跑;AFK 產報告 + 提案,client 逐條點頭
  才動 disciplines / skills — 系統自我升級的唯一入口。

## 成效檢驗

見 [`pilot-quacket.md`](pilot-quacket.md):以 Quacket 為歷史對照的 A/B 試點 —
全新 feature 走全產線,舊 25 張 issues 當 baseline,輕量記錄 + client debrief。

## 原件去留總表

| matt-pocock 原件 | 去留 |
|------------------|------|
| wayfinder / tdd / code-review / prototype / research / improve-codebase-architecture / domain-modeling | **照用不改**(部分被自建層呼叫或 wrap) |
| to-tickets / to-spec / triage / implement | **fork 收編進本 repo**(拿掉 disable-model-invocation,wrap/自建層直接呼叫;upstream 更新手動 port) |
| to-tickets | **薄層 wrap** by `slice-tickets`(補驗收項標注) |
| implement | **薄層 wrap** by `build`(補交棒 comment) |
| grilling(對 client) | **被 pm-intake 取代**;保留給 engineer-mode 與 wayfinder 建圖 |
