# QA 報告 — #107 票內平行化(regression / walkthrough / code-review 三線並行,judge 排在 walkthrough 之後)

**verdict:blocking 2 條,不放行。**

本輪 QA 自己就是這張票的第一個實例:三支 lane 在同一則訊息一次發出去,judge 等 walkthrough
交出證據之後才開。

## 逐條驗收項

| AC | judge 判定 | QA 收斂後 | 依據 |
| --- | --- | --- | --- |
| 1 三線同時開始不互相等待 | pass | **pass** | `skills/qa/SKILL.md:24-36`,「同時開始」寫成可執行動作(同一則訊息一次發出去);序列語掃描 0 命中 |
| 2 judge 排在 walkthrough 之後 + 明文寫約束與理由 | pass | **fail** | 散文兩半都在,但守門守不住:正文那句排序約束整句刪掉,`validate.py` 仍 green(BUG-A2) |
| 3 並行後 regression 全綠且與序列跑一致 | fail(缺對照組) | **pass** | 補跑序列對照組,9/9 exit 0,與並行那次逐條一致 — `docs/qa/107-sequential-control.txt` |
| 4 任一支失敗要指名道姓,不因別支綠而報綠 | fail(演練用替身指令) | **pass** | 補跑真 sub-agent 失敗注入,lane `drill-regression` 自爆 exit 2,本報告指名列出 |
| 5 改動到的 SKILL.md 都過 `/writing-for-agents` | fail | **fail** | `skills/build/SKILL.md` 兩處 stale / 自相矛盾(BUG-B) |

judge 對 AC3 / AC4 判 fail 的是**證據缺口**,不是產品缺陷 — QA 本輪補跑後成立,原始判定保留在下面。

## 三線各自的結果

| lane | verdict | 內容 |
| --- | --- | --- |
| regression | **green** | 既有 9 支全 exit 0;`97-mutate` 15/15、`107-mutate` 8/8 咬住;修前對照母體 28 格不合 0;第二把尺 3 筆差額全判設計收窄 |
| walkthrough | **red** | AC1–AC4 pass,AC5 fail(3 條 finding) |
| code-review | **red** | 1 blocker(lane 只認粗體)+ 2 should-fix + 3 nit |
| drill-regression(失敗注入演練) | **red(刻意)** | 演練用,不計入判定;順手打穿 BUG-A2 |

## Blocking

### BUG-A — 守門的錨點沒對準 load-bearing 的那個宣告(同型四筆)

判準是 `judge_ordering_issues`。它咬的東西跟「文件真的寫下那條約束」之間有落差,四個形狀
都實測過:

| # | 破壞 | 守門 | 應該 |
| --- | --- | --- | --- |
| A1 | lane 表插一列 `\| judge \| 逐條判定 \| pass/fail \|`(第一欄不粗體) | **green** | red |
| A2 | 正文「**排序約束**:獨立 judge 排在 walkthrough 之後才開…」整句刪掉,只留 §3 標題 | **green** | red |
| A3 | 整段 `## 2. 並行池` 拿掉 | red,但訊息是 `lanes are []` | `no 並行池 section` |
| A4 | §2 的 `###` 子段裡加一張非 lane 表(第一欄粗體) | **red** | green(假陽性) |

同一個根:`LANE_CELL_RE` 只認粗體、`JUDGE_SPAN_RE`/`JUDGE_AFTER_RE` 掃整份文件、
`POOL_SECTION_RE` 的 lookahead 是 `^## ` 而 §3 標題本身含「並行池」「walkthrough 之後」。

A2 最嚴重 —— 它打穿的正是 AC2 那句話本身。self-check 的 real-skill layer 用
`JUDGE_AFTER_RE.sub("walkthrough 之前", text)` 改壞,那會連 §3 標題一起改掉所以會紅;
它從來沒測過「刪正文、留標題」。

### BUG-B — AC5:`skills/build/SKILL.md` 沒過 `/writing-for-agents`

1. `:12` `跑完接 §2 收尾` — 本輪新的 §2 是 code-review 並行位置,收尾是 §3。同檔 `:18` 改對了,這行漏改。
2. `:8` 「執行流程(…、`/code-review`、commit)全依原件,本檔只補一個 delta」 — §2 做的就是改 `/code-review` 的位置,而且現在有三個 delta 節;frontmatter 已更新,body 沒有。
3. (nit,併本票修)`skills/qa/SKILL.md:79` 「唯一一條看報告驗不出來的約束」是無界全稱詞,同檔 `:35-36` 就是反例。

## Known issues(帶著 demo,處置由 client 在 demo 收尾確認)

| # | 內容 | 建議觸發點 |
| --- | --- | --- |
| K1 | `validate.py:201` 與 `AGENTS.md:72` 舉的假陽性例子(client-demo / next)repo 裡不存在,真正的例子是 `skills/build-batch/SKILL.md:243` | 併 BUG-A 那張票一起改(同一段程式碼) |
| K2 | 排序約束在 `blueprint.md` / `AGENTS.md` / `SKILL.md` 各寫一次,守門只咬 SKILL.md,blueprint 那份會靜靜漂掉 | 下次動 blueprint 的票 |
| K3 | 軟否定(「沒有必要排在…之後」)繞得過 `unnegated` — #64 已宣告的天花板,非本輪引入 | 不修,已宣告 |
| K4 | 票上寫 harness 重複「repo 裡已經有 4 份」,實測共用該 harness 的只有 `97-mutate.py` / `107-mutate.py` 兩支(67 行逐字相同);tech-debt 票也還沒開 | 開 tech-debt 票時把範圍寫成兩支、67 行 |
| K5 | 這條規則目前全 repo 只有 `skills/qa/SKILL.md` 一支真的受檢,「會不會誤紅」的證據幾乎全靠 fixture 撐 | 下次有第二支 skill 自己開 judge 時複驗 |

## 未涵蓋範圍

- **「三支真的同時起跑」沒有帶時間戳的量測**。本輪只有本次 QA 執行本身當實例(三個 Agent call 在同一則訊息)。**接受不蓋**:要量就得改 harness 記時間戳,#107 沒點過,而且這條的失敗形狀是「慢」不是「錯」,`/qa` 每跑一次都會再曝露一次。
- **lane 真實工作負載搶資源**(同一個 dev server / Playwright / fixture DB)。這個 repo 沒有 web UI,搶不起來;本輪只驗到「兩支 `validate.py --self-check` 同開互不干擾」。**綁著**:第一張帶 dev server 的切片票 QA 時補驗。
- **Tauri 原生殼**:本 repo 不適用。

## demo 實錄清單

| 驗收項 | 實錄 |
| --- | --- |
| AC1 / AC2 / AC3(不搶資源那半)/ AC4 | `docs/qa/107-walkthrough.txt`(388 行,`set -x`) |
| 逐條判讀 | `docs/qa/107-walkthrough.md` |
| AC3 全綠 + 修前對照 + 第二把尺 | `docs/qa/107-regression.txt` |
| AC3 序列對照組 | `docs/qa/107-sequential-control.txt` |

## 一鍵重開

```
bash scripts/qa/107-walkthrough.sh "$(mktemp -d)/qa107"   # AC1–AC4 全套走查,exit 0 = 全格符合預期
python scripts/qa/107-mutate.py --run                     # 判準的 mutation 台,要 8/8 咬住
python scripts/qa/107-prevdiff.py                         # 修前對照,母體 28 不合 0
python scripts/qa/107-wide.py .                           # 第二把尺(不套受測規則)
```
