---
name: slice-tickets
description: 把拍板的 spec 切成 vertical slice tickets:薄層 wrap /to-tickets,每張 ticket 標注它覆蓋的驗收項,並檢查驗收清單每條都有票覆蓋。當 spec 拍板後要切票(pm-intake/to-spec 交棒指路「/slice-tickets #N」)時使用;沒有拍板驗收清單的 spec 先回 pm-intake 補。
---

# slice-tickets

薄層 wrap 原件 `/to-tickets`:切票邏輯全依原件,本檔只補一個 delta — **驗收項覆蓋標注**,讓 `qa` 與 `client-demo` 拿它定測試範圍。

## 1. 定輸入

讀 spec issue 的完整 body 與 comments。驗收清單(拍板的 checklist)是本 skill 的核心輸入 — 找不到就停下回報,指路回 `pm-intake` 補拍,不要自己編。

## 2. 呼叫 /to-tickets(發佈前停下)

呼叫 `/to-tickets <spec ref>`(已收編,模型可叫)照原件流程切票,但**發佈時機由本檔控制**:走到使用者核准 breakdown 後、進發佈步驟前停下,先做完 §3 與 §4 再發佈。

## 3. Delta:覆蓋驗收項

每張 ticket body 加一段:

```markdown
## 覆蓋驗收項

- <驗收清單第幾條,原文照抄>
```

這段是下游的測試範圍 oracle:`qa` 的 walkthrough 只測這幾條,`client-demo` 的 re-demo 也按它定範圍。沒有可測驗收項的票(純基礎工程)寫「無 — 由後續票的驗收項間接驗證」。

## 4. 覆蓋對帳,然後發佈

對帳:驗收清單每一條至少被一張 ticket 覆蓋。有漏條就回報使用者,補一張票或拍板不做 — 每條都有著落才發佈。發佈照原件的 tracker 流程走。

## 5. 交棒

- 每張 ticket comment:「下一步:`/build #N`」。
- Spec ticket 收尾 comment:tickets 清單 link + 覆蓋對帳結果 +「下一步:從無 blocker 的票開始 `/build #N`」。
