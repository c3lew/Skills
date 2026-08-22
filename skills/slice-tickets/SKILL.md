---
name: slice-tickets
description: 把拍板的 spec 切成 vertical slice tickets:薄層 wrap /to-tickets,每張 ticket 標注它覆蓋的驗收項、判快車道還是慢車道並整批給 client 點頭、對帳 blocking 邊,並檢查驗收清單每條都有票覆蓋。當 spec 拍板後要切票(pm-intake/to-spec 交棒指路「/slice-tickets #N」)時使用;沒有拍板驗收清單的 spec 先回 pm-intake 補。
---

# slice-tickets

薄層 wrap 原件 `/to-tickets`:切票邏輯全依原件,本檔補三個 delta — **驗收項覆蓋標注**(讓 `qa` 與 `client-demo` 拿它定測試範圍)、**快/慢分級**(讓 client 一眼看得出哪幾張會來煩他,並有否決權)與 **blocking 邊對帳**(讓 `build-batch` 敢照它排批次)。

## 1. 定輸入

讀 spec issue 的完整 body 與 comments。驗收清單(拍板的 checklist)是本 skill 的核心輸入 — 找不到就停下回報,指路回 `pm-intake` 補拍,不要自己編。

## 2. 呼叫 /to-tickets(發佈前停下)

呼叫 `/to-tickets <spec ref>`(已收編,模型可叫)照原件流程切票,但**發佈時機由本檔控制**:走到使用者核准 breakdown 後、進發佈步驟前停下,先做完 §3–§5,再照 §6 對帳與發佈。

## 3. Delta:覆蓋驗收項

每張 ticket body 加一段:

```markdown
## 覆蓋驗收項

- <驗收清單第幾條,原文照抄>
```

這段是下游的測試範圍 oracle:`qa` 的 walkthrough 只測這幾條,`client-demo` 的 re-demo 也按它定範圍。沒有可測驗收項的票(純基礎工程)寫「無 — 由後續票的驗收項間接驗證」。

## 4. Delta:快/慢分級

每張票填完「覆蓋驗收項」之後,整批一起判快慢。判準是可計算的,所以由 `build-batch` skill 目錄底下的 `batch.py` 算與印 —— 不要自己判、也不要自己排版那份清單,client 是照那份清單點頭的:

```bash
python <build-batch skill dir>/batch.py <<'JSON'
{"mode": "classify",
 "tickets": [{"number": 47, "coverage": ["1. 切票的時候…"], "judgement": false},
             {"number": 48, "coverage": [], "judgement": false},
             {"number": 49, "coverage": [], "judgement": true}],
 "titles": {"47": "…", "48": "…", "49": "…"}}
JSON
```

每張票餵三樣純資料:

- `coverage` —— §3 那段列出來的驗收項。寫「無 — 由後續票的驗收項間接驗證」的那種餵 `[]`。
- `judgement` —— 這張票會不會動到判斷邏輯、篩選條件、分類判準、或任何資料寫入。會就是 `true`,它是硬規則:一律慢,不看 `coverage` 寫什麼。
- `override` —— client 當場改的那個字(`"快"` / `"慢"`),沒改就不寫。

`batch.py` 不在 → 這批整批判慢車道,不要自己重寫一份判斷。保守方向不會漏掉 demo,兩份各說各話會。

印出來的清單直接給 client 看,然後問:**這批的快慢分級,有要改的嗎?** 要改就把那張的 `override` 填進去重跑一次 —— 照你說的改,改完的才是寫進票裡的那個。點頭之前不要寫進票,也不要發佈。

**硬規則蓋過 client 的 override**:`judgement` 是 `true` 的票被 client 說「改快」時,`batch.py` 會當場停,那批就這樣不能貼進票。這時候做兩件事:

1. 當場回報他為什麼停 —— 這張動到判斷邏輯或資料寫入,標「快」就沒有人會演給他看,而那種改動表面上看不出來、錯了最慘。
2. 他真的要那張快,回去改票的內容:把動到判斷邏輯或資料寫入的那部分切出去,再重切一次分級。票的內容沒變就是慢。

`judgement` 是你讀 diff 的判斷結果,不是放行開關 —— 不要自己去改 `judgement` 旗標讓它過。為了讓 client 那句話成立而把 `true` 改成 `false`,拆掉的是這條線上唯一的一道防護,而拆掉的當下沒有任何東西會紅。

點頭之後,把清單最後那段逐張貼進票 body 的「覆蓋驗收項」段下方,一張一行 —— 長這樣:

```markdown
分級:慢 — 覆蓋 2 條驗收項
```

格式固定是「分級:<快或慢> — 一句理由」。它由 `batch.py` 印出來、守門釘著,不要自己改寫措辭 —— 下游要拿這一行認車道,漂掉就認不出來。

**這條判準的天花板**:`coverage` 是照抄的、判得準,但 `judgement` 是 agent 讀 diff 自己判的,判錯必然會發生 —— 這關只保證你有否決權。判錯的代價要靠降級回路兜(spec #106 決策 3:標「快」的票對驗收清單有一條沒過就當場降級),而那個回路**還沒出貨**(自己查:`grep -rn 降級回路 skills/` —— #120 當下 7 個 hit 全在這一句與守它的 `batch.py` 註解裡,沒有一支 skill 在做那件事)。就算出了,它接得住的是**有驗收項**的那半;`coverage` 是空的那半(純基礎工程、沒有可看的行為)一條驗收項都沒有,回路不會被觸發,`judgement` 就是那半唯一的一道。不要為了把它判準而加規則 —— 這是宣告過的天花板,要補的是那個洞,不是這條判準。

## 5. Delta:blocking 邊對帳

切出來的票**一張 blocking 邊都沒宣告**的時候,發佈前回報 client:「這批 N 張彼此都沒有先後關係,對嗎?」等他回答,不要自己補一條邊,也不要靜靜發佈。

真的沒有先後關係是常態(平行切片),但「漏標」跟「真的沒有」在票面上長得一模一樣,而下游 `/build-batch` 完全吃這份宣告:漏標的那批會被算成全部能同時開,兩張改同一個檔案的票就並排跑起來,撞在 merge 那關 — 那時候已經沒人問得到 client 了。切票這關是唯一還問得到的地方。

有任何一張宣告了邊就不問 — 這一問防的是整批一起漏標(切票時根本沒想過先後),不是逐張複查。

## 6. 覆蓋對帳,然後發佈

對帳:驗收清單每一條至少被一張 ticket 覆蓋。有漏條就回報使用者,補一張票或拍板不做 — 每條都有著落才發佈。發佈照原件的 tracker 流程走。

## 7. 交棒

- 每張 ticket comment:「下一步:`/build #N`(Codex: `$build #N`)」。
- Spec ticket 收尾 comment:tickets 清單 link + 覆蓋對帳結果 +「下一步:從無 blocker 的票開始 `/build #N`(Codex: `$build #N`)」。
