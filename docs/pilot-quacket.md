# Quacket A/B 試點計畫

驗證新系統(本藍圖)是否比舊做法更好。對照物:[Quacket](https://github.com/c3lew/Quacket) — 已 ship 到 v0.2.5 的 Tauri v2 + React tray 工具,issue-driven 開發、matt-pocock 慣例已裝、測試密(26 個 Vitest 檔 + Rust 端)。

## 形式:歷史對照(不跑真 A/B)

- **Baseline(舊做法)**:Quacket 既有 25 張 issues 的實績 — 訪談怎麼問、rework 幾次、哪些 works-but-wrong 漏到 client 手上。tracker 就是現成資料,不重跑。
- **Treatment(新系統)**:一個**全新 feature idea** 從 `pm-intake` 一路走到過關,全 greenfield 產線覆蓋(pm-intake → to-spec → slice-tickets → implement → qa → client-demo → tracking-viz)。
- 真 A/B(同 feature 跑兩遍)不採:雙倍工 + 學習效應污染;兩個不同 features 各走一套也不採:沒對照性。

## 範圍

1. **主菜**:全新 feature 全產線走完(題目開跑時由 client 挑,不提前佔位)。
2. **順跑**:試點期間自然冒出的 bug / 小改,走 `maintain` 維護產線(mini-intake、分級閉環、tech-debt backlog 都試得到),幾乎零額外成本。
3. **不硬塞**:現成 open 的 Quacket #24(crash-safe filing)照舊做法走完,不進試點 — 它已有 spec,會跳過產線前半。

## Desktop QA 環境

Quacket 的架構剛好對縫:UI 是 pure reducer + injected seams(fake-runner、fake files)。QA 環境定為 **Vite dev server + fakes 在瀏覽器跑**,給 Playwright 測;Tauri 原生殼行為(tray、global hotkey、updater)由 client-demo 親手操作把關。此路線已寫入 `docs/specs/qa.md`。

## 評量:輕量記錄,不搞正式實驗

n=1 要的是「哪裡明顯更好/更糟」的訊號,不是統計:

- **過程指標(順手記,tracker 上本來就有痕跡)**:訪談/來回輪數、rework 次數、QA 攔到的 defect 數、works-but-wrong 有沒有在 demo 前被攔下。
- **結果體感**:試點收尾 client 寫一份主觀 debrief — 這是不是我要的、過程累不累、跟舊做法比哪裡有感。
- 對照讀法:新系統的痕跡 vs 舊 25 張 issues 的同類痕跡。

## 開跑條件與步驟

1. 藍圖 skills 建置完成(specs → SKILL.md → copy 到 `~/.claude/skills/`,見 blueprint 建置章)。
2. Client 挑定新 feature 題目。
3. 在 Quacket repo 開 feature ticket,從 `/pm-intake` 起跑;此後每環節按 ticket 接力棒交棒。
4. 過關後寫 debrief,對照 baseline,決定系統哪裡要修 — 修正回饋回本 repo 的 specs。
