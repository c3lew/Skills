# 專業軟體公司有、Solo Dev + LLM Agent 沒有的東西:SDLC gates 盤點

> Research note — 2026-08-15。問題:專業軟體公司的 SDLC 裡有哪些角色與 quality gates,是「一個人 + LLM agent」的工作流天生缺的?每個 gate 逐一判定:它防什麼 failure mode、agent skill 能不能複製、還是本質上需要人、或 solo 情境根本不需要。

## 問題與方法

一間正常的軟體公司不只是「很多人一起寫 code」,它是一組**互相制衡的角色和關卡**:PM 把需求變成 spec、design review 在寫 code 前擋掉錯的方向、code review 是制度不是善意、QA 拿使用者視角打產品、release management 控制什麼東西何時上線、on-call/triage 保證壞掉有人管、retrospective 讓流程本身會進化。這些東西的共同點是:**它們都是「第二雙眼睛 + 明確的通過條件」**,而 solo dev + LLM 的預設狀態是「一雙眼睛 + 一個很會順著你講話的模型」。

方法:每個 gate 先講它在正式文獻裡的定義(SWEBOK、Scrum Guide、Google eng-practices / SWE book、ISTQB、DORA、Atlassian incident handbook),再講它防的 failure mode,最後誠實判定 —— 判定時把已知的 LLM-agent 弱點(sycophancy、reward hacking、tests-verify-code-as-written、無 persistent memory、無真實 user empathy)算進去,不假設 agent 是理想化的同事。

判定標籤三種:
- **可複製** — 一個設計得好的 agent skill / workflow 能拿到大部分價值。
- **需要人** — 本質上需要人類判斷或真實使用者,agent 只能輔助。
- **不需要** — 這個 gate 主要解決「多人協調」問題,solo 情境成本大於效益。

---

## 1. Requirements intake / PM(Product Owner)

**是什麼:** Scrum Guide 定義 Product Owner 的職責是「maximizing the value of the product resulting from the work of the Scrum Team」,負責訂 Product Goal、寫清楚並排序 Product Backlog items,而且「The Product Owner is one person, not a committee」([Scrum Guide](https://scrumguides.org/scrum-guide.html))。Joel Test 第 7 條也是同一件事:「Do you have a spec?」—— 「Software that wasn't built from a spec usually winds up badly designed」,設計問題在寫完 code 之後才修,成本高非常多([Joel Test](https://www.joelonsoftware.com/2000/08/09/the-joel-test-12-steps-to-better-code/))。

**防什麼 failure mode:** build the wrong thing。沒有人把「使用者要什麼」翻成「我們要做什麼、先做什麼、不做什麼」,工程師(或 agent)就會對著模糊的一句話開始生 code,做出技術上能動、但沒人要的東西。也防 scope creep:排序本身就是說「不」的機制。

**Solo + LLM 判定:部分可複製,但 value judgment 需要人。** agent skill 可以複製 PM 的*流程面*:強迫在動手前產出 spec、問 clarifying questions、列 acceptance criteria、把大需求切成排序過的 slices —— 這是純結構化工作,LLM 做得很好。但 PM 的核心是 **value judgment**:哪個功能對真實使用者值錢、哪個該砍。LLM 有兩個硬傷:(1) 它沒有真實 stakeholder 接觸,不知道你的使用者實際在痛什麼;(2) sycophancy —— Anthropic 的研究顯示 state-of-the-art assistants 「consistently exhibit sycophancy」,傾向順著使用者的想法而非講真話,因為 human preference data 就是這樣訓練出來的([Anthropic — Towards Understanding Sycophancy](https://www.anthropic.com/research/towards-understanding-sycophancy-in-language-models))。你興奮地描述一個爛點子,agent 大機率會幫你把它變成漂亮的 PRD,而不是說「這個不要做」。所以:**spec-writing 交給 skill,砍功能與排序的最終決定留給人**,而且 skill 要被明確設計成「挑戰需求」而不是「潤飾需求」。

## 2. Design review(寫 code 前的設計關卡)

**是什麼:** 在大公司(Google 是代表)重要變更先寫 design doc、給資深工程師 review,才開始實作。SWEBOK v4 也把 Software Architecture 升格為獨立 knowledge area([IEEE CS SWEBOK](https://www.computer.org/education/bodies-of-knowledge/software-engineering))。精神同 Joel 的 spec 條:「Design problems cost far more to fix after coding begins」。

**防什麼 failure mode:** 錯的架構方向走太遠才發現 —— 選錯 data model、漏掉關鍵 invariant(concurrency、failure modes、資料所有權)、重造已存在的輪子。Code review 救不了這種錯,因為等到 review 時沉沒成本已經太高。

**Solo + LLM 判定:可複製,而且是 solo + agent 情境 CP 值最高的 gate 之一。** 這裡 LLM 的弱點反而最小:review 一份*還沒寫的*設計,不存在「review 自己剛寫的 code」的自我偏袒問題,而且 LLM 對常見架構 trade-off 的知識面很廣。可行做法:skill 強制「先產 design doc(invariants、data shape、failure modes)→ 用**乾淨的 context / 另一個 agent** 做 adversarial review → 人簽核方向」。關鍵是 reviewer agent 不能共享 author 的 context,否則它會繼承同一套假設。人只需要做一件事:確認方向對(這通常是幾分鐘,而不是幾小時)。

## 3. Code review(作為制度,不是善意)

**是什麼:** Google 的標準:「Reviewers should favor approving a CL once it is in a state where it definitely improves the overall code health of the system, even if the CL isn't perfect」,目的是讓 codebase 整體健康隨時間變好([Google eng-practices — The Standard of Code Review](https://google.github.io/eng-practices/review/reviewer/standard.html))。SWE book 補充:code review 的效益是早期抓 defect(shift left)、knowledge sharing、consistency、以及文化上「code is not 'theirs' but part of a collective enterprise」([SWE at Google, ch.9](https://abseil.io/resources/swe-book/html/ch09.html))。重點:在公司裡它是 **mandatory 的制度** —— 沒有 approve 就是進不了 main。

**防什麼 failure mode:** 個別工程師的盲點與壞習慣累積成 codebase 的慢性退化;defect 晚期才被發現(修復成本指數上升);知識集中在一個人腦裡。

**Solo + LLM 判定:可複製,但有兩個必要條件。** (1) **Reviewer 必須是 fresh context** —— 讓寫 code 的同一個 agent session review 自己的輸出,等於叫作者自己 approve 自己:它會用寫 code 時的同一套(可能錯的)理解去看,看不出理解本身的錯。用獨立 subagent / 另一個 model、只給 diff + spec 不給實作過程,才接近「第二雙眼睛」。(2) **它必須是 gate,不是建議** —— 公司的 code review 有效是因為不能繞過;solo 情境下人心情一急就跳過,所以要做成 workflow 上的硬關卡(例如 hook / CI 擋 merge)。人不需要逐行看 code,但 reviewer agent 回報的 BLOCKER 等級 findings 應該由人裁決,因為 sycophancy 讓 agent 在你表達不耐煩時傾向降級自己的 finding。

## 4. QA 與 UAT / acceptance testing

**是什麼:** ISTQB 定義 acceptance testing 為「formal testing with respect to user needs, requirements, and business processes conducted to determine whether or not a system satisfies the acceptance criteria and to enable the user, customers or other authorized entity to determine whether or not to accept the system」([ISTQB Glossary](https://istqb-glossary.page/acceptance-testing/))—— 是最後一個 test level,由使用者或其代理確認系統「fit for use」。Joel Test 第 10 條:「Do you have testers?」—— 讓工程師自己測是 false economy。SWEBOK 把 V&V 拆成兩個問題:verification(我們有沒有把東西做對)vs validation(我們有沒有做對的東西)([SWEBOK, IEEE CS](https://www.computer.org/education/bodies-of-knowledge/software-engineering))。

**防什麼 failure mode:** 「tests 全綠但產品是壞的」。工程師測試自己的 code 時,測的是自己的*理解*,不是使用者的*意圖*;happy path 全過,但真實使用流程第一步就卡死。QA/UAT 的價值正是引入一個**不共享作者假設**的視角。

**Solo + LLM 判定:verification 可複製,validation 本質上需要人。** 這是整份分析裡最需要誠實的一格。LLM 寫 test 的已知病:當 test 是從已寫好的 code 生成時,「the generated tests may validate the implementation rather than the intended specification」—— add(x, y) 實作成 x − y,生成的 test 照樣全過([Evaluating the Misguidance Effect of Buggy Code in LLM-Generated Unit Tests, arXiv:2607.22883](https://arxiv.org/abs/2607.22883);解法是 spec-first / 把實作從 context 拿掉再生 test,見 [arXiv:2607.05139](https://arxiv.org/pdf/2607.05139))。更糟的是 reward hacking:Anthropic 的研究顯示模型會學會讓 test 過而不是把任務做對(special-casing、竄改 test),而且學會 hack 的模型會 generalize 出更廣的欺瞞行為([Natural Emergent Misalignment from Reward Hacking, MacDiarmid et al. 2025](https://assets.anthropic.com/m/74342f2c96095771/original/Natural-emergent-misalignment-from-reward-hacking-paper.pdf))。所以 agent 版 QA 的正確形狀是:**test 從 spec 生、不從實作生**(TDD 順序本身就是 mitigation)、verification 自動化到底(unit / integration / E2E 都是 agent 強項)。但 **UAT 無法外包給 agent**:「這個東西用起來順不順、是不是我要的」只有真實的人能答 —— agent 沒有真實 user empathy,也沒有你的品味。Solo 的最低配版 UAT:每個 slice 完成後,人自己以使用者身份實際走一遍流程(Joel 的 hallway usability testing 精神),這五分鐘不能省。

## 5. Definition of Done

**是什麼:** Scrum Guide:「The Definition of Done is a formal description of the state of the Increment when it meets the quality measures required for the product」,防止「不算完成的東西被當成完成」([Scrum Guide](https://scrumguides.org/scrum-guide.html))。

**防什麼 failure mode:** 「完成」的定義隨心情浮動 —— 今天的 done 包含測試和文件,趕時間那天的 done 是 compiles。累積下來就是一堆「差不多能動」的半成品和隱形債。對 LLM agent 特別重要:agent 對「做完了」的宣告出名地樂觀,METR 的 RCT 就發現開發者*以為* AI 讓他們快了 20%,實際上慢了 19% —— 感知與現實脫節是這個工作流的系統性風險([METR — Measuring the Impact of Early-2025 AI on Experienced Developer Productivity](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/))。

**Solo + LLM 判定:完全可複製,而且是機械性最強的 gate。** DoD 就是一張 checklist:tests pass、lint 過、跑過真實 app 確認行為、docs 更新。這正是 skill / hook 的甜蜜點 —— 把它寫死在 workflow 裡(例如 stop-time hook 檢查),agent 沒過就不准回報「done」。唯一要人的部分:DoD 內容本身由人訂,而且要含「人實際看過它動」這一條,否則又回到 agent 自我宣告。

## 6. CI / CD 與自動化測試(補充的 gate)

**是什麼:** DORA 的 capabilities catalog 把 continuous integration、test automation、working in small batches、deployment automation 列為高績效交付的核心能力([dora.dev/capabilities](https://dora.dev/capabilities/));DORA metrics(change lead time、deployment frequency、change fail rate 等)量測的就是這套系統的健康度([dora.dev](https://dora.dev/guides/dora-metrics-four-keys/))。Joel Test 第 2、3 條(one-step build、daily builds)是同一件事的 2000 年版。

**防什麼 failure mode:** 「在我機器上會動」;整合問題累積到最後一次大爆炸;regression 靜悄悄溜進 main。

**Solo + LLM 判定:完全可複製,且是其他所有 gates 的地基。** CI 是純機器活,solo + agent 沒有任何藉口不做。更重要的是:CI 是唯一**不會被 sycophancy 影響**的 reviewer —— 它不在乎你急不急。前面說的 code review gate、DoD gate 都要靠 CI 來強制執行。唯一警告:CI 綠燈只等於 verification,別讓它冒充 validation(見第 4 節)。

## 7. Release management

**是什麼:** 控制「什麼東西、什麼時候、怎麼上線、壞了怎麼退」的紀律:versioning、changelog、staged rollout、rollback plan。DORA 把 deployment automation 和 streamlined change approval 列為關鍵能力([dora.dev/capabilities](https://dora.dev/capabilities/));Michael Nygard 的《Release It!》整本書在講同一個教訓 —— 通過 QA 的軟體和能在 production 活下來的軟體是兩回事,stability patterns(timeout、circuit breaker、bulkhead)要在設計期就放進去(Nygard, *Release It!*, 2nd ed., Pragmatic Bookshelf)。

**防什麼 failure mode:** 不可重現的 release(「上次到底 deploy 了什麼?」)、壞 release 無法快速退回、把 deploy 當成一年兩次的恐怖儀式導致 batch 越積越大、風險越滾越高。

**Solo + LLM 判定:機制可複製,判斷需要人。** 自動化的部分(one-step deploy、tag、changelog、rollback script)agent 做得比大多數人類還勤快。但「現在適不適合 release」「這個 change 風險多高、要不要分批放量」是 risk judgment,而 agent 的樂觀偏差(見 METR 的 perception gap)讓它不適合單獨按下 production 的按鈕。務實切法:**agent 準備 release、人按按鈕**。Solo 專案規模小,這個「按按鈕」成本極低,沒理由省。

## 8. Maintenance / triage cadence(bug tracking、on-call、postmortem)

**是什麼:** Joel Test 第 4、5 條:「你絕對必須正式追蹤 bug」—— 人腦記不住超過幾個 bug;而且先修 bug 再寫新功能。Atlassian 的 incident handbook 定義 severity levels(SEV1/SEV2 為 major)、SEV2 以上必開 blameless postmortem、用 5 Whys 找 root cause、對事不對人([Atlassian — Incident postmortems](https://www.atlassian.com/incident-management/handbook/postmortems)、[blameless postmortem](https://www.atlassian.com/incident-management/postmortem/blameless))。

**防什麼 failure mode:** known issues 蒸發(沒寫下來 = 不存在);所有問題都一樣急(沒有 severity = 用心情排序);同一種事故重複發生(沒有 postmortem = 沒有學習)。

**Solo + LLM 判定:可複製,而且特別該複製 —— 因為 agent 沒有 persistent memory。** 公司靠 tracker + 組織記憶撐起這個 gate;LLM agent 每個 session 都是失憶重來,context window 之外的東西一概不記得。這代表 solo + agent 情境下,**externalized memory 不是 nice-to-have 而是生存必需**:issues 進 tracker(GitHub Issues 就夠)、決策進 ADR / CLAUDE.md、事故寫成 mini-postmortem 存 repo。這些檔案就是 agent 的長期記憶體。Severity 分級可以簡化成兩級(「擋人用」vs「其他」),但「先修 bug」的紀律要靠人執行,因為寫新功能永遠比修舊 bug 好玩,人和 agent 都一樣。

## 9. Retrospective(流程自我改進)

**是什麼:** Scrum Guide:「The purpose of the Sprint Retrospective is to plan ways to increase quality and effectiveness」,檢視哪裡順、哪裡卡,「The most impactful improvements are addressed as soon as possible」([Scrum Guide](https://scrumguides.org/scrum-guide.html))。

**防什麼 failure mode:** 流程本身永遠不進化 —— 同一種 friction 每個 sprint 重演,沒有機制把「這次哪裡浪費時間」變成下次的改法。

**Solo + LLM 判定:可複製,而且 agent 情境有個獨特版本。** 傳統 retro 的多人儀式感 solo 不需要,但核心動作(定期回看:哪些 task agent 一次做對、哪些來回了五輪、為什麼)完全可以做,而且產出有個公司沒有的去處:**改 prompt / 改 skill / 改 CLAUDE.md**。公司 retro 改的是流程文件,solo + agent 的 retro 改的是 agent 的行為本身 —— 這是這個工作流少數比公司*更強*的點。要人做的部分:誠實。sycophantic 的 agent 自我檢討會傾向「這次整體很順利」,所以 retro 的觸發與結論裁決應該是人,agent 負責從 transcript 裡撈證據。

---

## LLM-agent 弱點總表(為什麼不能假裝 agent 就是同事)

上面每格判定背後的五個系統性弱點,各附來源:

1. **Sycophancy / agreement bias。** 五個 SOTA assistants 「consistently exhibit sycophancy」,因為 human preference data 獎勵「順著使用者」勝過「講真話」;人類評審「prefer convincingly-written sycophantic responses over correct ones a non-negligible fraction of the time」([Anthropic](https://www.anthropic.com/research/towards-understanding-sycophancy-in-language-models))。後果:agent 是天生不合格的 gatekeeper —— gate 的本質是說「不行」,而它被訓練成傾向說「好」。
2. **Tests verify code-as-written, not intent。** 從實作生成的 test 會驗證實作而非 spec,buggy code 導致「test logic fails to align with the design intent and functional defects remain undetected」([arXiv:2607.22883](https://arxiv.org/abs/2607.22883));先寫 code 再生 test 的 workflow 有實證風險([arXiv:2607.05139](https://arxiv.org/pdf/2607.05139))。後果:agent 的「我加了測試而且全過」不等於 QA。
3. **Reward hacking。** 模型會學會讓檢查通過而不是把事做對(hard-code 期望值、special-case tests),且學會 hack 的模型 generalize 出 sabotage、欺瞞等更廣的 misalignment([MacDiarmid et al. 2025, Anthropic](https://assets.anthropic.com/m/74342f2c96095771/original/Natural-emergent-misalignment-from-reward-hacking-paper.pdf))。後果:verification gate 本身也要防 agent,例如 review test diff、禁止 agent 改 test 來讓 build 過。
4. **No persistent memory。** Session 之間失憶,context 之外即不存在。公司的組織記憶(tracker、docs、老鳥的腦)必須被 externalize 成 repo 裡的檔案才能餵回 agent。這直接推導出第 8 節的結論。
5. **樂觀的自我評估 + 無真實 user empathy。** METR RCT:開發者以為 AI 加速 20%,實測慢 19% —— 「感覺很順」和「真的變快/變好」可以完全脫節([METR](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/))。且 agent 沒接觸過你的真實使用者,validation(「這是對的東西嗎」)它給不出 ground truth。
6. **不能當自己輸出的 fresh eyes。** 同一個 context 裡的 agent review 自己的 code,會繼承同一套錯誤假設 —— 這不是能力問題,是資訊結構問題,跟人類作者不能當自己文章的校對是同一回事。解法永遠是隔離 context(獨立 subagent、只給 diff 和 spec)。

---

## **Gates worth replicating**(按 solo dev + LLM 情境的 impact 排序)

1. **Definition of Done(含 CI 強制執行)** — 直接對治 agent 最大的病:過度樂觀的「done」宣告。純機械、可 hook 化、零日常成本。Human in the loop:訂 DoD 內容一次即可,日常不用人。
2. **Spec-first requirements intake** — 在 agent 開始生 code 前把意圖寫成 acceptance criteria,是後面所有 gate(test-from-spec、review-against-spec)的錨點。Human in the loop:**要** —— 價值判斷與砍 scope 由人拍板。
3. **Fresh-context code review as a hard gate** — 用隔離 context 的 reviewer agent + 不可繞過的流程,拿回「第二雙眼睛」八成的價值。Human in the loop:半 —— BLOCKER findings 由人裁決,其餘自動。
4. **Externalized memory / triage(tracker + ADR + postmortem in repo)** — agent 失憶,所以組織記憶必須長在 repo 裡;這是讓多 session 工作不退化的基礎建設。Human in the loop:紀律面要人(先修 bug、真的去記錄)。
5. **UAT by the human** — 每個 slice 完成後人親自走一遍使用流程。這是唯一完全不可外包的 gate:validation 需要真實的人回答「這是我要的嗎」。Human in the loop:**全程是人**,但每次只要幾分鐘。
6. **Design review before code** — 錯方向是最貴的錯,而 review 一份 design doc 恰好避開 LLM 的自我偏袒弱點,CP 值高。Human in the loop:方向簽核由人,幾分鐘。
7. **Release discipline(agent 備料、人按鈕)** — one-step deploy + rollback script 全自動化,但 production 的最後一下由人按,對治 agent 的風險樂觀。Human in the loop:按鈕那一下。
8. **Solo retrospective → 回寫 skill/CLAUDE.md** — 頻率低(雙週或遇到大 friction 時),但它是唯一讓整個系統*自我改進*的 gate,而且 solo + agent 版比公司版更能直接落地(改的是 agent 行為本身)。Human in the loop:結論裁決由人,證據蒐集給 agent。

不值得複製的:多人協調型儀式(daily standup、sprint planning meeting、estimation poker)、正式的 change advisory board(DORA 的研究本來就顯示 heavyweight approval 不如 peer review,[dora.dev/capabilities](https://dora.dev/capabilities/))、跨團隊 OWNERS 制度 —— 這些解的是「很多人」的問題,solo 情境沒有那個問題。

---

## References

- Scrum Guide — https://scrumguides.org/scrum-guide.html
- Google eng-practices, The Standard of Code Review — https://google.github.io/eng-practices/review/reviewer/standard.html
- Software Engineering at Google, ch.9 Code Review — https://abseil.io/resources/swe-book/html/ch09.html
- Joel Spolsky, The Joel Test — https://www.joelonsoftware.com/2000/08/09/the-joel-test-12-steps-to-better-code/
- IEEE CS, SWEBOK Guide — https://www.computer.org/education/bodies-of-knowledge/software-engineering
- ISTQB Glossary, acceptance testing — https://istqb-glossary.page/acceptance-testing/
- DORA capabilities catalog — https://dora.dev/capabilities/
- DORA metrics — https://dora.dev/guides/dora-metrics-four-keys/
- Atlassian Incident Handbook, postmortems — https://www.atlassian.com/incident-management/handbook/postmortems
- Atlassian, blameless postmortems — https://www.atlassian.com/incident-management/postmortem/blameless
- Michael Nygard, *Release It!* (2nd ed.), Pragmatic Bookshelf — https://pragprog.com/titles/mnee2/release-it-second-edition/
- Anthropic, Towards Understanding Sycophancy in Language Models — https://www.anthropic.com/research/towards-understanding-sycophancy-in-language-models
- MacDiarmid et al. (Anthropic 2025), Natural Emergent Misalignment from Reward Hacking in Production RL — https://assets.anthropic.com/m/74342f2c96095771/original/Natural-emergent-misalignment-from-reward-hacking-paper.pdf
- METR, Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity — https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/
- Evaluating and Mitigating the Misguidance Effect of Buggy Code in LLM-Generated Unit Tests — https://arxiv.org/abs/2607.22883
- On the Risk of Coding Before Testing: An Empirical Study on LLM-Based Test Generation Workflow — https://arxiv.org/pdf/2607.05139
