# Context Window「Smart Zone」研究筆記

> 調查日期:2026-08-15。問題:「LLM/agent 在 context 用量落在某個 band 內表現最好、window 越滿越退化」這個說法,有多少實證?band 在哪?agent harness 該怎麼設計才能待在 zone 裡?

## TL;DR

- **退化是真的,而且有大量獨立實證**:RULER(NVIDIA)、NoLiMa、Lost in the Middle、LongBench v2、Chroma 的 Context Rot report 全部指向同一件事 — model 的 effective context 遠小於 advertised context,而且輸入越長、任務越不像單純 retrieval,退化越快。
- **數字上最狠的是 NoLiMa**:13 個號稱支援 128K+ 的 model,**在 32K 就有 11 個掉到 short-context baseline 的 50% 以下**;GPT-4o 從 99.3% 掉到 69.7%。RULER 則是 17 個號稱 32K+ 的 model **只有一半在 32K 還撐得住**。
- **「zone 的邊界」沒有一個公認的數字**。學術 benchmark 給的是「多長開始爆」(model-dependent,常見在 8K–32K 就開始有感);practitioner guidance 給的是「window 用到幾 %」— HumanLayer 的 ACE-FCA 建議 **40–60% utilization**,但那是工程經驗法則,不是 controlled measurement。Anthropic 官方 Claude Code docs 只說「performance degrades as context fills」,沒給百分比。
- **對策已經收斂成固定幾招**:subagent context isolation、compaction/handoff、just-in-time retrieval、把 durable state 寫到檔案、把 instruction 檔案(CLAUDE.md / SKILL.md)壓小。每一招都有 first-party 出處,細節在第二節。

---

## 1. 退化的實證與 band 位置

### 1.1 Effective length 遠小於 advertised length

- **RULER**([arXiv 2404.06654](https://arxiv.org/abs/2404.06654), NVIDIA, COLM 2024):測 17 個 long-context model、13 個 task(不只 needle-in-a-haystack,還有 multi-hop tracing、aggregation)。Abstract 原話:*"While these models all claim context sizes of 32K tokens or greater, only half of them can maintain satisfactory performance at the length of 32K"*,而且 *"almost all models exhibit large performance drops as the context length increases"*。Yi-34B 號稱 200K,實測遠低於此。重點:**NIAH 幾乎滿分不代表 long-context 能力** — 一換成需要理解的 task 就露餡。
- **NoLiMa**([arXiv 2502.05167](https://arxiv.org/abs/2502.05167)):把 needle 和 question 之間的字面重疊(lexical match)拿掉,強迫 model 靠 latent association。結果:13 個號稱 128K+ 的 model,**32K 時 11 個掉到 short-context baseline 的 50% 以下**;GPT-4o 從 baseline 99.3% 掉到 69.7%。CoT / reasoning model 也救不回來。這是「band 下緣可能比你想的低很多」的最強證據 — **當任務需要語意推理而非字面比對,32K 就已經出 zone 了**。
- **LongBench v2**([arXiv 2412.15204](https://arxiv.org/abs/2412.15204)):503 題、8K–2M words 的真實長文任務。Human experts(15 分鐘限時)只拿 53.7%;最強 model direct answer 只有 50.1%,o1-preview 靠長 reasoning 才到 57.7%。意義:長 context 的「深度理解」對 model 和人都難,advertised window ≠ 可用的理解力。

### 1.2 位置效應與 input 長度本身就是變數

- **Lost in the Middle**(Liu et al., [arXiv 2307.03172](https://arxiv.org/abs/2307.03172)):multi-document QA 和 key-value retrieval 都呈 **U-shaped curve** — *"performance is often highest when relevant information occurs at the beginning or end of the input context, and significantly degrades when models must access relevant information in the middle of long contexts, even for explicitly long-context models."* 所以不只「多長」,「放哪裡」也影響 — 塞在 window 中段的資訊最容易被漏掉。
- **Context Rot**(Chroma, [research.trychroma.com/context-rot](https://research.trychroma.com/context-rot)):測 18 個 model(Claude Opus 4 / Sonnet 4 / 3.7 / 3.5、o3、GPT-4.1 系列、GPT-4o、Gemini 2.5 Pro/Flash、Qwen3 等)。關鍵發現:
  - **input length 本身就會讓表現下滑**,即使 task 難度不變(repeated words 這種 trivial task 也隨長度掉)。
  - needle 和 question 的 **semantic similarity 越低,退化越快**(similarity 範圍 0.445–0.829 的實驗設計)。
  - **一個 distractor 就會拉低 accuracy**,而且不同 distractor 傷害不均;Claude 系列 hallucination rate 最低、GPT 系列最高。
  - **LongMemEval**:同一題,focused prompt(~300 tokens)vs full prompt(~113k tokens),focused 顯著贏,*"even with full reasoning capabilities on the latest models"* — 連答案明明在 context 裡,Opus 4 都會回 *"I cannot determine... because the specific dates are not provided"*。
- **Anthropic engineering blog**([Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)):把機制講白 — *"LLMs have an 'attention budget' that they draw on when parsing large volumes of context"*;transformer 的 n² pairwise attention 使 *"as its context length increases, a model's ability to capture these pairwise relationships gets stretched thin"*。這是 vendor 對 context rot 的正式承認,但**沒有給具體 threshold**。
- **Claude Code 官方 docs**([Best practices](https://code.claude.com/docs/en/best-practices)):直接寫 *"Most best practices are based on one constraint: Claude's context window fills up fast, and performance degrades as it fills"*、*"The context window is the most important resource to manage"*。一樣沒給百分比。

### 1.3 那 band 到底在哪?誠實版結論

分三層講,信任度由高到低:

1. **Measured(benchmark 實測)**:退化是連續的、從很早就開始(Chroma 顯示連 trivial task 都隨長度單調下滑),但「斷崖」位置 model-dependent。對需要推理的任務,**8K–32K 就可能明顯退化**(NoLiMa);對單純 retrieval,大部分 frontier model 撐得比較久。沒有任何 paper 說「x% of window 是安全線」— 學術結果是以 **絕對 token 長度** 呈現的,不是 window 百分比。
2. **Vendor guidance**:Anthropic 說「會退化、要管理」,並把 auto-compact 設在接近 window 上限(例如 Sonnet 5 的 1M window 預設 ~967K 才 compact,[Model config docs](https://code.claude.com/docs/en/model-config))— 注意這是「避免撞牆」的 last-resort 門檻,**不是**「這之前都沒事」的品質保證。
3. **Practitioner folklore(有用但非實測)**:HumanLayer 的 ACE-FCA([ace-fca.md](https://github.com/humanlayer/advanced-context-engineering-for-coding-agents/blob/main/ace-fca.md))提出 **40–60% utilization** 的目標區間(Frequent Intentional Compaction),理由是留 headroom 給 tool output 和 reasoning。這是工程經驗法則,沒有 controlled eval 支持那兩個數字本身。「~100K tokens per ticket」這類 sizing 規則同樣屬於 harness convention / folklore — 找不到 first-party 實驗出處,但它跟 measured evidence 方向一致(200K window 的 model,100K ticket ≈ 50% utilization,恰好落在 ACE-FCA 的區間,也低於 NoLiMa 顯示大退化的區域上緣)。

**一句話**:「smart zone」的存在有扎實實證;zone 的精確邊界沒有。合理的工程近似是「**以 200K window 而言,單一 session 的工作記憶盡量控制在幾十 K 到 ~100K,越需要推理的任務越往低的那端靠**」。

---

## 2. 讓 agent session 待在 zone 裡的實務作法

以下每招都有 first-party 出處。

### 2.1 Subagent fan-out / context isolation

- Anthropic [multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system):*"Subagents facilitate compression by operating in parallel with their own context windows... before condensing the most important tokens for the lead research agent."* 成效:Opus 4 lead + Sonnet 4 subagents **贏過 single-agent Opus 4 90.2%**(internal research eval);token usage 解釋了 80% 的 performance variance。代價:multi-agent 用掉 **~15x** chat 的 token(agent 單體約 4x)。
- Claude Code docs([Best practices](https://code.claude.com/docs/en/best-practices)):*"Subagents run in separate context windows and report back summaries"* — 官方明講 research/大量讀檔要丟給 subagent,main context 留給 implementation。
- **反方意見要記**:Cognition 的 [Don't Build Multi-Agents](https://cognition.ai/blog/dont-build-multi-agents) — *"Share context, and share full agent traces"*、*"Actions carry implicit decisions, and conflicting decisions carry bad results"*。平行 subagent 各自做隱含決策會互相打架。調和方式:**read-only 的調查/搜尋 fan-out 很安全(沒有 write 衝突),要「寫 code 的決策」盡量留在單一線程**,這也是 Claude Code 實際的預設形狀(subagent 主要拿來 investigate/review,不是平行寫)。

### 2.2 Compaction / handoff

- Anthropic context engineering blog:compaction = *"taking a conversation nearing the context window limit, summarizing its contents, and reinitiating a new context window with the summary"*。
- Claude Code:auto-compact 預設接近 window 上限才觸發(Sonnet 5 ~967K/1M;可用 `/autocompact 500k`、`CLAUDE_CODE_AUTO_COMPACT_WINDOW` 調早,接受 100K–1M,[Model config](https://code.claude.com/docs/en/model-config))。docs 建議在大任務開始前主動 `/compact <instructions>` 聚焦、不相關任務之間用 `/clear`:*"A clean session with a better prompt almost always outperforms a long session with accumulated corrections."*
- Anthropic API 層還有 [context editing](https://platform.claude.com/docs/en/build-with-claude/context-editing):`clear_tool_uses` 預設 **100K input tokens 觸發、保留最近 3 個 tool use**,搭配 memory tool 讓 model 在被清掉前把重點寫進 memory file。
- Cognition 的進階版:用一個 **dedicated compression model** 持續摘要 action history,兼顧長任務和 context 一致性。

### 2.3 Just-in-time context loading(agentic search > pre-loaded RAG)

- Anthropic context engineering blog:*"agents built with the 'just-in-time' approach maintain lightweight identifiers... and use these references to dynamically load data into context at runtime"*;trade-off 是 runtime exploration 較慢,建議 hybrid。
- Claude Code 本身就是這樣設計的:MCP tool schema 預設 deferred、用到才載;skill 只載 one-line description,*"Full skill content loads only when Claude actually uses one"*([context-window docs](https://code.claude.com/docs/en/context-window))。

### 2.4 Note-taking / memory outside the window

- Anthropic context engineering blog:structured note-taking — *"the agent regularly writes notes persisted to memory outside of the context window"*;multi-agent 文也講 agent *"retrieve stored context like the research plan from their memory rather than losing previous work when reaching the context limit."*
- Manus([Context Engineering for AI Agents](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus)):*"treat the file system as the ultimate context: unlimited in size, persistent by nature"*;壓縮要**可還原** — *"the content of a web page can be dropped from the context as long as the URL is preserved"*(留 URL / file path,丟內容)。另外兩個 Manus 招:**todo.md recitation**(不斷改寫 todo,把 global plan 推進 recent attention span,直接對抗 lost-in-the-middle)、**保留錯誤在 context 裡**(*"leave the wrong turns in the context"*,model 看到失敗才不會重犯)。
- Manus 也提醒成本面:agent 的 input:output ≈ **100:1**,KV-cache hit rate 是 production agent 最重要的 metric(cached $0.30/MTok vs uncached $3/MTok,10x)— 所以 context 要 **append-only、prefix 穩定**,亂改歷史會炸 cache。

### 2.5 Session / ticket sizing

- HumanLayer ACE-FCA:整個 workflow 圍繞 **40–60% utilization** 設計(research → plan → implement,每 phase 產出壓縮過的 artifact 再開新 context)。
- 「一張 ticket ≈ 100K tokens、一個 session 做完一張」是社群 harness 的 sizing convention(folklore,無實測出處),但與上面所有 evidence 方向一致:**工作切到單 session 能在 window 半滿以內做完,永遠不要指望 auto-compact 救你** — auto-compact 觸發時你早就深入退化區了。
- Claude Code docs 對應建議:大 feature 先讓 Claude interview 你寫成 SPEC.md,然後 *"start a fresh session to execute it"* — spec 是 handoff artifact,新 session 是 clean context。

---

## 3. Claude-Code skill system 該內建的具體規則

從上面 evidence 直接推出來的規則,附依據:

1. **SKILL.md 保持小,references 懶載入。** 依據:skill listing 常駐 context 只有 one-liner、全文用到才載(Claude Code context-window docs);CLAUDE.md 同理 — *"Bloated CLAUDE.md files cause Claude to ignore your actual instructions!"*(Best practices)。規則:SKILL.md 本體只放觸發條件 + 核心流程(目標 <100 行),細節拆到 `references/*.md` 讓 model 需要時才 Read — 這就是 just-in-time loading 在 skill 層的落地。
2. **Ticket sizing:一張票一個 session 能在 window 半滿內做完。** 依據:NoLiMa/RULER 顯示推理型任務幾十 K 就開始退化;ACE-FCA 的 40–60% 區間;auto-compact 是 last resort 不是品質工具。規則:planning skill 切 ticket 時,估「這張票需要讀+寫多少 token」,超過就再切;寧可多一次 handoff,不要一次撐滿。~100K/ticket(對 200K window)是可用的 default,標明它是 convention 不是實測值。
3. **Bulk reading 一律丟 subagent。** 依據:*"Subagents run in separate context windows and report back summaries"*(Best practices);multi-agent blog 的 compression 論述。規則:codebase 調查、多檔 review、web research 都用 Explore/general-purpose subagent,main session 只收 conclusion。但**寫入決策不分散** — 遵守 Cognition 的兩原則,implementation 留在單線程。
4. **Durable state 寫檔案,不留在對話裡。** 依據:Anthropic structured note-taking、Manus file-system-as-memory。規則:plan、進度、決策記錄寫到 `docs/` 或 ticket 檔;壓縮要可還原(留 path/URL 丟內容);長任務維護一個會被反覆改寫的 checklist 檔(recitation,對抗 lost-in-the-middle)。
5. **Handoff 優於 compact,compact 優於硬撐。** 依據:LongMemEval focused-vs-full(300 tokens 贏 113K);Best practices 的 "clean session with a better prompt almost always outperforms a long session"。規則:phase 結束就產 handoff artifact(spec/plan/state file)開新 session;真的要續跑才 `/compact <focus>`;把 `/autocompact` 調低於預設(預設幾乎是撞牆才觸發)。
6. **關鍵 instruction 放頭尾,不放中間。** 依據:Lost in the Middle 的 U-shape。規則:skill 的 hard rules 放 SKILL.md 開頭;長 prompt 的 acceptance criteria 放最後重述一次。
7. **Context append-only、prefix 穩定。** 依據:Manus KV-cache(10x 成本差)。規則:skill 不要在 session 中途動態改寫 system-level 內容;動態資訊放對話尾端。
8. **不確定性要誠實標註**:40–60%、100K/ticket 這些數字寫進 skill 時標 "engineering convention",別包裝成 measured threshold — 不同 model、不同任務型態,zone 邊界會移動。

---

## 參考來源

**Anthropic first-party**
- Effective context engineering for AI agents — https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- How we built our multi-agent research system — https://www.anthropic.com/engineering/multi-agent-research-system
- Claude Code Best practices — https://code.claude.com/docs/en/best-practices
- Claude Code: Explore the context window — https://code.claude.com/docs/en/context-window
- Claude Code: Model configuration(auto-compact thresholds)— https://code.claude.com/docs/en/model-config
- Context editing(API, defaults: trigger 100K / keep 3)— https://platform.claude.com/docs/en/build-with-claude/context-editing

**Published evals(measured)**
- RULER: What's the Real Context Size of Your Long-Context Language Models?(NVIDIA)— https://arxiv.org/abs/2404.06654
- NoLiMa: Long-Context Evaluation Beyond Literal Matching — https://arxiv.org/abs/2502.05167
- Lost in the Middle: How Language Models Use Long Contexts(Liu et al.)— https://arxiv.org/abs/2307.03172
- LongBench v2 — https://arxiv.org/abs/2412.15204
- Context Rot(Chroma technical report)— https://research.trychroma.com/context-rot

**Agent-harness design(practitioner)**
- Don't Build Multi-Agents(Cognition)— https://cognition.ai/blog/dont-build-multi-agents
- Context Engineering for AI Agents: Lessons from Building Manus — https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus
- Advanced Context Engineering for Coding Agents(HumanLayer, ACE-FCA, 40–60% target)— https://github.com/humanlayer/advanced-context-engineering-for-coding-agents/blob/main/ace-fca.md
