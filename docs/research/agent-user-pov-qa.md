# AI Agent 扮演使用者做 QA:對著 spec 實際操作產品的作法調查

> 調查日期:2026-08-15。所有 claim 都對過 primary source(官方 docs / README / 第一方 blog),查不到的會直接標明「未驗證」。

## TL;DR

- Web 產品的最佳路徑已經很成熟:**Playwright MCP + accessibility tree snapshot**。它給 LLM 的是結構化資料不是像素,「No vision models needed, operates purely on structured data」、「Deterministic tool application」([playwright-mcp README](https://github.com/microsoft/playwright-mcp))。Claude Code 官方就有 [Playwright plugin](https://claude.com/plugins/playwright)(31 萬+ 安裝)。
- Playwright 官方自己也走 agentic 路線了:[Playwright Agents](https://playwright.dev/docs/test-agents)(planner / generator / healer)直接支援 Claude Code,`npx playwright init-agents --loop=claude`。
- 「works-but-wrong」類問題(code 沒錯但不符使用者意圖)要靠 **spec-as-oracle**:從 PRD 產生 Gherkin 式 acceptance scenarios,agent 逐條走,再用 LLM-as-judge 對 transcript 打分 — Anthropic 的 [evals 文章](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)給了具體 rubric 作法。
- 視覺層:screenshot + model judgment 適合抓「明顯壞掉」的 layout 問題;pixel-perfect regression 交給 [`toHaveScreenshot`](https://playwright.dev/docs/test-snapshots) / [Percy](https://www.browserstack.com/docs/percy) / [Chromatic](https://www.chromatic.com/docs/),LLM 看圖抓不到 1–2px 的 diff。
- 非 web:CLI 用 [pexpect](https://pexpect.readthedocs.io/en/stable/overview.html) / tmux;TUI 有 [microsoft/tui-test](https://github.com/microsoft/tui-test)(存在,active beta,還特別為 AI agent 設計了 stable exit codes);Electron 走 Playwright 的 [experimental Electron support](https://playwright.dev/docs/api/class-electron);全都不行才 fallback 到 [computer use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool)(beta、慢、貴)。
- 包成 Claude Code skill 的推薦架構:**spec → scenarios → Playwright MCP 逐條 walkthrough → 每條記 verdict + evidence → LLM-as-judge 對 spec 覆核 → 報告**。詳見最後「建議」。

---

## 1. Playwright / browser-driven acceptance walkthrough

### Playwright MCP(Claude Code 裡的主力)

[microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp) 的核心設計是用 **accessibility tree snapshot** 而不是截圖跟 LLM 溝通:「Uses Playwright's accessibility tree, not pixel-based input」,好處是「Deterministic tool application」,避免 screenshot-based 方法常見的 ambiguity。README 列的能力包括:

- **Core automation**:click、type、navigate、fill form、drag-and-drop、evaluate JS
- **Tab / network / storage**:tab 管理、mock request、offline mode、cookies/localStorage
- **DevTools 級功能**:**trace recording**、**video recording with action overlays**、element highlighting — 這對 QA 特別有價值,walkthrough 過程可以留完整證據
- **Vision mode(opt-in)**:需要座標式操作時才開,預設不用 vision model

執行模式支援 **headless / headed**、persistent profile(保留登入狀態)、isolated mode(乾淨無狀態測試)([README](https://github.com/microsoft/playwright-mcp))。Claude Code 安裝一行搞定:`claude mcp add playwright npx @playwright/mcp@latest`([playwright.dev getting started](https://playwright.dev/docs/getting-started-mcp)),或直接裝官方 [Playwright plugin](https://claude.com/plugins/playwright)。複雜情境還有 `browser_run_code_unsafe` 可以直接跑 Playwright script([getting started](https://playwright.dev/docs/getting-started-mcp))。

### Playwright 自己的 agentic 方向:Playwright Agents

[playwright.dev/docs/test-agents](https://playwright.dev/docs/test-agents) 確實存在,定義了三個 agent 的 pipeline:

1. **Planner** — 「explores the app and produces a Markdown test plan」:給它一句需求(例如 "Generate a plan for guest checkout"),它實際去逛 app,產出含步驟與 expected outcome 的 markdown plan
2. **Generator** — 吃 plan,「verifies selectors and assertions live as it performs the scenarios」,邊操作邊驗證 selector,產出可執行的 Playwright test
3. **Healer** — 「executes the test suite and automatically repairs failing tests」:replay 失敗步驟、找 equivalent element、patch locator / wait 再重跑

支援環境包含 **Claude Code**、VS Code(1.105+)、Codex、OpenCode,setup 是 `npx playwright init-agents --loop=claude`。這基本上就是官方版的「agent 扮演使用者 → 固化成 regression test」流程,而且 artifact 約定清楚(`specs/` 放 plan、`tests/` 放產出的 test)。

**對 QA skill 的啟示**:Planner 的「先探索、產 markdown plan」跟 Healer 的「失敗時看 UI 找等價元素」這兩個 pattern 可以直接借用,即使不用完整的 Playwright Agents 工具鏈。

## 2. Anthropic 第一方資源

### Computer use tool

[官方 docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool):beta 功能(header `computer-use-2025-11-24`),提供 screenshot capture + mouse/keyboard control,支援 Opus 5 / Sonnet 5 / Opus 4.x 等。重點限制與 best practice(皆出自官方文件):

- 「Claude sometimes assumes outcomes of its actions without explicitly checking their results」— 官方建議每步截圖驗證後才前進
- dropdown、scrollbar 這類元件「might be tricky for Claude to manipulate using mouse movements」,建議改用 keyboard shortcuts
- prompt injection 風險:頁面內容可能 override 你的指令,登入情境要特別隔離
- 新版 tool 有 `enable_zoom` 可以放大看小字(sidebar 檔名、status bar 等)
- Thinking effort 有官方調參建議(Sonnet 4.6/Opus 4.6 用 `medium`,`max` 「adds token cost without improving accuracy on UI tasks」)

結論:computer use 是**通用但昂貴**的 fallback — 每步一張截圖進 context,token 成本跟 latency 都遠高於 accessibility tree。web 有 Playwright MCP 就不要用它。

### Agent evals(對 QA 判定很關鍵)

[Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) 把 grader 分三類:code-based(快、客觀但「brittle to valid variations」)、model-based(能處理 nuance 但 non-deterministic)、human(gold standard 但貴)。LLM-as-judge 的具體建議:

- 用「clear, structured rubrics to grade each dimension of a task, and then grade each dimension with an isolated LLM-as-judge」— 分維度、每維度獨立 judge,比一個大 judge 可靠
- 「give the LLM a way out」— 資訊不足時允許回 "Unknown",不要逼它硬判
- 「grade what the agent produced, not the path it took」— 判結果不判路徑
- 讀 transcript 是必要功課:「the transcript tells you whether the agent made a genuine mistake or whether your graders rejected a valid solution」

### Claude Agent SDK

[Agent SDK 的 MCP docs](https://code.claude.com/docs/en/agent-sdk/mcp) 確認:SDK 可以在 code 裡或 `.mcp.json` 掛任意 MCP server(含 Playwright MCP),用 `allowedTools: ["mcp__playwright__*"]` 授權。也就是說「QA agent 走 browser」這件事可以脫離互動式 Claude Code、包成 headless 的 SDK 程式跑在 CI 裡。SDK 沒有專門的 browser automation API — browser 能力就是透過 MCP 來的。

## 3. 從 spec 產生 user scenarios:BDD / Gherkin

[Cucumber 官方 BDD docs](https://cucumber.io/docs/bdd/) 定義的三步 loop 剛好對映 LLM QA 的 pipeline:

1. **Discovery**(what it *could* do)— 用具體 examples 探索需求 → LLM 讀 PRD/spec,列出使用者情境與 edge cases
2. **Formulation**(what it *should* do)— examples 寫成人機皆可讀的 executable specification → LLM 產出 Gherkin 式 Given/When/Then scenarios
3. **Automation**(what it *actually does*)— 自動驗證 → agent 拿 scenarios 去實際操作產品

BDD 的賣點「system documentation that is automatically checked against the system's behaviour」正是 spec-as-oracle 的定義。實務上 LLM 產 scenario 有兩個要點:(a) Gherkin 格式強迫每條 scenario 有明確的 expected outcome,judge 才有東西可對;(b) scenario 要在**操作前**先寫死,不能邊走邊定義成功條件,不然會發生「看到什麼就接受什麼」的 confirmation bias — 這跟 Playwright Agents 先由 Planner 產 plan、再由 Generator 執行的順序一致([test-agents](https://playwright.dev/docs/test-agents))。

## 4. 抓「works-but-wrong」:行為符合 code 但不符使用者意圖

這類 bug 的本質是 oracle 選錯了 — unit test 拿 implementation 當 oracle,所以永遠測不出「實作本身就理解錯」。對策:

- **Spec-as-oracle**:判定標準只能來自 spec/PRD 的原句,不是 code。實作方式就是第 3 節的 scenario 化 + 每條 scenario 附上它對應的 spec 語句,verdict 必須引用 spec 原文。
- **LLM-as-judge over transcripts**:walkthrough 完把 transcript(actions + snapshots + screenshots)交給獨立的 judge pass,按 [Anthropic 的建議](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)分維度用 rubric 打分、允許回 Unknown。關鍵是 judge 跟 operator 分開 — 操作的 agent 會傾向宣稱自己成功,獨立 judge 讀 evidence 比較不會護航。
- **Metamorphic / property-style checks**:不用知道正確輸出,只驗證行為間的關係(例:搜尋加一個 filter 後結果數不該變多;排序切換不該改變結果集合;重新整理後購物車不該變)。這對「沒有精確 expected output 的 spec」特別有用。註:metamorphic testing 是測試學界的成熟概念(Chen et al. 起源),但本輪沒有找到單一權威的第一方線上文件可引,此段屬方法論歸納。
- **比對 spec 語句而非實作**:報告格式上,每個 finding 都應該是「spec 說 X([引句])、觀察到 Y(附 evidence)」的配對,而不是「test failed」。這讓 works-but-wrong(行為 ≠ spec)跟 spec-gap(spec 沒講)可以分開列。

## 5. 視覺 / UX 層檢查

### Screenshot + model judgment

Playwright MCP 有 `browser_take_screenshot`,computer use 全程都是截圖。LLM 看截圖**可靠**能判的:元素明顯重疊/溢出、整塊 UI 沒 render、文字被截斷、明顯的對比問題、「這頁看起來像不像 spec 描述的東西」這類語意層判斷。**不可靠**的:1–2px 的 alignment、精確色值、字距行高微差、跨 render 的 pixel 一致性 — 官方 computer use docs 甚至要靠 `enable_zoom` 才能讀小字([docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool)),可見小尺度視覺資訊對模型本來就吃力。

### Pixel-level 工具(第一方)

- [`toHaveScreenshot`](https://playwright.dev/docs/test-snapshots):首跑自動產 baseline,filename 帶 browser + platform,因為「Screenshots differ between browsers and platforms due to different rendering, fonts and more」;官方明講 flakiness 來源包括「host OS, version, settings, hardware, power source (battery vs. power adapter), headless mode」,解法是 baseline 跟測試跑在同一環境(實務上就是 Docker)。有 `maxDiffPixels` 容差、`stylePath` 遮 dynamic content、`--update-snapshots` 更新 baseline。
- [Percy](https://www.browserstack.com/docs/percy):抓 DOM snapshot 上傳、在雲端 browser render、跟 baseline 比對,diff 走 review/approval workflow;近期還加了 AI agents 做「natural-language summaries of visual changes」跟 noise reduction。
- [Chromatic](https://www.chromatic.com/docs/):吃 Storybook stories / Playwright / Cypress,雲端跨 Chrome/Firefox/Safari/Edge 截圖比對;TurboSnap 用 git dependency graph 只測改到的 component;有 UI Review 的人工核可流程。

分工結論:**LLM 判語意與明顯壞損,pixel diff 工具判精確 regression**,兩者互補不互替。

## 6. 非 web 產品

- **CLI(non-interactive)**:最簡單,agent 直接用 shell 跑指令、驗 stdout/exit code,Claude Code 的 Bash tool 原生就能做,零額外依賴。
- **CLI(interactive)**:[pexpect](https://pexpect.readthedocs.io/en/stable/overview.html) — `spawn()` / `expect(pattern)` / `sendline()`,官方明說「especially handy if you are writing automated test tools」。限制:`pexpect.spawn` 在 Windows 不可用(依賴 Unix pty),只能退用 `PopenSpawn`,且「Many programs only offer interactive behaviour if they detect that they are running in a terminal」。跨平台替代:tmux `send-keys` + `capture-pane`(Unix)。
- **TUI**:[microsoft/tui-test](https://github.com/microsoft/tui-test) **存在**,Rust 核心、有 Node/Python/Rust bindings 跟 CLI,跨 Windows/Linux/macOS。狀態是 active beta(「in the middle of a major re-write」)。亮點是它明確為 AI agent 設計:「stable exit codes so an agent can branch on failure class without parsing text」、structured JSON context、asciinema 錄影。這是目前 TUI 測試對 agent 最友善的第一方選項。
- **Desktop / Electron**:Playwright 有 [experimental Electron support](https://playwright.dev/docs/api/class-electron)(`_electron.launch({ args: ['main.js'] })`、`firstWindow()`、可在 main process `evaluate()`)。限制:原生 dialog(showOpenDialog 等)攔不到,要用 `evaluate()` stub 掉。非 Electron 的原生桌面 app 走 WebDriver 系(未在本輪逐一驗證各 driver)或直接 fallback [computer use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool)。
- **Mobile**:簡述 — 主流是 Appium(WebDriver 協定)與 Maestro,本輪未對其官方文件做驗證,先不展開;emulator + computer use 理論可行但成本高。

## 7. 綜合評比

| 方法 | 可靠度(flakiness/determinism) | 成本(tokens/時間) | Claude Code skill 適配度 |
|---|---|---|---|
| Playwright MCP(a11y snapshot) | 高 — 結構化資料、deterministic tool application([README](https://github.com/microsoft/playwright-mcp));app 本身的 async 仍可能 flaky | 中 — snapshot 是文字,比截圖省很多 token;大頁面 snapshot 仍不小 | **最佳** — 官方 plugin 一鍵裝、tool 齊全、有 trace 佐證 |
| Playwright Agents(planner/generator/healer) | 高 — 產出是真正的 test code,可重複跑;healer 自動修 flaky locator | 生成期中,之後跑 test 幾乎零 token | 高 — 原生支援 Claude Code,適合「QA 完固化成 regression suite」 |
| Computer use(截圖+座標) | 中低 — 官方自承會 assume outcome、dropdown/scroll 難操作 | 高 — 每步一張截圖,慢且貴 | 低 — 只當萬用 fallback(原生 desktop、無 a11y 的畫面) |
| Gherkin scenario 生成(spec→scenarios) | 高 — 純文字生成,無執行面 flakiness;品質取決於 spec | 低 | 高 — skill 的第一階段,純 prompt 工作 |
| LLM-as-judge over transcript | 中 — non-deterministic,需 rubric + isolated judges 校準([Anthropic](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)) | 中 — 多一輪 model pass | 高 — 一個獨立 subagent 就能做 |
| Screenshot + vision 判斷 | 中 — 語意層可靠、pixel 層不可靠 | 中高 — 圖片 token | 中 — 當輔助檢查,不當主 oracle |
| toHaveScreenshot / Percy / Chromatic | pixel 精確,但對環境極敏感(需固定環境/雲端 render) | 低 token(不經 LLM);SaaS 要錢 | 中 — skill 可以「建議接入」,不適合 skill 內即席跑 |
| pexpect / tmux(CLI) | 高 — 但 pattern matching 對 prompt 變動敏感;Windows 受限 | 低 | 高 — 純 Bash 可驅動 |
| tui-test(TUI) | 中高 — beta 中,但 agent-friendly 設計(stable exit codes) | 低 | 中高 — npm 一裝即用,惟 API 還在 rewrite |
| Playwright Electron | 中 — experimental,原生 dialog 要 stub | 中 | 中 — Electron 專案可直接沿用 Playwright MCP 生態 |

## 建議:Claude Code QA skill 的推薦架構

**Recommended default:五階段 pipeline,web 走 Playwright MCP。** 理由:a11y snapshot 路線是唯一同時做到「deterministic、省 token、官方支援、有 trace 證據」的方案;其他都是特定情境的補位。代價是它只覆蓋 web(+Electron),以及超大頁面的 snapshot 仍會吃 context。

1. **Scenario 生成(spec → Gherkin)**:讀 PRD/spec,產出編號的 Given/When/Then scenarios,每條標注對應的 spec 原句。走 [BDD 的 Discovery→Formulation](https://cucumber.io/docs/bdd/) 精神,scenario 在操作前定稿。
2. **環境偵測與啟動**:判斷產品型態(web / CLI / TUI / Electron),選 driver:Playwright MCP(web、Electron)→ Bash/pexpect/tmux(CLI/TUI)→ computer use(僅剩原生 desktop 才用)。
3. **Walkthrough 執行**:operator agent 逐條 scenario 操作,每步 snapshot、關鍵節點截圖,開 [trace recording](https://github.com/microsoft/playwright-mcp) 留證。每條 scenario 記 PASS / FAIL / BLOCKED + evidence,不即席改判定標準。
4. **獨立 judge pass**:另開 subagent 讀 transcript + evidence,按 rubric 分維度打分(功能正確、流程順暢、錯誤處理、視覺明顯問題),允許 Unknown,verdict 必須引 spec 原文 — 完全照 [Anthropic evals 指南](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)。
5. **報告 + 固化(optional)**:輸出「spec 說 X / 觀察到 Y」格式的 findings(分 bug / works-but-wrong / spec-gap 三類);高價值 scenario 可用 [Playwright Agents](https://playwright.dev/docs/test-agents) 的 generator 固化成 regression test。

設計要點:operator 跟 judge 一定分開(避免自我護航);vision 截圖只做語意層判斷,pixel regression 建議使用者接 `toHaveScreenshot` 或 Percy/Chromatic;headed mode 留給 debug,CI 預設 headless。

## 參考資料

- [microsoft/playwright-mcp README](https://github.com/microsoft/playwright-mcp)
- [Playwright Agents(playwright.dev/docs/test-agents)](https://playwright.dev/docs/test-agents)
- [Playwright MCP getting started](https://playwright.dev/docs/getting-started-mcp)
- [Playwright plugin for Claude Code(claude.com/plugins/playwright)](https://claude.com/plugins/playwright)
- [Anthropic — Computer use tool docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool)
- [Anthropic — Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- [Claude Agent SDK — MCP docs](https://code.claude.com/docs/en/agent-sdk/mcp)
- [Cucumber — BDD docs](https://cucumber.io/docs/bdd/)
- [Playwright — Visual comparisons(toHaveScreenshot)](https://playwright.dev/docs/test-snapshots)
- [Percy docs(BrowserStack)](https://www.browserstack.com/docs/percy)
- [Chromatic docs](https://www.chromatic.com/docs/)
- [Playwright — Electron(experimental)](https://playwright.dev/docs/api/class-electron)
- [pexpect docs](https://pexpect.readthedocs.io/en/stable/overview.html)
- [microsoft/tui-test](https://github.com/microsoft/tui-test)
