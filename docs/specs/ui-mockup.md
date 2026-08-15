# Spec: `ui-mockup`

**類型**:自建薄層 skill(HITL),wrap 原件 `/prototype`。

## 職責

在 spec 拍板**前**把長相/操作流程的分岔做成可點的 HTML prototype 給 client 選,拍板結果回寫 spec 當 QA 的視覺 oracle。

## 觸發

沿用兩軸對齊測試:長相/操作感會影響 client、且 LLM 沒把握 client 會怎麼選時才觸發。純後端/CLI 切片與小改動不觸發。呼叫方:pm-intake(主)、maintain 的改功能分流。

## 輸入

- 訪談中浮現的 UI 分岔點描述。
- Design system 文件(如已存在)— 所有 prototype 引用它;要偏離時當成分岔給 client 選。

## 行為

1. 呼叫 `/prototype` 產可點 HTML,存 `prototype/<name>` branch(沿 tracking-viz 慣例)。
2. **Variant 分級**:首次出現的頁面/主要 flow 給 2–3 個可點 variant 讓 client 操作後選;後續小改動出單一 proposal,點頭即過,不喜歡退回改。
3. 拍板後回寫紀律:prototype link 入 spec;驗收清單加「長相與操作流程與拍板 prototype 一致」條目。
4. 首個切片 UI 拍板後抽一份輕量 **design system 文件**存 repo(色、字、間距、元件慣例,白話可引用)。

## 產出與交棒

- 拍板 prototype(branch link)→ spec 的一部分,QA 拿它當視覺 oracle 抓 works-but-wrong;prototype 沒畫到的部分(RWD、edge case 畫面)以其風格延伸。
- Design system 文件(首次)或其更新。

## 引用

呼叫原件 `/prototype`;被 pm-intake、maintain 呼叫。
