---
name: ui-mockup
description: 在 spec 拍板前把長相/操作流程的分岔做成可點 HTML prototype 給 client 選,拍板結果回寫 spec 當 QA 的視覺 oracle。當訪談(pm-intake)或改功能分流(maintain)出現長相/操作感分岔、且沒把握 client 會怎麼選時使用;純後端/CLI 切片與小改動不觸發。
---

# ui-mockup

薄層 wrap 原件 `/prototype`:prototype 怎麼建全依原件的 UI branch,本檔只管 client 拍板的流程 — variant 分級、拍板回寫、design system 防漂移。

## 1. 定輸入

- 呼叫方帶來的 UI 分岔點描述:哪個頁面/flow、有哪幾種走法。
- Design system 文件(如已存在):所有 prototype 引用它;要偏離時,把偏離本身當一個分岔給 client 選。

## 2. 出可點 prototype

呼叫 `/prototype` 走 UI branch,產單一可點 HTML。份量按 variant 分級:

- **首次出現的頁面或主要 flow** → 2–3 個可點 variant,讓 client 實際操作後選一個。
- **後續小改動** → 單一 proposal,client 點頭即過;不喜歡退回改,不另開 variant。

## 3. 拍板回寫

client 選定即拍板,一次做完:

- prototype commit 到 `prototype/<name>` branch,資產放 docs/prototypes/(沿 tracking-viz 慣例),不進 main。
- 拍板 prototype 的 branch link 寫入 spec — QA 拿它當視覺 oracle 抓 works-but-wrong;prototype 沒畫到的畫面(RWD、edge case)以其風格延伸。
- Spec 驗收清單加一條:「長相與操作流程與拍板 prototype 一致」。

## 4. Design system 文件

- 首個切片的 UI 拍板後,從拍板 prototype 抽一份輕量 design system 文件存 repo:色、字、間距、元件慣例,白話寫,讓後續 prototype 與實作都引用同一份。
- 已有文件時,每次拍板若產生新慣例就更新它。
