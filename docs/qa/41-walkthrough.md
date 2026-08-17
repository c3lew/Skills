# QA walkthrough — #41 Codex 端到端:`$build` → `$qa` 跑通一張票

票上「覆蓋驗收項」= spec #35 驗收清單**第 6 條**(唯一一條):

> 在 Codex 至少跑通一張票的 `$build` → `$qa`,能開票、能留交棒 comment。

另加票面五條 acceptance criteria。本切片沒有瀏覽器 UI,不跑 Playwright;QA 環境 = 純 CLI +
`gh` + 一次 Codex read-only 實跑。

**取證原則**:不採信 build comment 的自陳。Codex 那輪跑完留下的東西(commit、comment、issue)
是**持久 artifact**,QA 逐件回頭查;「貼上交棒行 Codex 叫不叫得動」則由 QA 這輪**自己在
Codex 上重跑一次**(read-only)。

環境:`D:/Self Project/Skills`,HEAD = `1b481dd`,working tree 乾淨,`origin/main` 同步。
Codex = `codex-cli 0.147.0`(`codex --version`)。

**一鍵重開指令**(client-demo 直接抄):

```powershell
cd "D:/Self Project/Skills"
# regression
python scripts/validate.py; python scripts/validate.py --self-check; python scripts/install.py --self-check
# Codex 那輪留下的 artifact
git branch -r --contains 8d36435; git branch -r --contains 1b481dd
gh issue view 43 --comments
gh issue view 47
# 交棒行在 Codex 上可直接使用(read-only,不動任何東西)
codex exec --sandbox read-only "只回答問題。ticket 上寫『下一步:`/qa #43`(Codex: `$qa #43`)』 — 這行你會呼叫哪個 skill?讀不讀得到?路徑?第一節標題?"
```

---

## Step 0 — regression suite

```text
$ python scripts/validate.py
OK validate green
exit=0

$ python scripts/validate.py --self-check
OK validate self-check green
exit=0

$ python scripts/install.py --self-check
[fixture] FAIL skills/bad: missing SKILL.md
OK install self-check green
exit=0

$ git status --short
(clean)
$ git rev-list --left-right --count origin/main...HEAD
0	0
```

全綠,working tree 乾淨且與 origin 同步。

## Step 1 — AC1:Codex 跑 `$build`,產出程式碼改動 + 交棒 comment

Codex 對真實 ticket **#43** 跑 `$build #43`。QA 回查 artifact:

```text
$ git show --stat --format="%H%n%an%n%ad%n%s" 8d36435
8d36435b8b24070d8fed11196e567112ea06bcb7
c3lew
Mon Aug 17 16:01:04 2026 +0800
fix: label install self-check fixture output (#43)
 scripts/install.py | 7 ++++++-

$ git branch -r --contains 8d36435
  origin/main
```

程式碼改動真的存在、真的在 `main` 上。票上兩則 comment(`gh api .../issues/43/comments`):

| 時間 (UTC) | 內容 |
|---|---|
| 08:01:22 | `## Build 產出` — 變更說明 + commit link + 驗證 + 雙軸 code-review 0 findings |
| 08:01:24 | ``下一步:`/qa #43`(Codex: `$qa #43`)`` |

commit 本地時間 16:01:04 (+0800) = 08:01:04 UTC,與 comment 時間吻合(18 秒後),
時間軸自洽,不是事後補寫。**pass**

## Step 2 — AC2:接著跑 `$qa`,依驗收項實測並回報

Codex 對同一張票跑 `$qa #43`。artifact:

```text
$ git show --stat --format="%H%n%ad%n%s" 1b481dd
1b481dd15d9ca8cf07dbb0a20cb9bd24a008f438
Mon Aug 17 16:04:42 2026 +0800
test: record issue 43 QA walkthrough
 docs/qa/43-walkthrough.md | 101 +++++++++++++++++++++++++++++++++++++++++
$ git branch -r --contains 1b481dd
  origin/main
```

`docs/qa/43-walkthrough.md` 內容(QA 逐段讀過)含:三條驗收原句列為 oracle、regression 四條實錄、
逐條驗收實錄(含 test-the-test:刻意 bypass fixture 阻擋 → `AssertionError` exit 1)、
獨立 judge 逐條判定表、blocking/known issues/未涵蓋段、一鍵重開指令 — 與本 repo 既有 QA 實錄
(`36`–`40`、`46`)同形,不是敷衍的一句「跑過了」。

票上 QA comment(08:05:30)含白話摘要 + 逐條判定表 + regression + blocking 0 + demo 實錄路徑 +
一鍵重開;08:05:31 留 ``下一步:`/client-demo #43`(Codex: `$client-demo #43`)``。**pass**

## Step 3 — AC3:QA 發現問題時能開新 ticket(`gh` 在 Codex 上可用)

#43 那輪 QA 全綠、沒東西可開,所以改用 #41 實跑掃出的**真實** finding 讓 Codex 實際開票:

```text
$ gh api repos/c3lew/Skills/issues/47 --jq '{created_at,user,labels}'
{"created_at":"2026-08-17T08:07:31Z","labels":["ready-for-agent"],"user":"c3lew"}
```

#47「qa skill 綁死 Playwright MCP,Codex 端沒有這個 MCP」— body 有 來源 / 問題 / Acceptance
criteria / Blocked by 完整段落,label 也帶上了。建立時間 08:07:31 落在 Codex session 窗內
(08:01 build → 08:05 qa → 08:07 開票),序列自洽。`gh issue create --label --body` 在 Codex 上可用。

註:GitHub 上所有動作都掛在同一個 `c3lew` token,**author 欄位無法區分 agent**;判定依據是
「時間序列 + 內容只有那輪 Codex 跑過才知道」(#47 body 裡的 `~/.codex/config.toml` MCP 清單、
`~/.codex/skills/playwright` 這條 CLI skill,都是 Codex 端本機事實)。**pass**

## Step 4 — AC4:交棒 comment 的雙寫格式在 Codex 上正確顯示且可直接使用

**(a) 格式正確** — 把 Codex 寫回 #43 的兩條交棒行逐字元 dump:

```text
下一步:`/qa #43`(Codex: `$qa #43`)
下=U+4E0B 一=U+4E00 步=U+6B65 :=U+003A `=U+0060 /=U+002F q a   # =U+0023 4 3 `
(=U+0028 C o d e x :=U+003A  =U+0020 `=U+0060 $=U+0024 q a   # 4 3 ` )=U+0029

下一步:`/client-demo #43`(Codex: `$client-demo #43`)
… 同樣全部 U+0028 / U+0029 / U+003A(半形)
```

冒號、括號、井號全是半形 ASCII,與 `AGENTS.md:16` 的模板 ``下一步:`/qa #12`(Codex: `$qa #12`)``
字元級一致,也吃得下 `scripts/validate.py` 的 `HANDOFF_SPAN_RE` dual-write 規則。

**(b) 可直接使用** — QA 這輪自己在 Codex 上重跑,把那行原封不動貼進去:

```text
$ codex exec --sandbox read-only "…ticket 上看到這行交棒:下一步:`/qa #43`(Codex: `$qa #43`)
   (1) 這行對你是什麼意思、你會呼叫哪個 skill (2) 讀不讀得到、路徑 (3) 第一節標題"

OpenAI Codex v0.147.0 / model: gpt-5.6-sol / sandbox: read-only

1. 這表示要對 GitHub ticket #43 執行 QA 流程;Codex 會呼叫 `$qa` skill。
2. 讀得到。路徑:C:\Users\user\.agents\skills\qa\SKILL.md
3. 第一節標題:## 1. 定輸入
```

Codex 把貼上的那行解讀成正確的 skill + 正確的 issue number,而且真的讀得到裝在
`~/.agents/skills/` 的 skill 本體(第一節標題對得上 repo 內 `skills/qa/SKILL.md`)。**pass**

## Step 5 — AC5:Claude Code 專屬假設全部記錄並標明已修 / 待決

#41 build comment 的「撞到的 Claude Code 專屬假設」段列七條:

| # | 內容 | 標注 |
|---|---|---|
| ① | `qa/SKILL.md` 綁死 Playwright MCP | **待決**,已開 #47(QA 已核對 #47 真的存在) |
| ② | skill 內部 `/xxx` 互叫措辭 | 不用修 — 實跑證明 Codex 解析得動 |
| ③ | `gh` CLI 跨 agent | 確認成立 |
| ④ | subagent judge | 確認成立 |
| ⑤ | Codex 收尾摘要用全形標點(寫回票的 comment 是半形) | 記一筆,不開票 |
| ⑥ | Codex 額外產出 rollback artifacts 在 `%TEMP%` | 無害,不處理 |
| ⑦ | `$build` 不 push → comment 裡的 commit link 在 push 前是 404 | 「本輪由我補 push」,**沒開票** |

②③④ 是「假設不成立/沒被打破」,⑤⑥ 是「有現象但不需要動作」,都有明確處置。
⑦ 是**真的有副作用、也明說了沒開票**的一條 — 見下方 known issue。

## Step 6 — 獨立 judge

乾淨 subagent 只收到 spec 第 6 條原句 + 票面五條 AC + Step 0–5 證據,不給實作脈絡與本 session 判斷:

| 驗收原句 / AC | judge | 理由(judge 原話節錄) |
|---|---|---|
| spec 第 6 條:Codex 上跑通一張票的 `$build` → `$qa`,能開票、能留交棒 comment | **pass** | 字面三個條件都有 artifact 支撐:build/qa comment 齊全、兩顆 commit 在 `origin/main`、#47 格式完整 |
| AC1 `$build` 產出改動 + 交棒 comment | **pass** | `8d36435` 改 `scripts/install.py` 且在 main;兩則 comment 與 commit 差 18 秒,時序合理 |
| AC2 `$qa` 依驗收項實測並回報 | **pass** | 101 行實錄含 oracle / regression / test-the-test / judge 表;票上 3/3 逐條回報 |
| AC3 QA 發現問題能開票 | **works-but-wrong** | 「`gh` 開票機制本身確實可用,但驗收句的觸發條件是『QA 發現問題時』—— #43 那輪 3/3 全 pass、沒有發現問題,#47 是用另一個跟 #43 驗收項無關的 meta-finding 去測開票功能」 |
| AC4 雙寫格式正確顯示且可直接使用 | **pass** | 「唯一有第一手 Codex 驗證的一條」:字元級一致 + 全新獨立 session 正確解讀 |
| AC5 專屬假設全部記錄並標明已修/待決 | **pass** | 七條各有明確 disposition;⑦ 標法較模糊但仍有處置紀錄 |

**Works-but-wrong:1 條(AC3)。**

Judge 另外點名兩處證據空白:

- **agent 歸屬**:除 AC4 那次 read-only 實跑外,其餘「Codex 跑的」全靠 artifact + 敘述,GitHub 側共用同一 token,無法第一手排除「其實是 Claude Code 跑的」。judge 仍判 pass(artifact 內容對得上驗收句字面),但明說這是最大空白。QA 同意 — 已列為未涵蓋。
- **Playwright MCP(①)沒被端到端踩到**:#43 是純 CLI 票,`$qa` 真的踩到缺失依賴時會怎麼壞,沒測過。這也是 AC3 判 works-but-wrong 的根本原因之一。

### QA 對 AC3 的分級判定

Judge 的缺口成立,但**不列 blocking**,理由:

- 本票「覆蓋驗收項」段指定的 oracle 是 **spec 驗收清單第 6 條**,它要的是「能開票」,judge 判 pass。
- AC3 括號裡自己寫明測的是「`gh` 操作在 Codex 上可用」,這點 #47 已證。
- 沒測到的是**更窄的一段**:`$qa` skill「判 fail → 自動開票」這條分支在 Codex 上的行為。要補齊得在 Codex 上另跑一張**故意會 fail** 的票,成本等同再跑一次本票。

→ 開 known issue ticket 追蹤(見下),處置由 client 在 demo 收尾決定。

## Blocking / known issues / 未涵蓋

**Blocking:0。**

**Known issues(帶著 demo,處置由 client 在 demo 收尾決定):**

0. **`$qa` 判 fail → 自動開票這條分支沒被實測過(judge 判 AC3 works-but-wrong)** — 已開 **#48**。
   #43 那輪全綠,#47 是拿無關的 meta-finding 手動開的。要補齊得在 Codex 上另跑一張會 fail 的票。
1. **`$build` 不 push,commit link 在 push 前是 404** — #41 build comment ⑦。`implement`/`build`
   只 commit 不 push,但交棒 comment 會貼 commit link;那條 link 要等有人 push 才解析得到,
   本輪由人補 push。不影響本票驗收項(commit 與 comment 都真的在),但產線上是個會重複出現的
   小坑。要不要把 push 收進產線 = 產線設計問題,建議 client 決定「現在開票 / 之後 retro 一起收 /
   不修」。
2. **`qa` skill 綁死 Playwright MCP** — 已開 #47,不是本票要修的。UI 票在 Codex 上跑 walkthrough
   之前會撞到。

**未涵蓋:**

- **無法重演 Codex 那一輪本身**:`$build #43` / `$qa #43` 是一次性的 agent session,QA 這輪能查的是
  它留下的持久 artifact(commit / comment / issue)+ 一次 read-only 的 Codex 實跑。若要「完全重演」,
  必須在 Codex 上再挑一張新票走完兩棒 — 成本等同再跑一次本票,QA 判定 artifact + 時間序列 +
  live smoke 三者交叉已足以支撐第 6 條。
- **agent 歸屬無法從 GitHub 側證明**:所有 API 動作共用同一個 `c3lew` token。
- **UI 票在 Codex 上的 walkthrough**:本輪用的 #43 是純 CLI 票,沒有觸到 Playwright 那段(即 #47)。
- **無原生殼(Tauri)行為**,本 repo 沒有。
