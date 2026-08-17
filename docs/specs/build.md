# Spec: `build`

**類型**:薄層 wrap(原件 `/implement`)。

## 職責

執行票的唯一入口:呼叫原件 `/implement` 跑 tdd / code-review / commit,收尾補產線交棒 — 產出 comment + 固定「下一步:`/qa #N`(Codex: `$qa #N`)」。存在理由:原件收尾不保證留交棒 comment,接力棒會斷;wrap 補上,原件不改。

## 觸發與入口

ticket comment 指路「下一步:`/build #N`(Codex: `$build #N`)」(slice-tickets 切完、maintain 分類完、qa blocking 回修、client-demo 實作錯回流)。

## 行為

1. 呼叫 `/implement #N`(收編件),流程全依原件。
2. Delta:收尾先 `git push`(原件只 commit,未 push 的 sha 在 GitHub 是 404),再在票上留產出 comment(commit links + review findings 處置)+ 交棒 comment「下一步:`/qa #N`(Codex: `$qa #N`)」;未 push 數歸零 + 票上看得到交棒 comment 才算完成。

## 引用

原件 `/implement`;輸出被 `qa` 消費。
