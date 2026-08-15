---
name: client-demo
description: QA 綠後帶 client 親手驗收切片:demo checkpoint(可點 link + 白話 demo script + QA 摘要)、「不對」四分類回流、known issues 處置、過關即發(build + 換裝 + release note)。當 qa blocking 清零後 ticket 指路「/client-demo #N」時使用;HITL,client 要在場,agent 不代答。
---

# client-demo

QA 過後的驗收點:client **親手操作**切片、處理「不對」、判定過關。UAT 本質需要人 — 看錄影會漏操作感,client 沒點頭的判定都不算數。對 client 的所有輸出照 [`references/pm-interview.md`](references/pm-interview.md) 的語言規則:白話、非技術也看得懂。

## 1. 定輸入

- **可點的 link**:跑起來的切片(desktop 切片 = 裝好的 app 本體)。
- **驗收清單**:spec issue 裡 client 拍板的原句,只取本 ticket 覆蓋的驗收項。
- **QA 報告摘要 + known issues 清單**:本 ticket 的 QA 報告(qa 產出)。

缺任何一項就停下回報,指路回 `/qa #N`,不要自己補。QA 報告有 blocking 未清零也一樣擋下。

## 2. Demo checkpoint

給 client 三樣東西,一頁講完:

1. 可點的 link。
2. 白話 demo script:照驗收清單逐條走,每條寫「做什麼操作、應該看到什麼」。
3. QA 報告摘要 — **開頭先白話告知 known issues**,client 帶著預期操作,不是操作到一半踩到。

然後讓 client 親手走。agent 陪跑答疑,不代操作、不替 client 說「這樣算過」。

## 3. Client 說「不對」→ 四分類

每個「不對」當場提分類建議 — 白話解釋四類差在哪,client 確認;agent 只建議不硬拍:

- **spec 理解錯**(spec 寫的就不是 client 要的)→ 回 `pm-intake` 改 spec。
- **實作錯**(spec 對,做出來不對)→ 開 bug ticket 走 QA loop(`/implement` → `/qa`)。
- **新想法**(spec 沒提過,看到實物才想到)→ 開 feature ticket 排優先,不混進本切片。
- **技術拍板錯**(agent 自動拍的技術決策拍錯)→ 照 [`references/tech-decisions.md`](references/tech-decisions.md) 的修正回路重拍,不重訪 client。

分類寫進對應回流 ticket:client 原話 + 確認的分類 + 下一步指路。

## 4. Re-demo

回流 ticket 修完回來,只 re-demo 受影響的驗收項,不整片重走。閉環標準:client 說「不對」的每個點,都要 client 親口點頭才算解掉。

## 5. Known issues 收尾

逐條給建議處置 — **現在修 / 開 ticket 之後修 / 不修留紀錄** — 附一句白話理由,client 整批確認、有意見才挑出來談。每條的決定寫回 ticket。

## 6. 過關判定

五條**全部成立**才算過關:

1. client 親口 OK。
2. blocking 清零。
3. 每條 known issue 都有處置決定。
4. regression suite 全綠。
5. 高價值 scenarios 已固化。

前三條成立後,comment「下一步:`/qa #N` 固化」交 `qa` 把本切片高價值 scenarios 寫進 regression suite;suite 跑綠即補齊第 4、5 條。任一條不成立就停在對應步驟,不往下走。

## 7. 過關即發

過關 checklist 的最後一格,不另開 session:

1. agent build 新版 + 直接換裝本機(app 重啟一次,client 在場)。
2. 留上一版 installer 當 rollback — 反悔成本 = 裝回去。
3. dashboard 留一行白話 release note,維護進件時對版本用。

## 8. 收尾

- 過關 → 關閉 ticket,dashboard 更新(切片狀態 + release note)。
- 有「不對」未閉環 → ticket 列出回流 tickets 與各自下一步,本票留著等 re-demo。
