# Spec: `slice-tickets`

**類型**:自建薄層 skill,wrap 原件 `/to-tickets`。

## 職責

把拍板的 spec 切成 vertical slice tickets,補一個 delta:**每張 ticket 標注它覆蓋的驗收項**。

## 觸發與入口

Spec 拍板後,ticket comment 指路「下一步:`/slice-tickets #N`」。

## 行為

1. 呼叫 `/to-tickets`(收編件)照其原生邏輯切票(vertical slice:每張都端到端、可 demo)。
2. **Delta**:每張 ticket body 加「覆蓋驗收項」段,列出這片做完後驗收清單哪幾條可測 — `qa` 走 walkthrough 時按這個範圍測,`client-demo` 的 re-demo 也按它定範圍。
3. 檢查覆蓋完整性:驗收清單每一條至少被一張 ticket 覆蓋,漏了就回報。

## 產出與交棒

- Vertical slice tickets(各標覆蓋驗收項)。
- 每張 ticket comment 指路「下一步:`/build #N`」。

## 引用

呼叫原件 `/to-tickets`;輸出被 `/implement`、`qa`、`client-demo` 消費。
