# 藍圖骨架:逐環節接線圖

本檔是「像軟體公司一樣開發」skills 系統的骨架 — 開發生命週期每個環節用哪個 skill、
哪些用 matt-pocock 原件、哪些薄層 wrap、哪些自建取代,以及環節之間的交棒點。
血肉(各 skill 的完整 SKILL.md 規格)由「組裝藍圖」階段補上。

各角色的設計細節見對應 issue:pm-intake #5、qa/client-demo #6、tracking-viz #7、
ui-mockup #8、技術決策層 #9、維護流程 #10、本接線圖 #11。

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
| 3 | 切票 | wrap `/to-tickets` | **自建薄層** | vertical slice tickets,每張標注覆蓋的驗收項 |
| 4 | 實作(每張 ticket) | `/implement`(tdd + code-review) | **原件** | 完成 comment +「下一步:/qa #N」 |
| 5 | QA | `qa` | **自建**(AFK) | 綠 →「下一步:demo」;fail → 開 ticket 回 4(blocking 修完才 demo) |
| 6 | 驗收 | `client-demo` | **自建**(HITL) | 過關 → regression 固化;「不對」四分類回流 |
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

`/implement` → `qa`(regression 先跑 + 驗收清單 walkthrough + 獨立 judge 抓
works-but-wrong)→ blocking 清零 → `client-demo`(client 親手操作)→
「不對」四分類回流(spec 錯回 pm-intake / 實作錯開 bug ticket / 新想法開 feature
ticket / 技術拍板錯重拍)→ 過關(client 點頭 + blocking 清零 + known issues 有
處置 + regression 全綠 + 高價值 scenarios 固化)。

## 維護產線

| 環節 | 用什麼 | 關係 |
|------|--------|------|
| 維護進件 | wrap `/triage`(補四 delta:tech-debt 類別 / 兩軸分流 / 分級閉環 / refactor 結案儀式) | **自建薄層** |
| Bug | mini-intake → 開票 → `/implement` → `qa` → client 點頭閉環 | 原件 + 自建 |
| 改功能 | 兩軸分流:輕量一輪確認 或 完整 pm-intake(+ui-mockup) | 自建 |
| 技術債 | backlog 攢批,白話三行制定期報;執行 AFK,regression 全綠即結 | 自建慣例 |
| 架構重構 | `/improve-codebase-architecture` | **原件** + 結案儀式 invariant(ticket + regression 全綠 + 決策投影) |

## 橫切層

- **技術決策紀律**(依據型查證 / 白話三行制 / 決策投影):**引用規範文件**,不是
  skill — pm-intake、implement 收尾、維護層的 SKILL.md 都指向它;查證用 `/research`
  原件 fan-out。
- **PM 訪談紀律**(兩軸對齊測試 / 情境問法 / 每輪 ≤3 題 / 收斂回合 / 白話三行制):
  **引用規範文件** — pm-intake 主用,wayfinder map Notes 引用,mini-intake 是輕量版。

## 引用規範清單(`docs/disciplines/`,內容待組裝階段)

| 檔案 | 一行 scope |
|------|-----------|
| `pm-interview.md` | 怎麼跟 client 談話:兩軸測試、情境問法、節奏、收斂回合 |
| `tech-decisions.md` | 技術決策怎麼拍:依據型查證、三行制、決策投影、修正回路 |

## 原件去留總表

| matt-pocock 原件 | 去留 |
|------------------|------|
| wayfinder / to-spec / implement / tdd / code-review / prototype / research / triage / improve-codebase-architecture / domain-modeling | **照用不改**(部分被自建層呼叫或 wrap) |
| to-tickets | **薄層 wrap**(補驗收項標注) |
| grilling(對 client) | **被 pm-intake 取代**;保留給 engineer-mode 與 wayfinder 建圖 |
