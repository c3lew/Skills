---
name: build
description: 薄層 wrap /implement:tdd、code-review、commit 全依原件,只補 code-review 並行位置與收尾 delta — push 後產出寫回票 + 固定留「下一步:`/qa #N`(Codex: `$qa #N`)」交棒 comment。當 ticket 指路「/build #N」、或 ready-for-agent 的切片/bug 票要開工時使用。
---

# build

薄層 wrap 原件 `/implement`:執行流程(tdd、typecheck、測試、`/code-review`、commit)全依原件,本檔只補一個 delta — **收尾交棒**。原件檔案不改。

## 1. 呼叫原件

呼叫 `/implement #N`(已收編,模型可叫)跑完整流程,跑完接 §2 收尾。

## 2. code-review 的並行位置(delta)

原件把 `/code-review` 寫成序列的最後一步。它跟**跑 regression suite**(原件的 full test
suite)之間沒有資料依賴 — review 讀的是 diff,suite 讀的是跑起來的行為。兩支在同一則
訊息裡一次發出去,兩邊都回來才進 commit;任一支紅要指名道姓寫進 §3 的 comment,另一支綠蓋不過它。

**排序約束**:code-review 的 findings 在 commit **之前**處置完 — review 的結果決定
commit 裡有什麼,順序反過來就變成「先送出去再說」。tdd 的 red-green 循環同理,照原件
序列跑,不進並行池。

本關這支 code-review 吃的是 commit 前的工作區;`/qa` 那一關另有一支吃已經推上去的
最終 diff,兩支各看各的一段。

## 3. 收尾交棒(delta)

原件跑完不算完成,票上要有兩則 comment 才算 — 但**先 push**:

1. **push**:`git push`,再用 `git rev-list --count origin/<branch>..HEAD` 確認是 `0`。原件只 commit 不 push,沒推上去的 sha 在 GitHub 上是 404。
2. **產出 comment**:改了什麼(commit links)+ review findings 處置。
3. **交棒 comment** 固定一行:「下一步:`/qa #N`(Codex: `$qa #N`)」— bug 票同樣交給 qa(regression + 重現 scenario)。

順序是硬要求:push 沒綠不准貼 commit link — comment 一貼出去,link 就得當場點得開。

完成標準:未 push 的 commit 數是 `0`,且 `gh issue view N --comments` 看得到交棒 comment,才結束 session。

## 4. 書面證據(delta)

這片的交付物如果包含**本身就是證據的散文**(凍結例外清單的理由、研究文件的結論、
會被別人拿來對帳的量測宣稱),寫它的時候照 [`references/written-evidence.md`](references/written-evidence.md):
不用無界全稱詞、guard 蓋整個主張、guard 住在預設會跑的地方。純 code 的切片不適用。
