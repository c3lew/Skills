---
name: close
description: 通用結案出口:讀票判型別核對完工定義、執行票上完工動作(deploy/migration 等)、結案 comment + dashboard 更新後關票。當 client-demo 過關後或 fix 驗完 ticket 指路「/close #N」、或 client 說某張票可以結了時使用;完工定義沒滿足就擋下指路,不硬關。
---

# close

所有票的結案唯一出口。Invariant:**完工定義沒滿足的票不關** — 缺哪條就 comment 指路對應下一棒,票留著。

## 1. 判型別 → 核對完工定義

讀票(body + comments + labels)判來源,對表逐條核對;定義正本在各出處 skill,以該檔為準:

| 票型 | 完工定義(全滿足才關) | 正本 |
|------|------------------------|------|
| slice 票 | 過關五條:client 親口 OK、blocking 清零、known issues 有處置、regression 全綠、scenarios 已固化 | `/client-demo` §6 |
| 純基礎工程切片(覆蓋驗收項標「無 — 間接驗證」) | QA blocking 清零 + regression 全綠;驗收由後續票的 demo 間接把關 | `/qa` §6 |
| client 報的 bug | fix 過 `/qa` + client 點頭 | `/maintain` §3 |
| agent 自撿 bug | regression 綠 + 白話回報 | `/maintain` §3 |
| tech-debt / refactor | regression 全綠(可見行為不變)+ 決策投影 | `/maintain` §5–6 |
| known issue「之後修」票 | 同 bug,依報的人分級 | `/client-demo` §5 |

型別對不上表(例:純文件票)→ 用票上 acceptance criteria 當完工定義,逐條核對。

## 2. 執行票上的完工動作

兩個地方找這張票特有的收尾工作,有就執行、把證據(指令輸出 / link)留給 §3:

1. 票 body 的「完工動作」段(deploy、migration、文件同步、通知…)。
2. 專案 CONTEXT.md 的收尾慣例。

Release 不在此:切片的 build + 換裝 + release note 是 client-demo 過關即發的最後一格,到這裡應該已完成 — 沒完成就是 §1 擋下的缺件。

## 3. 結案儀式

1. 結案 comment:做了什麼(commit links)、完工定義逐條打勾、完工動作證據、決策投影(本票有拍板才有)。
2. `/tracking-viz` 更新 dashboard。
3. 關票。
