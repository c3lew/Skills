# QA 報告 — #108 分級判準(切票時標快/慢,整批給 client 點頭)

**verdict:blocking 3 條,不放行。**

三支 lane(regression / walkthrough / code-review)在同一則訊息一次發出去;獨立 judge 等
walkthrough 交出證據之後才開。三支 lane 都回綠,**judge 打穿其中兩條原句** —— 這正是 judge
存在的理由:lane 量的是「旗標進去、車道出來對不對」,judge 量的是「client 那句話有沒有兌現」。

## 逐條驗收項(判準 = 票上「覆蓋驗收項」的 client 原句)

| AC | walkthrough | judge | QA 收斂後 | 依據 |
| --- | --- | --- | --- | --- |
| 1. 每張票都標了「快」或「慢」加一句理由,整批一次列給我看,我可以當場改任何一張 | pass | **works-but-wrong** | **fail** | 多張票的批次裡只要有一張的 override 被拒,整批清單一行都不印,而且訊息不說是哪一張(BUG-A) |
| 4. 動到判斷邏輯、篩選條件、或資料寫入的票,即使沒有可看的行為,也一定被標成「慢」 | pass | fail | **pass(在本票範圍內)** | `judgement=true → 慢` 無條件成立、蓋過 override,client 有否決權,天花板明文 — 這三件是本票宣告的範圍。judge 打的是「旗標跟票的實際內容沒綁在一起」,那是票面自己宣告的天花板,不是本輪引入 |

**judge 對 AC4 判 fail 的理由我不全收,但它撿到一個沒人看到的洞**:天花板宣稱「判錯的代價由
降級回路關住」,而降級回路的觸發條件是「標快的票對驗收清單有任何一條沒過」。AC4 講的正是
**沒有可看行為**的票 —— 那種票 `coverage=[]`,一條驗收項都沒有,降級回路永遠不會被觸發。
網子的洞剛好就是 AC4 要守的那一格。這是 spec #106 決策 3 的洞,不是 #108 的實作 bug,但
#108 出貨的散文寫著「關住」是**過度宣稱**,下一個 agent 會照著信 → BUG-C。

## 三線各自的結果

| lane | verdict | 內容 |
| --- | --- | --- |
| regression | **green** | 15 支全綠(`97-mutate` 22/22、`107-mutate` 16/16、`107-walkthrough.sh` 全格)。修前對照:真實母體 16 支 SKILL.md 差額 **0**,fixture 17 格差額 10 筆全部同向收窄、逐筆判讀都是刻意,**無本輪引入的誤判**。第二把尺 `108-wide.py` 多撈 2 筆,逐筆判讀皆為寬尺自己的誤報,反向 0 筆 |
| walkthrough | **green** | AC1 / AC4 皆 pass;54 格 PASS + 3 格 KNOWN;守門改壞→紅→還原全過;`classify_one` 504 條路徑掃描未授權的「快」= 0 |
| code-review | **green** | 0 blocker,2 should-fix(S1 / S2),7 nit |
| judge(獨立,排在 walkthrough 之後) | **red** | AC1 works-but-wrong、AC4 fail |

judge 與 code-review 各自獨立撞到同一件事兩次(缺欄位靜靜判快、硬規則錯誤訊息把繞道寫出來),
兩把尺對上 → 真的。

## Blocking

### BUG-A — 一張被拒,整批清單消失,而且不說是哪一張(AC1 fail)

`skills/build-batch/batch.py:549-554`。`classify_tickets` 是 list comprehension,任一張
`raise SystemExit` 整批就死。實測三張票(#47 慢 / #48 快 / #49 硬規則),client 說「#49 改快」:

```
exit=1
stderr: 這張動到判斷邏輯或資料寫入,硬規則一律慢 —— 改不成快。驗收清單第 4 條就是它,要改請先改 judgement 旗標
stdout: (空)
```

三件事同時發生,前兩件打在原句上:

1. **整批 3 行分級一行都不印** —— 原句是「整批一次列給我看」。client 同一輪如果還改了 #47,那個改動也一起消失。
2. **訊息裡只有「這張」,沒有票號** —— 三張票的批次,client 手上沒有可以動作的資訊。
3. 這張改不了本身是 AC4 要求的,不算硬傷。

修法方向:整批先算完,被拒的那張在清單上標出來,清單照印,最後才非 0 退出並指名 `#49`。

### BUG-B — 漏餵 / 打錯 key 的票靜靜判「快」(不安全方向)

`skills/build-batch/batch.py:549-554` 的 `t.get("coverage", [])` / `t.get("judgement", False)`。
code-review 與 walkthrough 各自獨立撞到:

| 輸入 | 結果 |
| --- | --- |
| `{"number":50}`(欄位漏餵) | **快** — 理由印「沒有覆蓋驗收項,不會有你看得到的行為」 |
| `"coverage": ""` | **快** |
| `"judgment"`(少一個 e) | **快** |
| `"overide"`(少一個 r) | **快**,而且是 AC1「改了但沒生效」的靜默版:client 說慢、清單還是快 |

值層擋得住(`override` 打錯字會當場停),key 層擋不住 —— 同一個失敗形狀只補了一半。方向是
不安全那邊(這張票不會被 demo),而且理由那句話跟事實相反。同一支檔的既有慣例正好相反:
`plan_batch`(`batch.py:90-96`)對必填欄位用硬索引 `t["number"]`,漏餵當場炸。

同型:`plan_batch` 的 `t.get("blocked_by", [])`(`:96`)—— key 打錯 = 「這張沒有 blocker」,
整批被算成全能同時開。併本票一起修。

### BUG-C — 硬規則的處置只活在 code 裡,而天花板是過度宣稱

三處同根,`skills/slice-tickets/SKILL.md:47-62` + `batch.py:538-540`:

1. **SKILL.md §4 從頭到尾沒有一句話說「硬規則蓋過 client 的 override」**。§4 只講 `judgement` 蓋過 `coverage`(`:47`),對 client 的問句是無條件的「有要改的嗎?」(`:52`)。agent 撞到那個 stop 時,文件裡沒有任何指示告訴它該怎麼辦 —— 這正是 `CLASSIFY_LINES` 想關住的那種「只有散文講得出來」的洞,而這句沒被關進去。
2. **錯誤訊息自己把繞道寫出來**:「要改請先改 `judgement` 旗標」(`batch.py:540`)。agent 被 client 頂著,照字面把 `true` 改成 `false` 重跑 → 判快、一路綠、沒有任何東西會紅。硬規則是這條線唯一的防護,而它的錯誤訊息指的那條路就是唯一的拆法。
3. **「判錯的代價由降級回路關住」對 `coverage=[]` 的票不成立**(`SKILL.md:62`)。降級回路的觸發條件是「標快的票對驗收清單有任何一條沒過」,而 AC4 講的那種票一條驗收項都沒有。散文寫「關住」,下一個 agent 會照著信。

修法方向:錯誤訊息拿掉指路、改成「這張要改快得回去改票的內容」;§4 補一句硬規則蓋過 client
的處置並進 `CLASSIFY_LINES`;天花板那句改成講得出真話的版本(關得住的是有驗收項的那半)。

## Known issues(帶著 demo,處置由 client 在 demo 收尾整批確認)

| # | 內容 | 建議觸發點 |
| --- | --- | --- |
| K1 | **降級回路對「沒有驗收項的快票」沒有觸發條件** — spec #106 決策 3 的結構洞,不是 #108 引入。已在 #106 留 comment | 降級回路那張票 |
| K2 | `GRADE_LINE_RE` 有四個繞過:bullet 底下、4 空白縮排、blockquote、表格格子、冒號前空白 — 只要文件裡另有一行合格的分級行,壞的那行完全無聲。現況出貨檔不受影響 | 下一批動守門的票 |
| K3 | `CLASSIFY_CALL_RE` 是空白敏感的字面比對(`"mode": "classify"`),`{"mode":"classify"}` 整條看不到。第二支呼叫 classify 的 skill 會裸奔 | 第二支 skill 呼叫 classify 時 |
| K4 | `97-mutate.py` 漏一格:`GRADE_LINE_OK_RE` 的「破折號前後各一空白」沒有 knob(assert 在,實測放寬會轉紅,只是表上沒這格) | 併 BUG-B 的 knob 一起補 |
| K5 | 安裝根目錄寫法(`<… skill dir>/…`)全 repo 17 處**一處都沒被守門釘住**;改成裸 `python batch.py` 兩支守門都綠。方向安全(跑不動會被發現) | 既有形狀,下次動守門時 |
| K6 | `slice-tickets/SKILL.md:3` frontmatter 列的三件事跟 body 的三個 delta 對不上(blocking 邊對帳不在 description 裡)— #57 就有的 drift | 併 BUG-C 的散文修 |
| K7 | `SKILL.md:16`「先做完 §3–§6 再發佈」把發佈自己包進去(§6 標題就是「然後發佈」);`:52` 同一句話講兩次 | 同上 |
| K8 | `docs/specs/slice-tickets.md:7,15` 仍寫「補一個 delta」,#57 與本輪都沒進去 | 開 tech-debt |
| K9 | **下游還沒有消費端** — `client-demo` / `build-batch` 的 SKILL.md 一行都沒提分級行或快/慢車道。分級行寫進票、沒人讀 | 後續票補閉環 |
| K10 | `docs/blueprint.md:50` 的「快車道」= batch 名額,`slice-tickets/SKILL.md:50` 的「慢車道」= demo 分級,一詞兩義 | 下次動 blueprint |

## 未涵蓋範圍

- **從「一張真的票」到 `judgement` 旗標那一段,零證據**。整份 transcript 都是手工餵好的 JSON,沒有一格是「拿一張真票、由 agent 讀 diff 判旗標」。**接受不蓋**:票面已宣告這條判不準,而且它的正確性沒有機械判準可量 —— 要蓋就得先有降級回路。
- **Tauri 原生殼 / web UI**:本 repo 不適用。

## demo 實錄清單

| 驗收項 | 實錄 |
| --- | --- |
| AC1 / AC4 逐條 | `docs/qa/108-walkthrough.txt`(1331 行,`set -x`) |
| 逐條判讀 | `docs/qa/108-walkthrough.md` |
| regression 全綠 + 修前對照 + 第二把尺 | `docs/qa/108-regression.txt`(3302 行)、`docs/qa/108-prevdiff.txt`、`docs/qa/108-wide.txt` |

## 一鍵重開

```bash
bash scripts/qa/108-walkthrough.sh "$(mktemp -d)/qa108"
```
