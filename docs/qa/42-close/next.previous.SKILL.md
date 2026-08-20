---
name: next
description: 產線路由入口:讀現場(交棒 comment、tickets、repo 地基)推薦下一棒指令,只指路不執行。當你問「接下來做什麼 / 現在該跑哪個指令」、開新專案不知從哪開始、或隔了一陣子回到專案想接上進度時使用。
---

# next

整條產線的問路亭:判斷專案現在卡在哪一段,推薦**一個**下一棒指令。只指路,不 spawn 任何環節 — 推薦完就結束,跑不跑由 client 決定。

## 1. 先找接力棒

產線慣例:每個環節收尾都在票上留「下一步:`/skill #N`(Codex: `$skill #N`)」comment。用 `gh` CLI 掃 open tickets,最新活動那張的最後一則交棒 comment 就是答案 — 找到就推薦它,不走路由表。

**Sanity check**:接力棒只回答「那張票的下一步」。指令指向**別張票**時(例:票 A 上寫「下一步:`/build #B`(Codex: `$build #B`)」),先核對票 A 自己到結案條件沒 — 到了就先推 `/close #A`,接力棒指令列第二棒。一張票只有「還在產線上」或「已結案」兩種狀態,沒有「驗完了但放著」。

## 2. 沒接力棒才對路由表

收集現場訊號(git repo 有沒有、tracker 有沒有票、ticket labels 與狀態),由上往下比對,第一個命中的就是推薦:

| 現場 | 下一棒 |
|------|--------|
| 沒 git repo / 沒 GitHub tracker / 沒 `docs/agents/` | 鋪地基:`git init` + 開 GitHub repo + `/setup-matt-pocock-skills` |
| 大而模糊的 idea,還沒有 map issue | `/wayfinder` 建圖 |
| map 還有 open 子票(decision tickets) | 繼續 `/wayfinder` — 子票不逐張下指令 |
| map 收斂、或某 feature 相關 decisions 已全關 | `/pm-intake`(會讀 map 的 Decisions so far,不重問) |
| 清楚的單一 feature 需求,還沒有 spec | `/pm-intake` |
| spec 拍板了,還沒切票 | `/slice-tickets` |
| ≥2 張 `ready-for-agent` 切片票、彼此不卡(判法見下) | `/build-batch #<spec 票號>`;`/build #N` 列替代 |
| 有 `ready-for-agent` 切片票沒開工 | `/build #N` |
| implement 完成的票在等驗 | `/qa #N` |
| QA blocking 清零在等驗收 | `/client-demo #N` |
| 過關 / fix 驗完在等結案 | `/close #N` |
| 有票但沒有交棒 comment、也沒有 `ready-for-agent`(手開的、或裸跑 `/triage` 分完類的) | `/maintain #N` 補分類 + 補交棒 |
| 上線後 client 報問題 / 丟想法 / 要清 backlog | `/maintain` |
| dashboard 提示「該 retro 了」 | `/retro`(client 說跑才跑) |
| 只是想看現況、或 dashboard 過期 | `/tracking-viz` |

同時命中多個(例:一張票在等 QA、另一個 feature 想進 spec)就照表序推薦最上面的,其餘當替代列出。

### 批次那一列怎麼判

「彼此不卡」不用眼睛看,也不要在這裡另寫一套 — 那份判斷就是 `/build-batch` §3 在跑的那支檔,`build-batch` skill 目錄底下的 `batch.py`。同一份輸入餵進去,「要開」那段 ≥2 張就是命中這一列:

```bash
python <build-batch skill dir>/batch.py <<'JSON'
{"tickets": [{"number": 47, "state": "open", "blocked_by": []},
             {"number": 48, "state": "open", "blocked_by": [47]}],
 "titles": {"47": "...", "48": "..."}}
JSON
```

餵進去的候選跟 `/build-batch` §1 同一組:**open、帶 `ready-for-agent`、`## Parent` 指向同一份 spec** 的票 — 少了標籤這關,兩張已經在等 QA 的票也會被算成「要開 2 張」,推出一個沒東西可跑的批次。closed 的票照樣餵進去,它們是「卡關解除了沒」的依據。`blocked_by` 從票 body 的 `## Blocked by` 段抓 `#<n>`(平台原生的 dependency 關係優先)。

沒裝 `build-batch`(那支檔不在)就別自己心算,照下一列推單張 `/build #N`。

推薦行照 §3 雙寫:`/build-batch #51`(Codex: `$build-batch #51`),替代是 `/build #47`(Codex: `$build #47`)— 一次一張,慢但不用管平行合併。

## 3. 回報

固定格式,推薦的放第一個標 `(Recommended)`:

- **推薦指令**(可複製,雙寫:`/skill #N`(Codex: `$skill #N`)— 路由表寫單寫,輸出時補上 Codex 那半)+ 一兩句為什麼是它 + 代價/前提。
- 替代選項最多 1–2 個,各一句話講跟推薦差在哪。
- 現場一句話總結(現在在哪),讓 client 不用自己讀 tickets。
