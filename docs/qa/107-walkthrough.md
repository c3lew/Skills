# #107 QA walkthrough —— 票內平行化

- 票:#107「票內平行化:regression / 走查 / code review 同時跑,judge 排在走查後」
- branch:`build/107`(HEAD `97bf00d`),本輪 diff = `git diff 84ab07d..HEAD -- skills/`
- lane:walkthrough(regression / code-review 由並行池另外兩支跑)
- 可重跑:`bash scripts/qa/107-walkthrough.sh "$(mktemp -d)/qa107"`(exit 非 0 = 有格子不合預期)
- 完整 transcript:[`107-walkthrough.txt`](107-walkthrough.txt)

這片的交付物是散文(SKILL.md)+ 守門(`scripts/validate.py`),沒有 web UI,所以
「a11y snapshot」的等價物 = 每條 AC 一段可重跑的實測 transcript:指令 + 真實輸出 +
引用到的散文原文行號。

---

## AC1 —— 跑 `/qa` 時,regression suite、實測 walkthrough、code review 三者同時開始,不互相等待

**做了什麼**:讀出貨的 `skills/qa/SKILL.md` §2,判「下一個 agent 照著做會不會真的並行」;
再讀 `skills/build/SKILL.md` §2 的 code-review 並行位置,對兩份文件的母體宣告。
transcript STEP `==== AC1`(1a–1e)。

**觀察到什麼**

- lane 宣告在表格第一欄,剛好三支(`skills/qa/SKILL.md:31-33`):

  ```
  | **regression** | 跑既有 regression suite | 紅的每一條記為 blocking |
  | **walkthrough** | 照驗收原句實測切片 | 每條驗收項一份 a11y snapshot + demo 實錄 |
  | **code-review** | 對本票的最終 diff 跑 `/code-review` | findings 清單與處置 |
  ```

- 「同時開始」寫成可執行動作,不是宣告(`skills/qa/SKILL.md:35-36`):
  「**同時開始 = 三個 sub-agent 在同一則訊息裡一次發出去**。一支一支發,讀起來每支都是
  sub-agent,實際還是排隊,而且報告長得跟真的並行一模一樣。」
- 序列語掃描(`先跑` / `跑完才` / `再走`)在 `skills/qa/SKILL.md` 命中 0 條 —— 原本的
  `## 2. Regression 先跑` 與「跑完 regression 再走 walkthrough」已經整段改掉。
- 收斂條件明寫(`skills/qa/SKILL.md:42`):「三支都回來才收斂成一份報告 —— 有一支先紅也照樣
  等完另外兩支」。
- 票面矛盾已解且兩份文件不打架:`/qa` 這支吃「已經推上去的最終 diff」
  (`skills/qa/SKILL.md:70-71`),`/build` 那支吃「commit 前的工作區」
  (`skills/build/SKILL.md:24-25`),兩邊互相指名對方的母體,沒有互相取代。
- `skills/build/SKILL.md:16-18`:code-review 與 regression suite「兩支在同一則訊息裡一次
  發出去,兩邊都回來才進 commit」,形狀與 `/qa` 那三支一致。

**判定:PASS**

---

## AC2 —— 獨立 judge 仍然排在 walkthrough 完成之後才開始,且 SKILL.md 明文寫出這條排序約束與它的理由

### (a) 散文面

`skills/qa/SKILL.md:73-79`:

```
## 3. 獨立 judge(排在 walkthrough 之後,不進並行池)

**排序約束**:獨立 judge 排在 walkthrough 之後才開,不進 §2 的並行池。

理由:judge 的證據來源就是 walkthrough 產出的 a11y snapshot。提早開,它拿到空證據,然後把每一條
都判 pass — 而「證據是空的所以全過」跟「真的全過」在報告上長得一模一樣:沒有紅字、沒有
例外、每條 pass。這是本 skill 唯一一條看報告驗不出來的約束,所以寫在這裡當硬約束。
```

排序約束 + 理由都在,理由講的是失敗形狀(空證據全判 pass、報告長得跟真的一樣),不是
「因為要照順序」。

### (b) 可執行面 —— 六格 mutation

拿**真的** `skills/qa/SKILL.md` 複製到暫存 repo 副本上改壞,每格跑一次
`python scripts/validate.py`(副本裡那支),記 exit code 與錯誤原文。

| # | 破壞 | 預期 | 實際 exit | 錯誤原文 | 判定 |
| --- | --- | --- | --- | --- | --- |
| 2b-1 | 把 `\| **judge** \| 判定 \|` 插進 lane 表 | 紅 | 1 | `並行池 lanes are ['regression', 'walkthrough', 'code-review', 'judge'] — must be exactly [...]; a judge lane in that pool reads an empty a11y snapshot and passes every criterion, which looks identical to a real pass` | PASS |
| 2b-2 | 刪掉 `\| **code-review** …` 那列 | 紅 | 1 | `並行池 lanes are ['regression', 'walkthrough'] — must be exactly [...]` | PASS |
| 2b-3 | lane 表三列上下順序對調 | 綠 | 0 | (無) | PASS |
| 2b-4 | 「排在 walkthrough 之後」→「之前」 | 紅 | 1 | `never states that the 獨立 judge runs walkthrough…之後 — the ordering constraint is load-bearing, so it is written, not inferred` | PASS |
| 2b-5 | 整段 `## 2. 並行池…` 拿掉 | 紅 | 1 | `並行池 lanes are [] — must be exactly [...]` | PASS |
| 2b-6 | 原封不動 | 綠 | 0 | (無) | PASS |

六格都符合預期,錯誤全部指名 `skills/qa/SKILL.md`。

**觀察(不影響 AC2 判定,列為 known issue 候選)**:2b-5 把 `## 2. 並行池` 整段拿掉之後,守門
給的是 `並行池 lanes are []`,不是 `judge_ordering_issues` 裡那句 `runs an 獨立 judge but
declares no 並行池 section`。原因是 `POOL_SECTION_RE` 改去比對到 §3 的標題
`## 3. 獨立 judge(排在 walkthrough 之後,不進並行池)` —— 那行標題也含「並行池」三個字。
結果照樣是紅的(AC2 要的那件事成立),但錯誤訊息會把「整段不見了」誤報成「表是空的」,
下一個人照訊息去修會找錯地方。`validate.py` 那條 `no 並行池 section` 分支對出貨的
`skills/qa/SKILL.md` 實際上到不了。

---

## AC3 —— 並行之後 regression suite 全綠,結果與序列跑時一致(沒有因為並行而漏跑或搶資源失敗)

**做了什麼**:regression suite 本身由 regression lane 跑,這裡只驗「並行有沒有讓 lane 互相
搶資源」這一面 —— 散文面 + 一次實測。transcript STEP `==== AC3`。

**觀察到什麼**

- 散文面(`skills/qa/SKILL.md:38-40`):
  「**lane 之間不共用資源**:各自的 port、暫存目錄、QA artifacts 子目錄分開;真的共用
  (同一個 dev server、同一份 fixture DB)就把撞到的那兩支序列化,寧可慢也不要搶。
  搶資源的失敗會長得像 flaky,查起來比省下的時間貴。」
  —— 資源清單(port / 暫存目錄 / artifacts)與撞到的處置(序列化)都寫下來了。
- 實測:同時起兩個 `python scripts/validate.py --self-check`(它們各自用 `tempfile`),
  兩支都 exit 0,輸出各自完整,沒有互相干擾。

**判定:PASS**(範圍限「不搶資源」這一面;regression suite 全綠與序列一致由 regression lane 認定)

---

## AC4 —— 任一支並行 sub-agent 失敗時,QA 報告要如實列出是哪一支失敗,不因為其他支綠就報綠

**做了什麼**:散文面 + 一次演練。transcript STEP `==== AC4`(4a–4c)。

**觀察到什麼**

- 散文面(`skills/qa/SKILL.md:44-46`):
  「**任一支失敗要指名道姓**:報告寫明是哪一支 lane 失敗、失敗內容是什麼,其他兩支綠不能
  蓋過它 —— 三支的判定是 AND,不是多數決。lane 自己爆掉(sub-agent 掛了、環境起不來)跟
  lane 判 fail 同級:照樣寫進報告當紅,不准當成「沒跑到」略過。」
  報告格式那一端也咬住(`skills/qa/SKILL.md:96`):QA 報告要有「**三線各自的結果**
  (哪一支綠、哪一支紅、紅在哪)」。
- 演練:在暫存 repo 副本上把排序句改壞(`walkthrough 之後` → `之前`),三支 lane 同時發出去:
  - `regression`(副本的 `validate.py`)→ exit 1,輸出
    `FAIL skills/qa/SKILL.md: never states that the 獨立 judge runs walkthrough…之後 …`
  - `walkthrough`(`107-mutate.py --list`)→ exit 0
  - `codereview`(`git diff --stat 84ab07d..HEAD -- skills/`)→ exit 0
  - 收斂:`紅的 lane: regression`,`彙總 exit(AND):1`

  兩支綠沒有把紅蓋掉,transcript 裡看得出是哪一支紅、紅在哪一條判準。

**判定:PASS**

---

## AC5 —— 所有改動到的 SKILL.md 都過 `/writing-for-agents`

**做了什麼**:載入 `writing-for-agents` skill,拿它的判準逐條審本輪改動到的段落
(`git diff 84ab07d..HEAD -- skills/`:`skills/qa/SKILL.md` +53/-12、
`skills/build/SKILL.md` +19/-3)。build 那關的產出 comment 自陳「這輪沒留獨立走查紀錄,
QA 那關請當作待驗項覆核」,所以這條真的走一次。

### 符合

| 判準 | 觀察 |
| --- | --- |
| **Leading words** | `lane` 是 pretrained 詞,表格第一欄 + `### regression lane` / `### walkthrough lane` / `### code-review lane` 三個小標一致重複同一個 token,不是重複同一段意思 —— 正是 leading word 的用法。 |
| **Negation 配正面目標** | 每條禁令都先給正面動作:「不排隊」前面是「**同時開始 = 三個 sub-agent 在同一則訊息裡一次發出去**」;「不共用資源」後面接「各自的 port、暫存目錄、QA artifacts 子目錄分開」;「不准當成「沒跑到」略過」前面是「照樣寫進報告當紅」。沒有單獨掛著的禁令。 |
| **Completion criteria(clarity)** | 「三支都回來才收斂成一份報告」、`/build` 的「兩邊都回來才進 commit」—— 二元、數得出來,不是「做完就好」。 |
| **Information hierarchy / co-location** | 池的宣告、資源規則、失敗處置全在 §2 同一個標題下;三支 lane 各自的細節收進 `###` 子節,不散到別處。 |
| **Progressive disclosure** | 書面證據判準留在 `references/written-evidence.md` 用 pointer 接,沒有 inline 進來。 |
| **Pointer(qa description)** | 只加「regression / walkthrough / code-review 三線並行」,沒有把排序約束再寫一次;三個觸發 branch(ticket 指路 / bug fix 驗證 / demo 後固化)沒動。 |

### 不符合

1. **`skills/build/SKILL.md:12` —— 指到錯的節(relevance / 已經 stale)**

   ```
   呼叫 `/implement #N`(已收編,模型可叫)跑完整流程,跑完接 §2 收尾。
   ```

   本輪新的 §2 是「code-review 的並行位置」,收尾交棒被推到 §3。這行沒跟著改,現在把下一個
   agent 指到錯的節。同檔 `:18` 的「寫進 §3 的 comment」是改對的,兩行對照更看得出 `:12` 漏改。

2. **`skills/build/SKILL.md:8` —— 自我描述與本體矛盾(relevance / duplication)**

   ```
   薄層 wrap 原件 `/implement`:執行流程(tdd、typecheck、測試、`/code-review`、commit)全依原件,本檔只補一個 delta — **收尾交棒**。原件檔案不改。
   ```

   這行說「`/code-review` 全依原件」「只補一個 delta」,但本輪新增的 §2 做的就是**改
   `/code-review` 在原件裡的位置**,而且檔案現在有三個 delta 節(§2 並行位置、§3 收尾交棒、
   §4 書面證據)。frontmatter 的 description 已經更新成「只補 code-review 並行位置與收尾
   delta」,body 這行沒有 —— 同一個意思寫在兩處,只改了其中一處,剩下那處直接跟本體打架。

3. **`skills/qa/SKILL.md:79` —— 理由句用了無界全稱詞(nit)**

   ```
   這是本 skill 唯一一條看報告驗不出來的約束,所以寫在這裡當硬約束。
   ```

   `skills/build/references/written-evidence.md`「不准用無界全稱詞」要求理由句改寫成
   「母體多少、命中多少」的可數形式;「唯一一條」沒有邊界,而且本輪同一份文件裡
   「同時開始」那條(`:35-36`,一支一支發跟真的並行報告長得一樣)是同一個形狀的約束,
   直接構成反例。前兩句(空證據 → 全判 pass → 報告長得一模一樣)已經把 AC2 要的理由
   講完了,這句是 meta 收尾,刪掉不影響行為。

**判定:FAIL** —— 第 1、2 條是 `/build` 這輪自己改出來的 stale 交叉引用與自我矛盾,
`/writing-for-agents` 的 relevance / single-source-of-truth 判準直接咬到;第 3 條是 nit。
`scripts/validate.py` 對這三條都不吵(它守的是 `/qa` 的 lane 表與排序約束),所以純靠散文審。

---

## 摘要

| AC | 判定 |
| --- | --- |
| AC1 三線同時開始 | PASS |
| AC2 judge 排在 walkthrough 之後 + 明文寫理由(散文面 + 六格 mutation) | PASS |
| AC3 並行不搶資源 | PASS |
| AC4 失敗指名道姓、不被綠蓋過 | PASS |
| AC5 改動到的 SKILL.md 過 `/writing-for-agents` | FAIL(2 條 blocking 候選 + 1 條 nit,全在 `skills/build/SKILL.md`) |

另有一條與 AC 判定無關的守門觀察(`validate.py` 的 `no 並行池 section` 分支對出貨的
`skills/qa/SKILL.md` 到不了,整段刪掉會被誤報成「表是空的」),見 AC2 那節。
