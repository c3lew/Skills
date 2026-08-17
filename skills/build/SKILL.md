---
name: build
description: 薄層 wrap /implement:tdd、code-review、commit 全依原件,只補收尾 delta — push 後產出寫回票 + 固定留「下一步:`/qa #N`(Codex: `$qa #N`)」交棒 comment。當 ticket 指路「/build #N」、或 ready-for-agent 的切片/bug 票要開工時使用。
---

# build

薄層 wrap 原件 `/implement`:執行流程(tdd、typecheck、測試、`/code-review`、commit)全依原件,本檔只補一個 delta — **收尾交棒**。原件檔案不改。

## 1. 呼叫原件

呼叫 `/implement #N`(已收編,模型可叫)跑完整流程,跑完接 §2 收尾。

## 2. 收尾交棒(delta)

原件跑完不算完成,票上要有兩則 comment 才算 — 但**先 push**:

1. **push**:`git push`,再用 `git rev-list --count origin/<branch>..HEAD` 確認是 `0`。原件只 commit 不 push,沒推上去的 sha 在 GitHub 上是 404。
2. **產出 comment**:改了什麼(commit links)+ review findings 處置。
3. **交棒 comment** 固定一行:「下一步:`/qa #N`(Codex: `$qa #N`)」— bug 票同樣交給 qa(regression + 重現 scenario)。

順序是硬要求:push 沒綠不准貼 commit link — comment 一貼出去,link 就得當場點得開。

完成標準:未 push 的 commit 數是 `0`,且 `gh issue view N --comments` 看得到交棒 comment,才結束 session。
