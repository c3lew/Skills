## Agent skills

### Issue tracker

Issues and specs are tracked in GitHub Issues. See `docs/agents/issue-tracker.md`.

### Triage labels

Use the five canonical triage labels. See `docs/agents/triage-labels.md`.

### Handoff lines are dual-written

寫給 client 看的交棒行,同一行同時給兩種寫法:

```
下一步:`/qa #12`(Codex: `$qa #12`)
```

Codex 顯式呼叫 skill 用 `$name`,不是 `/name` — 只寫 slash 的交棒 comment 貼到
Codex 叫不動。skill 內部給 agent 讀的互叫措辭(「呼叫原件 `/implement`」)維持原樣,
不做全域替換。適用範圍是所有寫給 client 的下一棒指令:交棒 comment、`/next` 推薦、
dashboard hero。`scripts/validate.py` 會抓 `skills/*/SKILL.md` 裡「下一步:…」
baton 內漏寫的那一半(到 `」` 或行尾為止;baton 之外的內部措辭不管)。

### 會被跑到的 python 檔要釘 UTF-8

有 `if __name__ == "__main__"` 的 `*.py`,進入點第一行釘 stdout;會讀 stdin 的
再釘 stdin:

```python
sys.stdout.reconfigure(encoding="utf-8")
sys.stdin.reconfigure(encoding="utf-8")
```

Windows 主控台預設 cp950,而這條線印給 client 的東西全是中文 — 沒釘就是壞碼,
遇到 Big5 沒有的字(emoji、假名)直接 `UnicodeEncodeError` 當場中斷(#58)。

**沒有豁免**:不看你有沒有印東西,也不看你是不是走 `.buffer` 繞過 text layer。
要寫 bytes 照寫(`sys.stdout.buffer.write(...)` / `sys.stdin.buffer.read()`,hook
走這條,因為 hook 掛了比壞碼更慘)— 那支檔案還是照樣多寫這一行,對只寫 bytes 的
檔它是無害的 no-op(#96)。

釘在 `__main__` 的**第一層**:寫在 `main()` 裡不算(self-check 會拿 StringIO 呼叫
`main()`,StringIO 沒有 `reconfigure`)、寫在模組層不算、巢狀進 `__main__` 裡面的
`if` / `try` 也不算(死碼裡的 pin 不算數,#72)。一個檔有幾個 `__main__` 就要幾個
都寫到(#69)。

`scripts/validate.py` 的 `stream_encoding_issues` 就是在比這件事,整條是語法比對 ——
沒有可達性分析。宣告過的天花板(#67):`__main__` 只認
`if __name__ == "__main__":` 這一種正規寫法,反著寫與 `in (...)` 這類等價寫法不認。

**受檢範圍**:`.py` 全收,只有 `__pycache__` 與 `.` 開頭的目錄不算原始碼。
`__main__.py` 是 package 的 entry point,一樣受檢(#68)。一支 `.py` parse 不動
直接判 fail —— 「守門讀不進來」跟「這支沒問題」是兩個答案,只有後者能報綠(#66)。

改這條判準的時候,`scripts/qa/97-mutate.py --run` 是那張 mutation 台:表上每個 knob
逐一改壞,`--self-check` 要**全部**轉紅,一個沒咬住就是那條判準沒有測試釘著。
(總數看 `--run` 自己印的那行,不要抄進文件 —— 抄了就會過期。)

### `/qa` 的並行池是三線,judge 不在池裡

`/qa` 同時開 regression / walkthrough / code-review 三支 sub-agent(三個 call 在同一則
訊息裡一次發出去,一支一支發就是排隊)。獨立 judge 排在 walkthrough 之後 —— 它吃的是
walkthrough 產出的 a11y snapshot,提早開就拿到空證據,然後把每一條驗收項都判 pass,
而那份報告跟真的全過長得一模一樣:沒有紅字、沒有例外、每條 pass(#107)。

`scripts/validate.py` 的 `judge_ordering_issues` 就是在比這件事,整條是散文比對:並行池
那張表列的 lane 必須剛好是這三支(上下順序自由 —— 三支同時開,順序沒有語意),而且
「judge 排在 walkthrough 之後」要在文字裡沒被否定地出現一次。

**錨在宣告,不錨在排版**(#112):池的宣告是**表頭第一欄寫 `lane` 的那張表**,lane
名字就是它資料列的第一欄 —— 粗體與否不算數,同一段裡別的表(資源分配之類)不是宣告。
排序約束只讀正文:`^#` 開頭的標題先剪掉(fence 內的 `# ` 是註解不是標題,留著)——
§3 的標題自己就同時含 judge 與「walkthrough…之後」,不剪的話正文那句 load-bearing 的
約束整句刪掉還是綠。錨在排版與關鍵字的版本有四個同型缺口,四格都在 `--self-check` 的
real-skill layer 上拿出貨檔實測。

**判準錨在哪,就要寫在被讀的那份文件裡**:`lane` 這個表頭字是宣告的一部分,所以
`skills/qa/SKILL.md` §2 自己寫著「這張表就是池的宣告,表頭第一欄寫 `lane`」——
#112 的根因原句就是「那條約束只活在 code comment 裡」,活在註解裡的約束下一個 agent
讀不到。認的是小寫 literal `lane`;改成別的字不會靜音,守門會當成池沒被宣告而紅。

**宣告過的天花板**:母體只認**自己開一支 judge** 的 skill,認的字是 `subagent 當
judge`。散文裡光提到 judge 的(`skills/build-batch/SKILL.md` 引「QA 第 6 輪 judge
實測」當出處)不上鉤 —— 跟 #57 的「呼叫 `/to-tickets`」同一種有界啟發式;改寫那句
話就掉出母體,那條靠 review 擋。

改這條判準的時候,`scripts/qa/107-mutate.py --run` 是那張 mutation 台:表上每個 knob
逐一改壞,`--self-check` 要全部轉紅。

### 跨 skill 借判斷:走安裝根目錄,不走相對連結

一個 skill 要重用另一個 skill 已經測過的判斷(`/next` 的批次那一列借 `build-batch`
的 `batch.py` 算「彼此不卡」),路徑寫成安裝根目錄底下的兄弟 skill:

```
python <build-batch skill dir>/batch.py
```

不要寫 `../build-batch/batch.py` — 那是 `scripts/validate.py` 擋的相對連結,install
只抄自己那個目錄,裝單一 skill 的機器上當場斷。同時一定要寫「那支檔不在時怎麼辦」的
退路(`/next` 是退回推單張 `/build #N`):借來的判斷可能根本沒裝,而重寫一份判斷比
沒有更糟 — 兩份會各說各話。

### Domain docs

This repository uses a single-context layout. See `docs/agents/domain.md`.
