---
name: retro
description: 系統自我升級的唯一入口:AFK 掃三餵食口(拍板錯更正、tech-debt backlog、QA 漏抓)找重複 pattern,產白話 retro 報告 + amendment 提案(三行制);client 逐條點頭才動 Skills repo 的 disciplines/skills 並發決策投影。當 client 說要跑 retro、或 dashboard 提示「該 retro 了」且 client 說跑時使用;不排程、不自行觸發。
---

# retro

消化系統留下的紀錄,把重複出現的問題升級成 disciplines / skills 的 amendment — 改一處全體生效。原料全來自專案 tracker 的紀錄,不從 client 腦袋挖素材。Amendment 只動 Skills repo 的 `docs/disciplines/` 與 skills 文件,不動專案 spec(那是 pm-intake / maintain 的事)。

規則書:[`references/tech-decisions.md`](references/tech-decisions.md) — 白話三行制、決策投影、更正紀錄格式。

## 1. 觸發與 watermark

不排程,攢批:未消化餵食項 ≥ 5 時 dashboard(tracking-viz)提示「該 retro 了」,client 說跑才跑。門檻是自動拍板:首輪 retro 在 retro issue 發決策投影留紀錄,之後要調整走 amendment 提案。

上一輪的 retro issue 是 **watermark**:本輪掃描範圍 = watermark 建立時間之後新增的餵食項 + 上輪報告的「未成案觀察」清單。已成案處理的才算消化;找不到 retro issue(第一輪)就全掃。

## 2. AFK 掃三餵食口

用 `gh` CLI 掃專案 tracker:

1. **拍板錯更正**:帶「當初為什麼拍錯」那行的更正 comments。
2. **Tech-debt backlog**:`tech-debt` label tickets(讀 pattern 用,票本身留給 maintain 的批次拍板)。
3. **QA 漏抓**:demo「不對」分類為**實作錯**的紀錄(分類 comment 與回流 tickets 都算)— QA 該抓沒抓的每一件。

## 3. 找 pattern

單一事件不成案,重複才是 signal:同類成因出現 ≥ 2 次才立案,每個 pattern 對到一份該改的 discipline / skill 檔。沒立案的單一事件進報告的「**未成案觀察**」清單(一行一件),留給下輪累積。料不足就老實說「這批料不足以成案」— 報告照發(零提案 + 未成案觀察)。

## 4. 白話報告 + amendment 提案

在專案 tracker 開一張 retro issue 發報告(這張就是下一輪 watermark),全白話:

- 每個 pattern 一段:發現了什麼 → 建議改哪份 discipline / skill → 改了之後差在哪。
- 每條 amendment 用白話三行制報(格式見規則書)。
- 「未成案觀察」清單:這輪讀過但沒立案的單一事件,下輪接著累積。
- 固定留一格「**你有沒有要補充的觀察**」— 有就聊、成案就併入提案清單;沒有就結。

## 5. 逐條點頭 → 落地

client 逐條「改 / 不改」,點頭的才動文件:

- 改 Skills repo 的 `docs/disciplines/` 或 `skills/` 檔案;動到 `docs/disciplines/` 就同步更新各 skill 的 `references/` 副本(byte 一致),然後 `python scripts/validate.py` 綠、`python scripts/install.py` 換裝(一次裝進 Claude Code 與 Codex 兩邊,少一邊就會有 agent 讀到舊版)。
- 每條落地在 retro issue 發一則決策投影 comment(格式見規則書)。
- 「不改」的在 retro issue 留一句紀錄,之後不再提。

## 6. 收尾

retro issue 補上每條的結果(改 → commit link;不改 → 一句紀錄)後 close,回報一句白話總結:這輪消化了幾件、改了什麼、下次攢到門檻再見。
