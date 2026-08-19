---
name: slice-tickets
description: 把拍板的 spec 切成 vertical slice tickets:薄層 wrap /to-tickets,每張 ticket 標注它覆蓋的驗收項,並檢查驗收清單每條都有票覆蓋。當 spec 拍板後要切票(pm-intake/to-spec 交棒指路「/slice-tickets #N」)時使用;沒有拍板驗收清單的 spec 先回 pm-intake 補。
---

# slice-tickets

薄層 wrap 原件 `/to-tickets`:切票邏輯全依原件,本檔補兩個 delta — **驗收項覆蓋標注**(讓 `qa` 與 `client-demo` 拿它定測試範圍)與 **blocking 邊對帳**(讓 `build-batch` 敢照它排批次)。

## 1. 定輸入

讀 spec issue 的完整 body 與 comments。驗收清單(拍板的 checklist)是本 skill 的核心輸入 — 找不到就停下回報,指路回 `pm-intake` 補拍,不要自己編。

## 2. 呼叫 /to-tickets(發佈前停下)

呼叫 `/to-tickets <spec ref>`(已收編,模型可叫)照原件流程切票,但**發佈時機由本檔控制**:走到使用者核准 breakdown 後、進發佈步驟前停下,先做完 §3–§5 再發佈。

## 3. Delta:覆蓋驗收項

每張 ticket body 加一段:

```markdown
## 覆蓋驗收項

- <驗收清單第幾條,原文照抄>
```

這段是下游的測試範圍 oracle:`qa` 的 walkthrough 只測這幾條,`client-demo` 的 re-demo 也按它定範圍。沒有可測驗收項的票(純基礎工程)寫「無 — 由後續票的驗收項間接驗證」。

## 4. Delta:blocking 邊對帳

切出來的票**一張 blocking 邊都沒宣告**的時候,發佈前回報 client:「這批 N 張彼此都沒有先後關係,對嗎?」等他回答,不要自己補一條邊,也不要靜靜發佈。

真的沒有先後關係是常態(平行切片),但「漏標」跟「真的沒有」在票面上長得一模一樣,而下游 `/build-batch` 完全吃這份宣告:漏標的那批會被算成全部能同時開,兩張改同一個檔案的票就並排跑起來,撞在 merge 那關 — 那時候已經沒人問得到 client 了。切票這關是唯一還問得到的地方。

有任何一張宣告了邊就不問 — 這一問防的是整批一起漏標(切票時根本沒想過先後),不是逐張複查。

## 5. 覆蓋對帳,然後發佈

對帳:驗收清單每一條至少被一張 ticket 覆蓋。有漏條就回報使用者,補一張票或拍板不做 — 每條都有著落才發佈。發佈照原件的 tracker 流程走。

## 6. 交棒

- 每張 ticket comment:「下一步:`/build #N`(Codex: `$build #N`)」。
- Spec ticket 收尾 comment:tickets 清單 link + 覆蓋對帳結果 +「下一步:從無 blocker 的票開始 `/build #N`(Codex: `$build #N`)」。
