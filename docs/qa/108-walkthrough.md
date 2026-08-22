# #108 QA walkthrough —— 分級判準:切票時標快/慢,整批給 client 點頭

- 票:#108「分級判準:切票時標快/慢,整批給 client 點頭」
- branch:`build/108`(HEAD `8b91db1`)
- lane:walkthrough(regression / code-review 由並行池另外兩支跑)
- 測試範圍 oracle:票上「覆蓋驗收項」段的**原句**,只有兩條(AC1、AC4),不是 ticket 的技術 AC 清單
- 可重跑:`bash scripts/qa/108-walkthrough.sh "$(mktemp -d)/qa108"`(exit 非 0 = 有格子不合預期)
- 完整 transcript:[`108-walkthrough.txt`](108-walkthrough.txt)

這片沒有 web UI —— 產品就是散文(`skills/slice-tickets/SKILL.md`)+ 可執行判準
(`skills/build-batch/batch.py` 的 `classify`)+ 守門(`scripts/validate.py` 的
`grade_line_issues`)。所以走查的形狀 = **照著出貨的 SKILL.md 當下一個 agent 實際操作一遍**,
每條驗收項一段可重跑的 transcript:指令 + 真實輸出 + 引用到的散文原文行號。

## 一鍵重開這輪 QA 環境

這個 repo 沒有 server、沒有 DB、沒有前端,環境就是「一份 repo 副本 + `python`」。一行:

```bash
bash scripts/qa/108-walkthrough.sh "$(mktemp -d)/qa108"
```

它自己複製一份 pristine repo 到拋棄式暫存目錄,每個改壞散文的格子都在副本上做,repo 本體
只讀 —— 最後一格(5d)用 `git status --porcelain -- skills scripts/validate.py` 驗這件事。
要重看實錄:`less docs/qa/108-walkthrough.txt`。

---

## AC1 —— 「切票的時候,每張票都標了『快』或『慢』加一句理由,整批一次列給我看,我可以當場改任何一張。」

**做了什麼**:把 `skills/slice-tickets/SKILL.md:35-41` 那段指令**照抄**下來,只把
`<build-batch skill dir>` 換成安裝根目錄,其餘一個字不改,跑一次;再把 client 的 override
餵進去重跑。transcript STEP `==== AC1`(1a–1g)。

**觀察到什麼**

- 照抄跑得起來,exit 0,出來的就是 client 要看的那份(transcript 行 60–68):

  ```
  分級(3 張)— 標「慢」的會演給你看,標「快」的不會:
    慢  #47 … — 覆蓋 1 條驗收項
    快  #48 … — 沒有覆蓋驗收項,不會有你看得到的行為
    慢  #49 … — 動到判斷邏輯或資料寫入,硬規則一律慢

  點頭之後,這幾行逐張貼進票 body 的「覆蓋驗收項」段下方:
    #47  分級:慢 — 覆蓋 1 條驗收項
    #48  分級:快 — 沒有覆蓋驗收項,不會有你看得到的行為
    #49  分級:慢 — 動到判斷邏輯或資料寫入,硬規則一律慢
  ```

- **每張都有分級 + 一句理由**:3 張票,`^  (快|慢)  #\d+.* — .+$` 命中 3 行,沒有一行只有
  快/慢而沒有理由(1c)。
- **整批一次**:一次呼叫、一份清單,標題 `分級(3 張)` 的張數是 `batch.py` 自己數的
  (`format_classify`,`skills/build-batch/batch.py:566`),不是 agent 手排(1d)。同一次
  呼叫同時吐「給 client 看的清單」與「逐張要貼進票的那幾行」,兩份出自同一個
  `classify_tickets` 結果 —— 點頭的對象跟寫進票的東西不可能各說各話。
- **client 可以當場改任何一張**(1e):#47 原本是 `分級:慢 — 覆蓋 1 條驗收項`;client 說改快,
  `override: "快"` 填進去重跑,同一張變成 `分級:快 — 你當場改成「快」` —— **改後的那一行才是
  要寫進票的那個**,而且理由講明是他改的,不是把原理由留著只換一個字。反方向(#48 快→慢)
  也改得動。
- **「改了但沒生效」不會靜靜發生**(1f):`fast` / `快車道` / `Fast` / `"快 "`(尾巴多一個空白)
  / `""` 五種認不得的 override,五種都 exit 1、印
  `override 只能是「快」或「慢」,拿到 … —— 打錯一個字就靜靜照原判寫進票,不猜`,而且**一行分級
  都不印** —— 不會出現一份看起來正常、其實 client 那句被吃掉的清單。
- **分級行格式三邊 byte 對齊**(1g):

  | 來源 | 內容 |
  | --- | --- |
  | `batch.py` 印的(`format_grade_line`) | `'分級:慢 — 覆蓋 2 條驗收項'` |
  | UTF-8 bytes | `e5 88 86 e7 b4 9a 3a e6 85 a2 20 e2 80 94 20 …`(`3a` 半形冒號、`e2 80 94` em dash,前後各一個 `20`) |
  | `skills/slice-tickets/SKILL.md:57` | 同一行,byte 相同 |
  | `scripts/validate.py` `GRADE_LINE_OK_RE` | `match` 為 True;`grade_line_issues(出貨檔)` 回 `[]` |

  快/慢兩個字都套過一次,兩行都合格。

**判定:PASS**

---

## AC4 —— 「動到判斷邏輯、篩選條件、或資料寫入的票,即使沒有可看的行為,也一定被標成『慢』。」

**做了什麼**:先走原句那一格,再把「沒有任何路徑會靜靜落到『快』」當成一把尺,掃過
`classify_one` 的所有分支。transcript STEP `==== AC4`(4a–4e)。

**觀察到什麼**

- **4a 原句那一格**:`judgement=true` 而 `coverage=[]`(沒有可看的行為)→
  `#49  分級:慢 — 動到判斷邏輯或資料寫入,硬規則一律慢`,exit 0。
- **4b 硬規則蓋過 client**:同一張票 client 想改成快 → exit 1,
  `這張動到判斷邏輯或資料寫入,硬規則一律慢 —— 改不成快。驗收清單第 4 條就是它,要改請先改 judgement 旗標`,
  而且**一行分級都不印**。同向的 `override: "慢"` 不擋(結果一樣,沒必要停)。
- **4c 硬規則票 + 認不得的 override**:一樣停在 override 那關。這條的意義在於那條路的結果
  剛好也是慢 —— 吃掉之後畫面跟「client 根本沒改」一模一樣,所以它必須停,而它真的停了。
- **4d 全分支掃描**:9 種 `coverage` × 7 種 `judgement` × 8 種 `override` = **504 條路**
  (transcript 行 383–890)。結果 `快 52 / 慢 110 / 當場停 342`,**靜靜落到「快」而散文沒授權的:0**。
  尺是這樣定的 —— 只有兩條路准落到快:`judgement` 為假**且**(client 當場改成「快」,或
  沒有 override 且沒有覆蓋驗收項)。`judgement` 為真的每一條路,結果都是慢或當場停,一條例外都沒有。
  順帶掃到的邊界都在安全方向:
  - `judgement` 餵字串 `"false"`(truthy)→ 慢,不是快。
  - `coverage` 餵字串而不是 list → 逐字元迭代,`items` 非空 → 慢。
  - `["無障礙:鍵盤走得完整個表單"]` 沒有被 `NO_COVERAGE_RE` 誤殺 → 慢。
  - `["無 — 由後續票的驗收項間接驗證"]` / `-` / `——` 三種破折號寫法都認成「沒有覆蓋」→ 快
    (這是散文授權的那條)。

**判定:PASS**

---

## Finding —— 逐條(含同型全掃)

### F1(nit / known issue)`§4` 的安裝根目錄寫法有寫,但沒有任何守門釘著

`skills/slice-tickets/SKILL.md:32`「由 `build-batch` skill 目錄底下的 `batch.py` 算與印」+
`:35` `python <build-batch skill dir>/batch.py <<'JSON'` —— 散文那半在,寫法也跟既有慣例
一致(`skills/next/SKILL.md:45` 同一個寫法)。但把 `:35` 改成裸 `python batch.py`
(slice-tickets 單獨裝起來的機器上,身邊根本沒有 `batch.py`,這行照抄一定跑不動)之後:

```
+ python …/case/scripts/validate.py            → exit 0  OK validate green
+ python …/case/skills/build-batch/batch.py --self-check → exit 0  OK batch self-check green
```

**兩支守門都綠**(transcript 5c-8)。`classify_command_issue`
(`skills/build-batch/batch.py:758`)只要求那個 bash block 裡有 `batch.py`、有
`"mode": "classify"`、有 `<<` —— 路徑前綴不在它咬的東西裡面。

**同型全掃**(transcript 5c-9):repo 裡 `<… skill dir>/…` 的寫法共 **17 處**,
`build-batch/SKILL.md` 15 處(`<skill dir>/batch.py`)、`slice-tickets/SKILL.md:35` 1 處、
`next/SKILL.md:45` 1 處。**17 處一條都沒被守著** —— `skill_command_issue`
(`skills/build-batch/batch.py:639`)跟 `classify_command_issue` 都只認 `batch.py` 三個字;
`scripts/validate.py` 裡 15 處提到 "skill dir" 的規則守的是 markdown reference 有沒有跑出
skill 目錄(`scripts/validate.py:641`),對 fenced bash block 裡的 placeholder 前綴完全不看。
所以這不是 #108 開出來的洞,是既有形狀,#108 只是又多一處。

影響:這行漂掉不會有任何東西當場紅,而下一個 agent 照抄之後會 `FileNotFoundError`。方向是
安全的(跑不動 → agent 會發現 → §4 的退路是整批判慢),所以列 known issue,不列 blocking。

### F2(known issue)JSON **key** 打錯是靜的,而且靜在不安全的方向

`classify_one` 對 override 的**值**打錯字咬得很緊(「打錯一個字就靜靜照原判寫進票,不猜」),
但同一支檔對 **key** 打錯字完全不設防 —— `classify_tickets`
(`skills/build-batch/batch.py:549-554`)用 `t.get("coverage", [])` /
`t.get("judgement", False)` / `t.get("override")`,少一個字母就當作沒填:

| 餵進去的 JSON | 出來的 | 應該是 |
| --- | --- | --- |
| `{"number":49,"coverage":[],"judgment":true}`(`judgement` 少一個 `e`) | `分級:快 …`,exit 0 | 慢(AC4 那條) |
| `{"number":48,"coverage":[],"overide":"慢"}`(`override` 少一個 `r`) | `分級:快 …`,exit 0 | 慢(client 說的) |
| `{"number":49}`(兩個 key 都沒填) | `分級:快 …`,exit 0 | 至少要吵一聲 |

三種都 exit 0、都落到「快」、畫面跟「這張本來就沒東西可看」一模一樣。第二列正是 AC1 那句
「改了但沒生效」的靜默版:client 明明說了慢,清單上還是快,沒有任何提示。餵 JSON 的是 agent,
跟打 override 值的是同一雙手 —— 值層擋得住、key 層擋不住,是同一個失敗形狀只補了一半。

**同型全掃**:`batch.py` 裡同樣「optional key,預設落到寬鬆方向」的地方還有
`plan_batch` 的 `t.get("blocked_by", [])`(`skills/build-batch/batch.py:96`)—— key 打錯
就變成「這張沒有 blocker」,整批被算成全部能同時開,撞在 merge 那關。那條是既有的(不是 #108
改出來的),形狀一樣,一併記著。對照組:`mode` 漏掉不會靜靜換一個 mode 跑 —— 當場
`KeyError: 'state'`、exit 1(transcript 4e 最後一格)。

判定上這兩條都不推翻 AC:AC1 問的是「client 能不能當場改」(能,而且值層打錯會停),
AC4 問的是「`judgement=true` 會不會被標成慢」(會)。所以列 known issue。

### F3(nit)「快車道」在 repo 裡同時是兩件事

`docs/blueprint.md:50` 的「**快車道**」指的是 `build-batch`(多張票平行跑 build),
`skills/slice-tickets/SKILL.md:50` 的「整批判慢車道」指的是 #108 這條 demo 分級。同一個詞、
兩個意思、同一份 blueprint 的上下兩列(`:49` 講快/慢分級、`:50` 講快車道 = 批次)。讀 blueprint
的人會把「快車道的票」讀成「批次跑的票」。純命名,行為沒問題。

### 沒有抓到的(掃過但乾淨)

- 分級行格式三邊沒有任何一邊漂掉(AC1-1g)。
- `classify_one` 504 條路沒有一條靜靜落到「快」(AC4-4d)。
- §4 的四句「只有散文講得出來」的話(點頭一問、以 client 改的為準、`batch.py` 不在的退路、
  判準天花板)逐句改壞都紅(5c-1 ~ 5c-4,全部由 `batch.py --self-check` 的
  `classify_lines_issue` 咬到,錯誤訊息指名 `slice-tickets SKILL.md` 與那句話的用途)。
- 分級行示範寫歪(`分級:中 —`)→ `validate.py` 紅,訊息
  `分級行格式不對:'分級:中 — 覆蓋 2 條驗收項' — 要寫成「分級:快 — 一句理由」…`(5c-5)。
- 分級行示範整行拿掉 → `validate.py` 紅,訊息
  `呼叫 batch.py 的 classify 卻沒有示範過一行分級行 — …會由 agent 現場發明…`(5c-6)。
- 指令段不再把 JSON 餵進 `batch.py`(`"mode": "nope"`)→ 紅(5c-7,#58 的形狀)。
- pristine 兩支守門都綠(5c-0);repo 本體 `git status --porcelain -- skills scripts/validate.py`
  空的(5d)。

---

## 摘要

| 驗收項(原句) | 判定 |
| --- | --- |
| AC1 每張票標快/慢 + 一句理由,整批一次列出,client 可以當場改任何一張 | **PASS** |
| AC4 動到判斷邏輯/篩選條件/資料寫入的票,即使沒有可看的行為也一定是慢 | **PASS** |

| Finding | 型 | 位置 |
| --- | --- | --- |
| F1 安裝根目錄寫法沒被守門釘住(同型 17 處全沒守) | known issue | `skills/slice-tickets/SKILL.md:35`、`skills/build-batch/batch.py:758` |
| F2 JSON key 打錯靜靜落到「快」(同型:`blocked_by`) | known issue | `skills/build-batch/batch.py:549-554`、`:96` |
| F3 「快車道」一詞兩義 | nit | `docs/blueprint.md:50` vs `skills/slice-tickets/SKILL.md:50` |

**lane verdict:GREEN**(兩條原句都 PASS;三條 finding 全是 known issue / nit,沒有 blocking)
