# QA 報告 — #127 同一個票號在一批裡出現兩次

**verdict:blocking 1 條,不放行。**

三支 lane(regression / walkthrough / code-review)在同一則訊息一次發出去;獨立 judge 等
walkthrough 交出證據之後才開。**三支 lane 都回綠,judge 判 fail** —— 而且 judge 打的不是
lane 沒測到的角落:lane 量的是「票號重複的時候擋不擋得住」,judge 問的是「client 會不會
在某個入口以為一切正常然後點頭」。答案是會,而且長得跟 #127 原本那張圖一模一樣。

## 逐條驗收項(判準 = 票上「覆蓋驗收項」的 client 原句)

spec #108 驗收清單第 1 條:

> 1. 切票的時候,每張票都標了「快」或「慢」加一句理由,整批一次列給我看,我可以當場改任何一張。

| AC(票上原文) | walkthrough | judge | QA 收斂後 | 依據 |
| --- | --- | --- | --- | --- |
| 重複票號當場停(非 0 退出),不靜靜印兩列 | pass | **fail** | **fail** | int 票號那條路真的停了;票號寫成 `"47"` 整條繞過,exit 0(BUG-A) |
| 訊息指名哪個票號、重複幾次 | pass | fail | **fail** | 主路徑 `#47(重複 2 次)` 數得準(三重複講 3 次、混批不連坐);alias 路徑 stderr 是空的(BUG-A) |
| 停之前整批照印(#118 不變) | pass | pass | **pass** | 兩列都印、車道各自算成一快一慢,矛盾本身看得見 |
| 貼票那段不印 | pass | **fail** | **fail** | 主路徑 0 行 `分級:`;alias 路徑照印兩行矛盾的 `分級:`(BUG-A,最重的一筆) |
| `--self-check` 涵蓋重複批次、斷言咬整句 | pass | pass | **pass** | 措辭換成語意相同的字 → AssertionError;抬頭退回數列也紅 |
| 進 `97-mutate.py` mutation 台,守門拆掉轉紅 | pass | pass | **pass** | 10 格 knob 全咬住、歸因全對 |
| `slice-tickets/SKILL.md` 補一句 | pass | pass | **pass** | §4 那句在,被 `CLASSIFY_LINES` pin 住,刪掉會紅 |

**為什麼 judge 的 fail 我全收**:這三條的分歧點只有一個 —— alias 入口算不算「重複票號」。
票面沒定義票號的型別,所以嚴格照字面 walkthrough 判 pass 沒有錯。但判準是 **client 的原句**,
不是實作的型別:對 client 來說 `"47"` 跟 `47` 就是同一張 #47。這條 AC 存在的唯一理由是
「不要靜靜印出兩條矛盾的分級」,而那件事現在還做得到。

## 三線各自的結果

| lane | verdict | 內容 |
| --- | --- | --- |
| regression | **green** | 13/13 全綠(`97-mutate` `--run` / `--attribute` 50/50、`107-mutate` 16/16、`97/107/114/118/120/121-walkthrough.sh` 六支 exit 0)。修前對照 24 批:該改的 10 批差額全部預期內(其中 7 批修前是 exit 0,#127 真的把安靜失敗修掉了),不該動的 13 批 stdout/stderr/exit **逐 byte 相同**。**本輪引入的新誤判 0 條** |
| walkthrough | **green** | 72 格 PASS / 0 FAIL。邊界全過:三重複數得準、重複+打錯字一次給完兩句、重複+硬規則同批不連坐、`(改不了)` 不疊層、左欄 east-asian width 全等、無重複批次跟 `7c4754a^` 逐字相同 |
| code-review | **green** | 0 blocking、1 known issue、2 nit。build 那輪自記的 5 條逐條驗過屬實,含「`t["number"]` KeyError 是 pre-existing」那條聲稱(diff 母體證實兩版在印出任何東西之前就炸,可觀察行為零差異) |
| judge(獨立,排在 walkthrough 之後) | **red** | AC1 / AC2 / AC4 fail |

**四把尺裡有三把獨立撞到同一個洞**:code-review 從讀碼那面(`Counter` 拿原值當 key、
`titles` 有做 `int(k)` 正規化而 `tickets` 沒有)、`127-wide.py` 從 1889 個批次的黑箱那面、
judge 從 client 的眼睛那面。三個互不通氣的入口指向同一件事 → 真的。

regression lane 也在探針裡撞到同一格,但它判 **pre-existing** 不計入 —— 那個判讀是對的
(修前修後逐字相同),下面 BUG-A 解釋為什麼 pre-existing 在這張票上還是 blocking。

## 第二把尺(Oracle 獨立性)

受測物本身就是判準 —— 它自己判自己有沒有重複,只跑它綠只證明它同意自己。
`scripts/qa/127-wide.py` 完全不 import `batch.py`、自己用 `str(number).strip()` 算重複,
跑 1889 個批次:1887 個沒有違例,11 筆違例全部集中在兩個手寫特例上。逐筆判讀:

| 撈到的 | 判讀 |
| --- | --- |
| `{"number":"47"}` 與 `{"number":47}` 同批 | **不是誤報,是真的漏** → BUG-A |
| `{"number":" 47 "}`(前後空白)與 `47` 同批 | 同根因,更明顯(左欄跟貼票行直接歪成 `# 47`),當 BUG-A 的極端版一起處理 |
| 同標題不同票號(#47 / #48 都叫「登入頁」) | **誤報方向的下界證明** —— wide 的 key 是票號不是標題,它沒有 flag 它。列在母體裡是證明這把尺不會因為兩張票長得像就亂停 |

反向(wide 說沒事、batch.py 卻擋了)0 筆。

## Blocking

### BUG-A — 票號型別不一致時,#127 要殺的那個形狀原封不動活著

`skills/build-batch/batch.py:643`,`duplicate_counts(t["number"] for t in tickets)`。
`Counter` 拿 `t["number"]` 的原值當 key,`"47" != 47`,所以整條守門繞過去。

實跑(QA 親手重現,不是引用):

```
$ printf '%s' '{"mode":"classify","tickets":[
    {"number":47,"coverage":[]},
    {"number":"47","coverage":["1. 登入頁"]}],
    "titles":{"47":"登入頁"}}' | PYTHONIOENCODING=utf-8 python skills/build-batch/batch.py

分級(2 張)— 標「慢」的會演給你看,標「快」的不會:
  快  #47 登入頁 — 沒有覆蓋驗收項,不會有你看得到的行為
  慢  #47 — 覆蓋 1 條驗收項

點頭之後,每張票上會多這一行:
  #47  分級:快 — 沒有覆蓋驗收項,不會有你看得到的行為
  #47  分級:慢 — 覆蓋 1 條驗收項
exit=0
```

把這段跟 #127 票上「問題」那段對照 —— **一模一樣**:同一張 #47 兩列矛盾的分級、貼票那段
照印兩行、exit 0、stderr 空的。agent 會照著把兩行都貼進同一張票,而 `scripts/validate.py`
的 grade-line 守門是逐行看的,兩行都合法。

唯一的破綻是第二列標題查不到所以少了「登入頁」(`titles` 那邊有做 `int(k)` 正規化,
`tickets` 這邊沒有 —— 同一個根因)。那是極弱的訊號,client 不會讀成「這裡有問題」。

**為什麼 pre-existing 還是 blocking**:這張票的存在理由就是「這個形狀不准再發生」。
守門出貨的時候留著一個那個形狀走得過去的門,AC 第一條字面上就沒過 —— 對 client 來說
`"47"` 跟 `47` 是同一張票。這不是理論邊界:`slice-tickets/SKILL.md` 自己寫「餵進 JSON
的票號是手打/照抄的」,而緊鄰的 `titles` key 本來就帶引號,手打時把引號帶過去完全在
#127 講的那個「手滑」射程內。

**修法方向**:不要在 `duplicate_counts` 裡補型別特例 —— 那是加碼補償誤解。在入口讀完
JSON 就把票號正規化成同一種 key(跟 `titles` 同一手),轉不動就當場停,順帶把「票號一定
是整數」從隱含假設變成有地方可以炸的合約。然後補一格對應的 mutation knob:現有 10 格
沒有一格是型別/空白 alias 那一類,所以 mutation 台全綠跟這個洞不衝突 —— 它根本沒被測到。

## Known issues(非 blocking,帶著 demo,處置由 client 在 demo 收尾整批確認)

### K-1 — 整批被擋的時候,乾淨的票也一起卡住

judge 提的,實錄情境 E:一批四列裡只有 #47 重複,乾淨的 #49 也一起進「這批還不能貼」,
client 沒辦法只改 #47 就往下走。spec 第 1 條「我可以當場改任何一張」在那批是空的。

這是 #118 就定下來的設計取捨(整批照印再整批停),不是本輪引入,而且 SKILL.md 開的處方
本來就是「刪掉多的再整批重跑」。但 client 應該知道這件事,**建議在 demo 時當面對一次**:
他要的是不是連乾淨的那幾張也一起卡。

### K-2 — `rejected_rows` 這個名字跟它自己的合約打架

`skills/build-batch/batch.py:544`。這支的存在理由就是「講的是**票**不是**列**」(docstring
自己寫的),回傳去重過的 `(票號, 理由)`,但 `row` 在這支檔裡到處都是 `(n, grade, reason)`
三元組。下一個讀 `rejected = rejected_rows(rows)` 的人第一直覺會是「rows 的子集」。
純改名,`97-mutate.py` 的 `classify_rejected_not_deduped` 咬的是函式內部那行,不受影響。

### K-3 — 重複那幾列看不到「為什麼是快 / 為什麼是慢」

walkthrough 與 code-review 各自提到。`grade in GRADES` 那一列的車道理由被 dupe 理由整個
換掉,client 看到兩列一模一樣的理由:矛盾看得見,但看不出矛盾從哪來。

**QA 傾向不收**:SKILL.md 開的處方是「刪掉多的那幾列再重跑」,不是「挑一列留著」,
所以 client 不需要拿那兩句理由去裁決。列出來讓 client 自己決定。

### K-4 — 同一句「刪掉多的再重跑」在每一列各印一次

三重複就印三次。內容正確,只是吵。#121 那條「同一句不要印兩遍」管的是 stdout/stderr
之間,沒管同一份清單內。不違反任何 AC。

## 未涵蓋範圍

- `plan` / `start` 兩個 mode 對重複票號仍不吭聲。但這兩個 mode 的資料來自
  `gh issue list --json`,issue number 天生唯一 —— 手打那條路就是 `classify`,#127 打在
  對的地方。code-review lane 明確**不建議擴 scope**,QA 同意。
- 這個 repo 沒有 UI,walkthrough 用 shell transcript 取代 Playwright a11y snapshot
  (照 #97 以來這條線的既有做法)。

## Demo 實錄清單

| 驗收項 | 實錄 |
| --- | --- |
| 1. 每張票都標了快/慢加一句理由,整批一次列給我看,我可以當場改任何一張 | `docs/qa/127-walkthrough.txt`(72 格,情境 A–I) |

其他證據:

- `docs/qa/127-wide.txt` —— 第二把尺,1889 批母體
- `docs/qa/127-regression.txt` —— regression suite 13 支完整 transcript
- `docs/qa/127-prevdiff.txt` —— 修前對照 24 批

## 一鍵重開指令

```bash
bash scripts/qa/127-walkthrough.sh "$(mktemp -d)/qa127"   # exit 0 = 全格符合預期
PYTHONIOENCODING=utf-8 python scripts/qa/127-wide.py      # 第二把尺,輸出是一份等人看的清單
PYTHONIOENCODING=utf-8 python scripts/qa/127-prevdiff.py  # 修前對照(自己從 git 取 7c4754a^ 那份)
```
