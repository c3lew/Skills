---
name: build
description: 薄層 wrap /implement:tdd、code-review、commit 全依原件,只補收尾 delta — 產出寫回票 + 固定留「下一步:/qa #N」交棒 comment。當 ticket 指路「/build #N」、或 ready-for-agent 的切片/bug 票要開工時使用。
---

# build

薄層 wrap 原件 `/implement`:執行流程(tdd、typecheck、測試、`/code-review`、commit)全依原件,本檔只補一個 delta — **收尾交棒**。原件檔案不改。

## 1. 呼叫原件

照 `/implement #N` 跑完整流程。

## 2. 收尾交棒(delta)

原件跑完不算完成,票上要有兩則 comment 才算:

1. **產出 comment**:改了什麼(commit links)+ review findings 處置。
2. **交棒 comment** 固定一行:「下一步:`/qa #N`」— bug 票同樣交給 qa(regression + 重現 scenario)。

完成標準:`gh issue view N --comments` 看得到交棒 comment 才結束 session。
