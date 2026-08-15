---
name: next
description: 產線路由入口:讀現場(交棒 comment、tickets、repo 地基)推薦下一棒指令,只指路不執行。當你問「接下來做什麼 / 現在該跑哪個指令」、開新專案不知從哪開始、或隔了一陣子回到專案想接上進度時使用。
---

# next

整條產線的問路亭:判斷專案現在卡在哪一段,推薦**一個**下一棒指令。只指路,不 spawn 任何環節 — 推薦完就結束,跑不跑由 client 決定。

## 1. 先找接力棒

產線慣例:每個環節收尾都在票上留「下一步:`/skill #N`」comment。用 `gh` CLI 掃 open tickets,最新活動那張的最後一則交棒 comment 就是答案 — 找到就直接推薦它,不走路由表。

## 2. 沒接力棒才對路由表

收集現場訊號(git repo 有沒有、tracker 有沒有票、ticket labels 與狀態),由上往下比對,第一個命中的就是推薦:

| 現場 | 下一棒 |
|------|--------|
| 沒 git repo / 沒 GitHub tracker / 沒 `docs/agents/` | 鋪地基:`git init` + 開 GitHub repo + `/setup-matt-pocock-skills` |
| 大而模糊的 idea,還沒有 map issue | `/wayfinder` 建圖 |
| 清楚的單一 feature 需求,還沒有 spec | `/pm-intake` |
| spec 拍板了,還沒切票 | `/slice-tickets` |
| 有 `ready-for-agent` 切片票沒開工 | `/implement #N` |
| implement 完成的票在等驗 | `/qa #N` |
| QA blocking 清零在等驗收 | `/client-demo #N` |
| 上線後 client 報問題 / 丟想法 / 要清 backlog | `/maintain` |
| dashboard 提示「該 retro 了」 | `/retro`(client 說跑才跑) |
| 只是想看現況、或 dashboard 過期 | `/tracking-viz` |

同時命中多個(例:一張票在等 QA、另一個 feature 想進 spec)就照表序推薦最上面的,其餘當替代列出。

## 3. 回報

固定格式,推薦的放第一個標 `(Recommended)`:

- **推薦指令**(可複製的 `/skill #N`)+ 一兩句為什麼是它 + 代價/前提。
- 替代選項最多 1–2 個,各一句話講跟推薦差在哪。
- 現場一句話總結(現在在哪),讓 client 不用自己讀 tickets。
